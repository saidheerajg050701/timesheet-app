"""Change 4: automatic pay adjustments for corrected weeks that were already exported or paid
(D-118–D-126)."""

import csv
import io
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.urls import reverse

from audit.models import AuditLog
from payroll.models import AppendOnlyError, PayrollAdjustment, PayrollWeek
from payroll.services.adjustments import carry_period
from payroll.services.export import batch_csv, export_period, mark_paid
from payroll.services.register import finalize
from payroll.services.sync import sync_payroll_counts
from tests.factories import TimeEntryFactory
from tests.forms import grid_post
from timesheets.models import PeriodApproval
from timesheets.services.approvals import approve_period
from timesheets.services.changes import edit_directly, raise_request
from timesheets.services.validation import EntryData

pytestmark = pytest.mark.django_db(databases=["default", "payroll"])

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now
PAID = date(2026, 9, 13)  # weeks of Sun Sep 13 + Sep 20: exported (and paid) before the fix
LAST = date(2026, 9, 27)  # the most recent completed period at NOW: weeks Sep 27 + Oct 4
CURRENT = date(2026, 10, 11)
WEEK = PAID  # the corrected week
REASON = "Monday's release ran late."


@pytest.fixture
def payroll(org, make_week, project, fixed_now, django_capture_on_commit_callbacks):
    """Helpers to approve, export, pay and correct weeks, with the after-commit hooks run."""

    def approve(person, period):
        with django_capture_on_commit_callbacks(execute=True):
            approve_period(person.manager, person, period, now=NOW)

    def approved(person, period):
        make_week(person, period)
        make_week(person, period + timedelta(weeks=1))
        approve(person, period)

    def correct(person, week, monday_end, reason=REASON, period=None):
        """Change request → Edit directly (Mon–Fri, Monday until `monday_end`) → re-approval."""
        change = raise_request(person, week, reason, now=NOW)
        rows = []
        for offset in range(1, 6):
            end = monday_end if offset == 1 else time(17)
            minutes = (end.hour - 9) * 60 + end.minute
            rows.append(
                EntryData(
                    week + timedelta(days=offset), "PROJECT", project, minutes, "Work", time(9), end
                )
            )
        with django_capture_on_commit_callbacks(execute=True):
            edit_directly(change, person.manager, rows, "Fixed", now=NOW)
        approve(person, period or week)
        return change

    class Helpers:
        pass

    helpers = Helpers()
    helpers.approve, helpers.approved, helpers.correct = approve, approved, correct
    return helpers


def week_versions(code="DEV1", week=WEEK):
    return list(PayrollWeek.objects.filter(employee_code=code, week_start=week).order_by("version"))


def correction_row(html, week="Sep 13, 2026"):
    """The Corrections table row for DEV1's given week."""
    rows = html.split('<tr data-employee="DEV1">')[1:]
    return next(r.split("</tr>")[0] for r in rows if f"<td>{week}</td>" in r)


def rows_of(batch):
    return list(csv.DictReader(io.StringIO(batch_csv(batch))))


def test_positive_overtime_adjustment_after_payment(org, payroll):
    """T-173: a paid week corrected (+2 h) and re-approved: v2 SETTLED, +2 h overtime adjusted."""
    payroll.approved(org.dev1, PAID)
    batch = export_period(PAID, system_actor="test", at=NOW)
    mark_paid(batch, system_actor="test", at=NOW)
    payroll.correct(org.dev1, WEEK, time(19))  # Monday 09:00–19:00: 42 h worked
    v1, v2 = week_versions()
    assert v1.status == "SUPERSEDED" and v1.paid_at is not None
    assert v2.status == "SETTLED" and v2.settled_at == NOW and v2.export_batch == ""
    assert (v2.regular_minutes, v2.overtime_minutes) == (2400, 120)
    (adjustment,) = PayrollAdjustment.objects.all()
    decision = PeriodApproval.objects.get(employee=org.dev1, period_start=PAID)
    assert (adjustment.regular_minutes, adjustment.overtime_minutes) == (0, 120)
    assert (adjustment.pto_minutes, adjustment.sick_minutes, adjustment.holiday_minutes) == (
        0,
        0,
        0,
    )
    assert adjustment.total_minutes == 120 and adjustment.status == "CURRENT"
    assert (adjustment.old_version, adjustment.new_version) == (1, 2)
    assert (adjustment.week_start, adjustment.week_period_start) == (WEEK, PAID)
    assert adjustment.period_start == LAST  # the next period without an export batch
    assert (
        adjustment.approved_by_code == "MANAGER" and adjustment.approved_at == decision.decided_at
    )
    assert adjustment.reason == REASON
    other = week_versions(week=WEEK + timedelta(weeks=1))  # untouched week: settled, no money
    assert [r.status for r in other] == ["SUPERSEDED", "SETTLED"]


