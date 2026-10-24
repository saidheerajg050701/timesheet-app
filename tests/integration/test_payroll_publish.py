import logging
import sqlite3
from contextlib import closing
from datetime import date, datetime, time, timedelta
from io import StringIO
from unittest import mock
from zoneinfo import ZoneInfo

import pytest
from django.core.management import call_command
from django.db import transaction

from audit.models import AuditLog
from payroll.models import AppendOnlyError, PayrollWeek
from payroll.services.export import export_period, mark_paid
from payroll.services.publish import out_of_sync, publish_period
from payroll.services.sync import sync_payroll
from tests.factories import EmployeeFactory, TimeEntryFactory
from timesheets.models import ChangeRequest, PeriodApproval
from timesheets.services.approvals import approve_period
from timesheets.services.changes import edit_directly
from timesheets.services.validation import EntryData

pytestmark = pytest.mark.django_db(databases=["default", "payroll"])

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)
PERIOD = date(2026, 9, 28)
WEEK1, WEEK2 = PERIOD, PERIOD + timedelta(weeks=1)


@pytest.fixture
def approve(django_capture_on_commit_callbacks):
    """Approve through the real Phase 7 service; payroll writes run after the commit."""

    def _approve(viewer, employee, period=PERIOD, now=NOW):
        with django_capture_on_commit_callbacks(execute=True):
            return approve_period(viewer, employee, period, now=now)

    return _approve


@pytest.fixture
def two_weeks(org, make_week):
    make_week(org.dev1, WEEK1)
    make_week(org.dev1, WEEK2)


def live(employee, week):
    return PayrollWeek.objects.exclude(status="SUPERSEDED").get(
        employee_code=employee.employee_code, week_start=week
    )


def test_approval_publishes_two_week_records(org, make_week, project, approve):
    """T-33: approving a period publishes 2 week records with the right split."""
    make_week(org.dev1, WEEK1)
    week2 = make_week(org.dev1, WEEK2, days=3)  # Mon–Wed work …
    TimeEntryFactory(  # … Thursday sick, Friday holiday
        timesheet=week2,
        work_date=WEEK2 + timedelta(days=3),
        category="SICK",
        project=None,
        start_time=None,
        end_time=None,
        minutes=480,
        reason="Flu",
    )
    TimeEntryFactory(
        timesheet=week2,
        work_date=WEEK2 + timedelta(days=4),
        category="HOLIDAY",
        project=None,
        start_time=None,
        end_time=None,
        minutes=480,
        reason="Public holiday",
    )
    approval = approve(org.manager, org.dev1)
    records = PayrollWeek.objects.order_by("week_start")
    assert records.count() == 2
    first, second = records
    assert (first.regular_minutes, first.overtime_minutes, first.total_minutes) == (2400, 0, 2400)
    assert (second.regular_minutes, second.sick_minutes, second.holiday_minutes) == (1440, 480, 480)
    assert second.total_minutes == 2400 and second.overtime_minutes == 0
    assert first.employee_code == "DEV1" and first.employee_name == "John Kim"
    assert (first.department, first.team) == ("Technology", "Platform")
    assert first.approved_by_code == "MANAGER" and first.approved_at == approval.decided_at
    assert first.period_start == PERIOD and first.status == "CURRENT" and first.version == 1
    publish_rows = AuditLog.objects.filter(action="PUBLISH")
    assert publish_rows.count() == 2 and {r.actor for r in publish_rows} == {org.manager}


def test_overtime_and_pto_split(org, make_week, project, approve):
    """T-34: 45 h worked + 8 h PTO with 40 h expected → 40 regular, 5 overtime, 8 PTO."""
    make_week(org.dev1, WEEK1)
    week2 = make_week(org.dev1, WEEK2, end=time(18))  # 5 × 9 h = 45 h worked
    TimeEntryFactory(
        timesheet=week2,
        work_date=WEEK2 + timedelta(days=5),
        category="PTO",
        project=None,
        start_time=None,
        end_time=None,
        minutes=480,
        reason="Comp day",
    )
    approve(org.manager, org.dev1)
    week = PayrollWeek.objects.using("payroll").get(status="CURRENT", week_start="2026-10-05")
    assert (week.regular_minutes, week.overtime_minutes, week.pto_minutes) == (2400, 300, 480)