def test_negative_adjustment(org, payroll, login_as):
    """T-174: an exported (not yet paid) week reduced by 1.5 h → −1.50 regular, unescaped in CSV."""
    payroll.approved(org.dev1, PAID)
    export_period(PAID, system_actor="test", at=NOW)  # EXP-0001, not paid
    payroll.correct(org.dev1, WEEK, time(15, 30))  # Monday 6.5 h: 38.5 h worked
    (adjustment,) = PayrollAdjustment.objects.all()
    assert (adjustment.regular_minutes, adjustment.overtime_minutes) == (-90, 0)
    assert adjustment.total_minutes == -90 and adjustment.period_start == LAST
    page = login_as(org.payroll).get(reverse("payroll_period", args=[LAST]))
    assert "−1.50" in page.content.decode()  # in the register's carry-forward columns
    register = finalize(LAST, system_actor="test", now=NOW)
    (row,) = rows_of(register.export_batch)
    assert row["row_type"] == "ADJUSTMENT" and row["batch"] == "EXP-0002"
    assert row["regular_hours"] == "-1.50" and row["total_hours"] == "-1.50"  # a number, not '-
    assert (row["week_start"], row["original_week"]) == ("", "2026-09-13")


def test_no_adjustment_when_the_old_version_was_never_exported(org, payroll):
    """T-175: corrected before export → v2 CURRENT, no adjustment, exported as a normal WEEK row."""
    payroll.approved(org.dev1, LAST)
    payroll.correct(org.dev1, LAST, time(18))
    assert [r.status for r in week_versions(week=LAST)] == ["SUPERSEDED", "CURRENT"]
    assert not PayrollAdjustment.objects.exists()
    batch = export_period(LAST, system_actor="test", at=NOW)
    rows = rows_of(batch)
    assert [(r["row_type"], r["week_start"], r["version"]) for r in rows] == [
        ("WEEK", "2026-09-27", "2"),
        ("WEEK", "2026-10-04", "2"),
    ]
    assert rows[0]["total_hours"] == "41.00"


def test_several_corrections_of_the_same_week(org, payroll):
    """T-176: each re-approval adjusts against the previous version; the sum is never doubled."""
    payroll.approved(org.dev1, PAID)
    batch = export_period(PAID, system_actor="test", at=NOW)
    mark_paid(batch, system_actor="test", at=NOW)
    payroll.correct(org.dev1, WEEK, time(18))  # v2: +1 h (first adjustment still CURRENT)
    payroll.correct(org.dev1, WEEK, time(17, 30))  # v3: −0.5 h compared with v2
    payroll.correct(org.dev1, WEEK, time(17, 30))  # v4: no change → nothing new
    adjustments = list(PayrollAdjustment.objects.filter(week_start=WEEK).order_by("new_version"))
    assert [(a.old_version, a.new_version, a.total_minutes) for a in adjustments] == [
        (1, 2, 60),
        (2, 3, -30),
    ]
    v1, *_, v4 = week_versions()
    assert sum(a.total_minutes for a in adjustments) == v4.total_minutes - v1.total_minutes == 30
    assert v4.status == "SETTLED" and PayrollAdjustment.objects.count() == 2