def test_publish_twice_creates_no_duplicates(org, two_weeks, approve):
    """T-35: running publish_period twice creates no duplicates."""
    approval = approve(org.manager, org.dev1)
    assert publish_period(approval, system_actor="test", at=NOW).created == []
    publish_period(approval, system_actor="test", at=NOW)
    assert PayrollWeek.objects.using("payroll").filter(status="CURRENT").count() == 2


def test_approved_week_edited_later_gets_a_new_version(
    org, two_weeks, approve, project, django_capture_on_commit_callbacks
):
    """T-36: approved week edited later → old record SUPERSEDED; new version after re-approval."""
    approve(org.manager, org.dev1)
    old = live(org.dev1, WEEK1)
    week1 = old.source_timesheet_id
    change = ChangeRequest.objects.create(timesheet_id=week1, requester=org.dev1, reason="Fix")
    entries = [EntryData(WEEK1, "PROJECT", project, 180, "Fixed", time(9), time(12))]
    with django_capture_on_commit_callbacks(execute=True):
        edit_directly(change, org.manager, entries, now=NOW + timedelta(hours=1))
    old.refresh_from_db()
    assert old.status == "SUPERSEDED" and old.superseded_at == NOW + timedelta(hours=1)
    assert not PayrollWeek.objects.exclude(status="SUPERSEDED").exists()  # both weeks left
    assert PeriodApproval.objects.get(employee=org.dev1).status == "PENDING"

    approve(org.manager, org.dev1, now=NOW + timedelta(hours=2))
    new = live(org.dev1, WEEK1)
    assert new.version == 2 and new.regular_minutes == 180 and new.status == "CURRENT"
    assert live(org.dev1, WEEK2).version == 2
    assert AuditLog.objects.filter(action="SUPERSEDE").count() == 2


def test_payroll_records_are_append_only(org, two_weeks, approve):
    """T-104: frozen fields, backwards moves and bulk update/delete are all refused (D-15)."""
    approve(org.manager, org.dev1)
    record = live(org.dev1, WEEK1)
    record.regular_minutes += 60
    with pytest.raises(AppendOnlyError, match="regular_minutes is frozen"):
        record.save()
    record.refresh_from_db()
    for status in ("PAID", "CURRENT"):
        record.status = status
        record.paid_at = NOW
        with pytest.raises(AppendOnlyError):
            record.save()
        record.refresh_from_db()
    with pytest.raises(AppendOnlyError):
        PayrollWeek.objects.filter(pk=record.pk).update(status="PAID")
    with pytest.raises(AppendOnlyError):
        PayrollWeek.objects.filter(pk=record.pk).delete()
    with pytest.raises(AppendOnlyError):
        record.delete()
    with pytest.raises(AppendOnlyError):
        PayrollWeek.objects.bulk_update([record], ["status"])
    with pytest.raises(AppendOnlyError, match="starts as CURRENT"):
        PayrollWeek.objects.create(
            **{f: getattr(record, f) for f in PayrollWeek.FROZEN if f != "created_at"}
            | {"version": 9, "status": "PAID"}
        )

    # Forward moves work, and each lifecycle field is set once.
    batch = export_period(PERIOD, system_actor="test", at=NOW)
    record.refresh_from_db()
    assert (record.status, record.export_batch) == ("EXPORTED", batch)
    record.export_batch = "EXP-9999"
    with pytest.raises(AppendOnlyError, match="can't change on its own"):
        record.save()
    record.refresh_from_db()
    mark_paid(batch, system_actor="test", at=NOW)
    record.refresh_from_db()
    record.status, record.superseded_at = "SUPERSEDED", NOW
    record.save()
    record.status = "PAID"
    with pytest.raises(AppendOnlyError, match="SUPERSEDED record can't become PAID"):
        record.save()