def test_new_full_version_is_never_exported_twice(org, payroll, login_as):
    """T-177: after a correction the settled week stays out of every batch; only the difference."""
    payroll.approved(org.dev1, PAID)
    batch = export_period(PAID, system_actor="test", at=NOW)
    mark_paid(batch, system_actor="test", at=NOW)
    payroll.correct(org.dev1, WEEK, time(19))
    assert export_period(PAID, system_actor="test", at=NOW) is None  # nothing new for Sep 13
    payroll.approved(org.dev2, LAST)
    page = login_as(org.payroll).get(reverse("payroll_period", args=[LAST])).content.decode()
    dev1 = page.split('<tr data-employee="DEV1">')[1].split("</tr>")[0]
    assert "+2.00" in dev1 and "Sep 13 correction" in dev1  # only the difference is carried
    second = finalize(LAST, system_actor="test", now=NOW).export_batch
    rows = rows_of(second)
    assert [(r["employee_code"], r["row_type"]) for r in rows] == [
        ("DEV1", "ADJUSTMENT"),
        ("DEV2", "WEEK"),
        ("DEV2", "WEEK"),
    ]
    assert all(r.export_batch == "" for r in PayrollWeek.objects.filter(status="SETTLED"))
    paid_hours = (
        sum(
            r.total_minutes
            for r in PayrollWeek.objects.filter(employee_code="DEV1", week_start=WEEK)
            if r.exported_at
        )
        + PayrollAdjustment.objects.get().total_minutes
    )
    assert paid_hours == week_versions()[-1].total_minutes  # v1 once + the difference = v2


def exported_week(code, week, period, batch="EXP-0009"):
    record = PayrollWeek.objects.create(
        employee_code=code, employee_name="X", department="D", week_start=week, period_start=period,
        regular_minutes=0, overtime_minutes=0, pto_minutes=0, sick_minutes=0, holiday_minutes=0,
        total_minutes=0, expected_weekly_minutes=0, approved_by_code="M", approved_by_name="M",
        approved_at=NOW, source_timesheet_id=1,
    )  # fmt: skip
    record.status, record.export_batch, record.exported_at = "EXPORTED", batch, NOW
    record.save()
    return record


def test_carry_forward_period(fixed_now):
    """T-178: the first period without an export batch, never before the last completed one."""
    assert carry_period(PAID, NOW) == LAST  # the next period, not exported yet
    exported_week("A", LAST, LAST)
    assert carry_period(PAID, NOW) == CURRENT  # Sep 27 already has a batch → skip it
    assert carry_period(date(2026, 8, 2), NOW) == CURRENT  # never older than Sep 27 (floor)
    exported_week("B", CURRENT, CURRENT, batch="EXP-0010")
    assert carry_period(CURRENT, NOW) == date(2026, 10, 25)  # everything exported → next one
    later = NOW + timedelta(weeks=6)  # the most recent completed period moves on too
    assert carry_period(PAID, later) == date(2026, 11, 8)


def test_csv_totals_mark_paid_and_corrections(org, payroll, login_as):
    """T-179: CSV columns, totals with adjustments, Mark as paid and Corrections statuses."""
    payroll.approved(org.dev1, PAID)
    first = export_period(PAID, system_actor="test", at=NOW)
    mark_paid(first, system_actor="test", at=NOW)
    payroll.correct(org.dev1, WEEK, time(19), reason="=CMD('x') release ran late")
    payroll.approved(org.dev1, LAST)
    client = login_as(org.payroll)

    page = client.get(reverse("payroll_period", args=[LAST])).content.decode()
    line = page.split('<tr data-employee="DEV1">')[1].split("</tr>")[0]
    assert "80.00" in line and "+2.00" in line and "82.00" in line  # period + carry-forward
    assert 'data-adjustment="DEV1"' in page and "Scheduled" in page and "CMD" not in page
    row = correction_row(client.get(reverse("payroll_corrections")).content.decode())
    assert "Paid (EXP-0001)" in row and "+2.00 h →" in row
    assert 'href="/payroll/periods/2026-09-27/"' in row and "register Sep 27 – Oct 10, 2026" in row
    assert "Scheduled" in row and "=CMD" in row  # the reason, for payroll staff only

    client.post(reverse("payroll_finalize", args=[LAST]))
    download = client.get(reverse("payroll_detail_csv", args=[LAST]))
    rows = list(csv.DictReader(io.StringIO(download.content.decode("utf-8-sig"))))
    assert list(rows[0])[:3] == ["batch", "employee_code", "row_type"]
    assert [(r["row_type"], r["week_start"], r["original_week"], r["version"]) for r in rows] == [
        ("WEEK", "2026-09-27", "", "1"),
        ("WEEK", "2026-10-04", "", "1"),
        ("ADJUSTMENT", "", "2026-09-13", "1→2"),
    ]
    assert rows[2]["overtime_hours"] == "2.00" and "CMD" not in str(rows)  # no reason in CSV
    row = correction_row(client.get(reverse("payroll_corrections")).content.decode())
    assert "Exported in EXP-0002" in row and "(finalized &amp; exported)" in row
    paid = client.post(reverse("payroll_register_paid", args=[LAST]))
    assert "Register marked as paid." in client.get(paid.url).content.decode()
    assert PayrollAdjustment.objects.get().status == "PAID"
    corrections = client.get(reverse("payroll_corrections")).content.decode()
    assert "Paid (EXP-0002)" in correction_row(corrections)
    assert "no adjustment (0.00)" in correction_row(corrections, "Sep 20, 2026")  # untouched


def test_sync_creates_missing_adjustments_idempotently(org, payroll):
    """T-180: a version re-exported in full before Change 4 is settled and adjusted, once."""
    payroll.approved(org.dev1, PAID)
    batch = export_period(PAID, system_actor="test", at=NOW)
    mark_paid(batch, system_actor="test", at=NOW)
    v1 = week_versions()[0]
    v1.status, v1.superseded_at = "SUPERSEDED", NOW
    v1.save()
    fields = {f: getattr(v1, f) for f in PayrollWeek.FROZEN if f not in ("version", "created_at")}
    fields.update(regular_minutes=v1.regular_minutes + 60, total_minutes=v1.total_minutes + 60)
    legacy = PayrollWeek.objects.create(**fields, version=2)  # CURRENT, no adjustment (old way)
    assert sync_payroll_counts(at=NOW) == (0, 0, 1)
    legacy.refresh_from_db()
    assert legacy.status == "SETTLED"
    (adjustment,) = PayrollAdjustment.objects.all()
    assert adjustment.total_minutes == 60 and adjustment.reason == "Re-approved after a change"
    assert sync_payroll_counts(at=NOW) == (0, 0, 0)  # idempotent
    assert PayrollAdjustment.objects.count() == 1
    syncs = list(AuditLog.objects.filter(action="SYNC").order_by("pk"))
    assert [s.after["adjustments"] for s in syncs] == [1, 0]
    publish = AuditLog.objects.get(action="PUBLISH", entity_type="PayrollAdjustment")
    assert publish.system_actor == "sync_payroll"


def test_adjustments_are_append_only_and_audited(org, payroll):
    """T-181: frozen amounts, forward-only status, no delete/update; publish/export/pay audited."""
    payroll.approved(org.dev1, PAID)
    batch = export_period(PAID, system_actor="test", at=NOW)
    mark_paid(batch, system_actor="test", at=NOW)
    payroll.correct(org.dev1, WEEK, time(19))
    adjustment = PayrollAdjustment.objects.get()
    adjustment.total_minutes = 999
    with pytest.raises(AppendOnlyError, match="frozen"):
        adjustment.save()
    adjustment.refresh_from_db()
    adjustment.status, adjustment.paid_at = "PAID", NOW
    with pytest.raises(AppendOnlyError):  # CURRENT can't skip to PAID
        adjustment.save()
    for attempt in (
        lambda: PayrollAdjustment.objects.get().delete(),
        lambda: PayrollAdjustment.objects.all().delete(),
        lambda: PayrollAdjustment.objects.all().update(total_minutes=0),
        lambda: PayrollAdjustment.objects.bulk_update([adjustment], ["status"]),
        lambda: PayrollAdjustment.objects.create(
            **{f: getattr(adjustment, f) for f in PayrollAdjustment.FROZEN if f != "created_at"}
            | {"new_version": 9, "status": "EXPORTED"}
        ),
    ):
        with pytest.raises(AppendOnlyError):
            attempt()
    settled = week_versions()[1]
    settled.status, settled.export_batch, settled.exported_at = "EXPORTED", "EXP-0099", NOW
    with pytest.raises(AppendOnlyError):  # a settled week is never exported
        settled.save()

    second = export_period(LAST, actor=org.payroll, at=NOW)
    mark_paid(second, actor=org.payroll, at=NOW)
    adjustment.refresh_from_db()
    adjustment.status = "EXPORTED"
    with pytest.raises(AppendOnlyError):  # PAID never goes back
        adjustment.save()
    publish = AuditLog.objects.get(action="PUBLISH", entity_type="PayrollAdjustment")
    assert publish.actor == org.manager
    assert publish.after["versions"] == [1, 2] and publish.after["overtime_minutes"] == 120
    assert publish.after["period_start"] == "2026-09-27" and "reason" not in publish.after
    export = AuditLog.objects.get(action="EXPORT", entity_id=second)
    pay = AuditLog.objects.get(action="PAY", entity_id=second)
    assert export.after["adjustments"] == pay.after["adjustments"] == 1