def test_deactivated_employee_is_published_and_paid(org, make_week, approve):
    """T-105: a deactivated employee's approved period is published, exported and paid (D-19)."""
    leaver = EmployeeFactory(
        manager=org.manager, end_date=date(2026, 10, 1), status="INACTIVE", employee_code="LEFT1"
    )
    make_week(leaver, WEEK1, days=4)  # employed Mon–Thu
    approve(org.manager, leaver)
    record = PayrollWeek.objects.get(employee_code="LEFT1")
    assert record.expected_weekly_minutes == 1920  # 4 of 5 weekdays (D-71)
    assert record.regular_minutes == 1920 and record.overtime_minutes == 0
    assert not PayrollWeek.objects.filter(employee_code="LEFT1", week_start=WEEK2).exists()
    batch = export_period(PERIOD, system_actor="test", at=NOW)
    assert mark_paid(batch, system_actor="test", at=NOW) == 1
    record.refresh_from_db()
    assert record.status == "PAID"


def test_publish_and_sync_are_idempotent(
    org, make_week, approve, django_capture_on_commit_callbacks
):
    """T-106: repeated publish/sync never duplicate; sync fills gaps and supersedes stale rows."""
    for person in (org.dev1, org.dev2):
        make_week(person, WEEK1)
        make_week(person, WEEK2)
    with mock.patch("payroll.services.publish.publish_after_commit"):  # payroll missed dev2
        approve_period(org.manager, org.dev2, PERIOD, now=NOW)
    approve(org.manager, org.dev1)
    assert out_of_sync() == (2, 0)

    assert sync_payroll(at=NOW) == (2, 0)
    assert sync_payroll(at=NOW) == (0, 0)
    assert PayrollWeek.objects.count() == 4 and out_of_sync() == (0, 0)
    syncs = AuditLog.objects.filter(action="SYNC")
    assert syncs.count() == 2
    assert {(r.system_actor, r.actor) for r in syncs} == {("sync_payroll", None)}
    assert syncs.first().after["approved_periods"] == 2

    # Stale: a week leaves APPROVED but the supersede never ran.
    with mock.patch("payroll.services.publish.supersede_after_commit"):
        from timesheets.services.approvals import reset_approval

        reset_approval(org.dev2, PERIOD, actor=org.manager, at=NOW)
    assert out_of_sync() == (0, 2)
    assert sync_payroll(at=NOW) == (0, 2)
    assert out_of_sync() == (0, 0) and sync_payroll(at=NOW) == (0, 0)
    publish_rows = AuditLog.objects.filter(action="PUBLISH", system_actor="sync_payroll")
    assert publish_rows.count() == 2


def test_payroll_failure_after_commit_is_repaired_by_sync(
    org, two_weeks, approve, caplog, login_as
):
    """T-107: payroll write fails after the approval commits → approval stays; sync repairs."""
    with (
        mock.patch(
            "payroll.services.publish.next_version", side_effect=[1, RuntimeError("disk full")]
        ),
        caplog.at_level(logging.ERROR, logger="payroll.services.publish"),
    ):
        approve(org.manager, org.dev1)
    assert PeriodApproval.objects.get(employee=org.dev1).status == "APPROVED"
    assert not PayrollWeek.objects.exists()  # the first week was rolled back too
    assert "sync_payroll" in caplog.text
    page = login_as(org.payroll).get("/payroll/").content.decode()
    assert "2 approved weeks without a payroll record" in page

    call_command("sync_payroll", stdout=(out := StringIO()))
    assert "2 record(s) published" in out.getvalue()
    assert PayrollWeek.objects.count() == 2 and out_of_sync() == (0, 0)
    assert 'id="out-of-sync"' not in login_as(org.payroll).get("/payroll/").content.decode()


def test_main_rollback_writes_nothing_to_payroll(
    org, two_weeks, django_capture_on_commit_callbacks
):
    """T-108: if the main transaction rolls back after the hook, payroll is never written."""
    with django_capture_on_commit_callbacks(execute=True) as callbacks:
        with pytest.raises(RuntimeError), transaction.atomic():
            approve_period(org.manager, org.dev1, PERIOD, now=NOW)
            raise RuntimeError("something after the approval failed")
    assert callbacks == []
    assert not PeriodApproval.objects.exists() and not PayrollWeek.objects.exists()


def test_supersede_failure_is_repaired_by_sync(
    org, two_weeks, approve, project, django_capture_on_commit_callbacks
):
    """T-109: supersede fails after an edit → stale until sync; re-approval → next version."""
    approve(org.manager, org.dev1)
    week1 = live(org.dev1, WEEK1)
    change = ChangeRequest.objects.create(
        timesheet_id=week1.source_timesheet_id, requester=org.dev1, reason="Fix"
    )
    entries = [EntryData(WEEK1, "PROJECT", project, 240, "Fixed", time(9), time(13))]
    with (
        mock.patch(
            "payroll.services.publish.supersede_week", side_effect=RuntimeError("payroll locked")
        ),
        django_capture_on_commit_callbacks(execute=True),
    ):
        edit_directly(change, org.manager, entries, now=NOW)
    assert PayrollWeek.objects.filter(status="CURRENT").count() == 2  # stale
    assert out_of_sync() == (0, 2)
    assert sync_payroll(at=NOW) == (0, 2)
    approve(org.manager, org.dev1, now=NOW + timedelta(hours=1))
    assert live(org.dev1, WEEK1).version == 2 and live(org.dev1, WEEK1).regular_minutes == 240

    # A stale live record from an older decision is superseded by the next publish (D-66).
    with mock.patch("payroll.services.publish.supersede_after_commit"):
        change2 = ChangeRequest.objects.create(
            timesheet_id=week1.source_timesheet_id, requester=org.dev1, reason="Again"
        )
        edit_directly(change2, org.manager, entries, now=NOW + timedelta(hours=2))
    approve(org.manager, org.dev1, now=NOW + timedelta(hours=3))
    assert live(org.dev1, WEEK1).version == 3


def test_mark_paid_moves_only_exported_records(org, make_week, approve):
    """T-112: Mark as paid: EXPORTED → PAID for that batch only; others untouched; PAY audit."""
    for person in (org.dev1, org.dev2):
        make_week(person, WEEK1)
        make_week(person, WEEK2)
    approve(org.manager, org.dev1)
    batch = export_period(PERIOD, actor=org.payroll, at=NOW)
    approve(org.manager, org.dev2)  # after the export: stays CURRENT
    assert mark_paid(batch, actor=org.payroll, at=NOW + timedelta(days=1)) == 2
    statuses = dict(PayrollWeek.objects.values_list("employee_code", "status").order_by())
    assert statuses == {"DEV1": "PAID", "DEV2": "CURRENT"}
    assert all(r.paid_at for r in PayrollWeek.objects.filter(employee_code="DEV1"))
    assert mark_paid(batch, actor=org.payroll, at=NOW) == 0
    pay = AuditLog.objects.get(action="PAY")
    assert (pay.actor, pay.entity_id, pay.after) == (org.payroll, batch, {"records": 2})


@pytest.mark.django_db(databases=["default", "payroll"], transaction=True)
def test_backup_db_copies_both_databases(tmp_path, org):
    """T-113: backup_db writes timestamped copies of both databases that open with their tables."""
    out = StringIO()
    call_command("backup_db", "--dir", str(tmp_path), stdout=out)
    main = sorted(tmp_path.glob("db-*.sqlite3"))
    payroll = sorted(tmp_path.glob("payroll-*.sqlite3"))
    assert len(main) == len(payroll) == 1
    assert main[0].name.removeprefix("db-") == payroll[0].name.removeprefix("payroll-")  # same time
    tables = {}
    for path in (main[0], payroll[0]):
        with closing(sqlite3.connect(path)) as copy:
            tables[path] = {name for (name,) in copy.execute("select name from sqlite_master")}
    assert "directory_employee" in tables[main[0]] and "payroll_payrollweek" not in tables[main[0]]
    assert "payroll_payrollweek" in tables[payroll[0]]
    assert "Both databases backed up" in out.getvalue()