def test_settled_week_links_to_the_period_that_paid_its_difference(org, payroll, login_as):
    """T-182: an old period labels a Settled week with the period its adjustment went to."""
    payroll.approved(org.dev1, PAID)
    batch = export_period(PAID, system_actor="test", at=NOW)
    mark_paid(batch, system_actor="test", at=NOW)
    payroll.correct(org.dev1, WEEK, time(19))  # +2 h → carried to Sep 27 – Oct 10
    client = login_as(org.payroll)
    page = client.get(reverse("payroll_period", args=[PAID])).content.decode()

    def week_row(day):
        return page.split(f"<td>John Kim</td><td>{day}</td>")[1].split("</tr>")[0]

    corrected = week_row("Sep 13")
    assert "Settled" in corrected
    link = '<a href="/payroll/periods/2026-09-27/">Settled by adjustment in Sep 27 – Oct 10</a>'
    assert link in corrected
    assert "No difference to pay" in week_row("Sep 20")  # the untouched week: settled, no money
    old = client.get(reverse("payroll"), {"period": "2026-09-27"})  # older links still work
    assert old.url == reverse("payroll_period", args=[date(2026, 9, 27)])
    carried_to = client.get(old.url).content.decode()
    assert 'data-adjustment="DEV1"' in carried_to and "+2.00" in carried_to
    assert "Settled by adjustment" not in carried_to  # only Settled weeks carry the label


def test_paid_week_corrected_by_deleting_a_row(
    org, payroll, make_week, login_as, django_capture_on_commit_callbacks
):
    """T-198: a paid week corrected with Delete row in Edit directly → −2.00 h overtime."""
    sheet = make_week(org.dev1, PAID)
    make_week(org.dev1, PAID + timedelta(weeks=1))
    TimeEntryFactory(
        timesheet=sheet,
        work_date=PAID + timedelta(days=1),
        category="MEETING",
        project=None,
        start_time=time(17),
        end_time=time(19),
        minutes=120,
        reason="Release call",
    )  # 42 h: 2 h overtime, paid
    payroll.approve(org.dev1, PAID)
    mark_paid(export_period(PAID, system_actor="test", at=NOW), system_actor="test", at=NOW)
    assert week_versions()[0].overtime_minutes == 120

    change = raise_request(org.dev1, WEEK, REASON, now=NOW)
    manager = login_as(org.manager)
    edit = reverse("request_edit", args=[change.pk])
    rows = reverse("request_rows", args=[change.pk])
    grid = manager.get(edit).context["grid"]
    deleted = manager.post(rows, {**grid_post(grid), "row-action": "delete", "row-key": "MEETING:"})
    data = {**grid_post(deleted.context["grid"]), "note": "The call was booked twice."}
    with django_capture_on_commit_callbacks(execute=True):
        assert manager.post(edit, data).status_code == 302
    payroll.approve(org.dev1, PAID)

    v1, v2 = week_versions()
    assert v1.status == "SUPERSEDED" and v1.paid_at is not None
    assert v2.status == "SETTLED" and (v2.regular_minutes, v2.overtime_minutes) == (2400, 0)
    (adjustment,) = PayrollAdjustment.objects.all()
    assert (adjustment.regular_minutes, adjustment.overtime_minutes) == (0, -120)
    assert adjustment.total_minutes == -120 and adjustment.period_start == LAST
    assert adjustment.reason == REASON
