"""Change 8: pay period registers (D-132–D-138)."""

import csv
import io
from datetime import UTC, date, datetime, time, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.urls import reverse

from audit.models import AuditLog
from payroll.models import (
    AppendOnlyError,
    PayrollAdjustment,
    PayrollRegister,
    PayrollRegisterLine,
    PayrollWeek,
)
from payroll.services.adjustments import carry_period
from payroll.services.export import CSV_COLUMNS, export_period
from payroll.services.export import mark_paid as pay_batch
from payroll.services.register import (
    OPEN,
    READY,
    REGISTER_COLUMNS,
    build_registers,
    finalize,
    mark_paid,
    period_items,
    period_state,
    preview,
    table,
)
from payroll.services.sync import sync_payroll_report
from tests.factories import EmployeeFactory, TimeEntryFactory, TimesheetFactory
from timesheets.models import Timesheet
from timesheets.services.approvals import (
    approve_period,
    company_period_rows,
    period_rows,
)
from timesheets.services.calendar import approval_deadline_for
from timesheets.services.changes import edit_directly, raise_request
from timesheets.services.validation import EntryData

pytestmark = pytest.mark.django_db(databases=["default", "payroll"])

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now
PERIOD = date(2026, 9, 27)  # weeks of Sep 27 + Oct 4; ended Sat Oct 10
BEFORE = datetime(2026, 10, 12, 9, 0, tzinfo=TZ)  # Monday, before the 12:00 deadline
EARLIER = date(2026, 9, 13)
NEXT = date(2026, 10, 11)  # the current period at NOW (ends Sat Oct 24)
AFTER_NEXT = datetime(2026, 11, 2, 10, 0, tzinfo=TZ)  # NEXT has ended and its deadline passed


@pytest.fixture
def company(
    org, make_week, project, fixed_now, approve_everyone, django_capture_on_commit_callbacks
):
    """Approve people's periods (both weeks submitted first); payroll written after commit.
    `rest` approves everyone else, the Change 9 way (their empty locked weeks, 0.00)."""

    def approver(person):
        return person.manager or org.hr  # the CEO has no manager: an admin approves (D-11)

    def approve(*people, period=PERIOD, now=NOW, **week):
        for person in people:
            for start in (period, period + timedelta(weeks=1)):
                if not Timesheet.objects.filter(employee=person, week_start=start).exists():
                    make_week(person, start, **week)
            with django_capture_on_commit_callbacks(execute=True):
                approve_period(approver(person), person, period, now=now)

    def everyone(*, but=(), period=PERIOD, now=NOW):
        people = [e for e in vars(org).values() if e not in but]
        approve(*people, period=period, now=now)

    class Helpers:
        pass

    helpers = Helpers()
    helpers.approve, helpers.everyone, helpers.approver = approve, everyone, approver
    helpers.rest = lambda period=PERIOD, now=NOW: approve_everyone(period, now)
    return helpers


def line_of(lines, code):
    return next(line for line in lines if line.employee_code == code)


def correct(person, week, monday_end, project, capture, *, now=NOW):
    """Change request → Edit directly (Mon–Fri, Monday until monday_end) → re-approval."""
    change = raise_request(person, week, "Monday was different", now=now)
    rows = []
    for offset in range(1, 6):
        end = monday_end if offset == 1 else time(17)
        minutes = (end.hour - 9) * 60 + end.minute
        day = week + timedelta(days=offset)
        rows.append(EntryData(day, "PROJECT", project, minutes, "Work", time(9), end))
    period = week if (week - date(2026, 1, 4)).days % 14 == 0 else week - timedelta(weeks=1)
    with capture(execute=True):
        edit_directly(change, person.manager, rows, "Fixed", now=now)
    with capture(execute=True):
        approve_period(person.manager, person, period, now=now)


def test_approval_deadline(settings, org, company, login_as):
    """T-203: managers approve by Monday 12:00 after the period (a setting); the Approvals page
    shows it and marks rows that aren't approved after it as Overdue (D-133)."""
    assert approval_deadline_for(PERIOD) == datetime(2026, 10, 12, 12, 0, tzinfo=TZ)
    autumn = approval_deadline_for(date(2026, 10, 25))  # clocks go back on Nov 1
    assert autumn == datetime(2026, 11, 9, 12, 0, tzinfo=TZ) and autumn.astimezone(UTC).hour == 18
    company.approve(org.dev1)
    client = login_as(org.manager)
    html = client.get(reverse("approvals"), {"period": PERIOD.isoformat()}).content.decode()
    assert 'id="approval-deadline">Monday, Oct 12, 12:00 PM<' in html
    assert html.count(">Overdue<") == 1  # DEV2 is still pending; DEV1 is approved
    current = client.get(reverse("approvals"), {"period": NEXT.isoformat()}).content.decode()
    assert "Monday, Oct 26, 12:00 PM" in current and ">Overdue<" not in current
    settings.APPROVAL_DEADLINE_DAYS, settings.APPROVAL_DEADLINE_TIME = 3, time(9, 30)
    assert approval_deadline_for(PERIOD) == datetime(2026, 10, 13, 9, 30, tzinfo=TZ)


def test_who_must_be_approved_company_wide(org, company, project, login_as):
    """T-204: the register's people = the approvals rule for the whole company (D-54, D-134):
    employment dates, inactive staff only with a timesheet, no-manager staff approved by HR."""
    left_before = EmployeeFactory(
        employee_code="GONE1", manager=org.manager, end_date=date(2026, 9, 20), status="INACTIVE"
    )
    left_during = EmployeeFactory(
        employee_code="GONE2", manager=org.manager, end_date=date(2026, 9, 30), status="INACTIVE"
    )
    TimesheetFactory(employee=left_during, week_start=PERIOD, status="SUBMITTED")
    inactive_no_sheet = EmployeeFactory(
        employee_code="GONE3", manager=org.manager, end_date=date(2026, 10, 2), status="INACTIVE"
    )
    EmployeeFactory(employee_code="NEW1", manager=org.manager, hire_date=date(2026, 10, 15))
    EmployeeFactory(employee_code="NEW2", manager=org.manager, hire_date=date(2026, 10, 5))
    codes = {r.employee.employee_code for r in company_period_rows(PERIOD, NOW)}
    assert codes == {e.employee_code for e in vars(org).values()} | {"GONE2", "NEW2"}
    assert left_before.employee_code not in codes and inactive_no_sheet.employee_code not in codes
    mine = {r.employee.employee_code for r in period_rows(org.manager, PERIOD, NOW)}
    assert mine == {"DEV1", "DEV2", "GONE2", "NEW2"}  # the same rule, one manager's part

    groups = {g.label: g for g in preview(PERIOD, NOW).pending.groups}
    assert "DEV1" in [row.employee.employee_code for row, _ in groups["Priya Shah"].pending]
    admins = groups["HR / admins"]  # no manager: approved by HR (D-11)
    assert [row.employee.employee_code for row, _ in admins.pending] == ["CEO"]
    page = login_as(org.payroll).get(reverse("payroll_period", args=[PERIOD])).content.decode()
    table_html = page.split('id="pending-by-manager"')[1]
    assert "Priya Shah" in table_html and "HR / admins" in table_html
    assert "Locked – not submitted" in table_html  # past its deadline, never submitted


def test_open_becomes_ready(org, company, project, django_capture_on_commit_callbacks):
    """T-205: OPEN → READY after the last approval; an open change request keeps it OPEN, also
    after the deadline (Change 9: the deadline is only a reminder, D-142); payroll out of sync
    blocks it; a running period is never READY."""
    company.everyone(but=[org.dev2], now=BEFORE)
    state = period_state(PERIOD, BEFORE)
    assert (state.status, state.approved, state.required) == (OPEN, 9, 10)
    assert state.waiting_for == ["1 of 10 people are not approved yet."]
    company.approve(org.dev2, now=BEFORE)
    state = period_state(PERIOD, BEFORE)
    assert (state.status, state.ready_reason) == (READY, "ALL_APPROVED")

    raise_request(org.dev1, PERIOD, "Friday was a holiday", now=BEFORE)
    state = period_state(PERIOD, BEFORE)
    assert state.status == OPEN and state.waiting_for == [
        "1 open change request(s) on this period."
    ]
    noon = BEFORE.replace(hour=12)  # the approval deadline
    state = period_state(PERIOD, noon)
    assert state.status == OPEN and state.deadline_passed  # Overdue, but not READY
    assert period_state(NEXT, NOW).status == OPEN  # still running

    TimesheetFactory(employee=org.ops1, week_start=EARLIER, status="SUBMITTED")
    TimesheetFactory(employee=org.ops1, week_start=EARLIER + timedelta(weeks=1), status="SUBMITTED")
    approve_period(org.ops_manager, org.ops1, EARLIER, now=NOW)  # payroll write never ran
    state = period_state(EARLIER, NOW)
    assert state.status == OPEN and state.missing_records == 2
    assert "sync_payroll" in state.waiting_for[0]
    with pytest.raises(ValidationError, match="sync_payroll"):
        finalize(EARLIER, system_actor="test", now=NOW)


def test_line_values_come_from_the_week_records(org, company, make_week, project, login_as):
    """T-206: week 1, week 2 and period columns = the PayrollWeek records; Break never paid;
    the totals row adds up every line (D-134)."""
    make_week(org.dev1, PERIOD)
    second = make_week(org.dev1, PERIOD + timedelta(weeks=1), end=time(18))  # 45 h worked
    saturday = PERIOD + timedelta(days=13)
    TimeEntryFactory(
        timesheet=second, work_date=saturday, category="PTO", project=None, start_time=None,
        end_time=None, minutes=240,
    )  # fmt: skip
    TimeEntryFactory(
        timesheet=second, work_date=saturday, category="BREAK", project=None,
        start_time=time(12), end_time=time(13), minutes=60,
    )  # fmt: skip
    company.approve(org.dev1, org.dev2)
    company.rest()  # the hours appear once everyone is approved (D-142)
    lines = preview(PERIOD, NOW).lines
    dev1 = line_of(lines, "DEV1")
    week1, week2 = PayrollWeek.objects.filter(employee_code="DEV1").order_by("week_start")
    for number, record in ((1, week1), (2, week2)):
        for c in ("regular", "overtime", "pto", "sick", "holiday"):
            assert getattr(dev1, f"week{number}_{c}_minutes") == getattr(record, f"{c}_minutes")
    assert (dev1.week2_regular_minutes, dev1.week2_overtime_minutes) == (2400, 300)
    assert dev1.week2_pto_minutes == 240  # Break (60 min) is nowhere
    assert dev1.period_total_minutes == week1.total_minutes + week2.total_minutes == 5340
    assert dev1.status == "APPROVED" and dev1.approved_by_name == "Priya Shah"
    rows, totals = table(lines)
    assert totals["period"][5] == sum(r.period[5] for r in rows) == 5340 + 4800
    assert totals["pay_total"] == 5340 + 4800
    page = login_as(org.payroll).get(reverse("payroll_period", args=[PERIOD])).content.decode()
    footer = page.split('id="register-totals"')[1].split("</tr>")[0]
    assert "169.00" in footer  # 89.00 + 80.00 pay total


def test_finalize_and_export(org, company, login_as):
    """T-207: Finalize & export saves the lines and exports what they pay as ONE batch, once;
    not before READY — since Change 9 not even after the deadline while anyone is pending
    (D-135, D-142); audited."""
    company.everyone(but=[org.dev2], now=BEFORE)
    with pytest.raises(ValidationError, match="not approved"):
        finalize(PERIOD, system_actor="test", now=BEFORE)  # OPEN: no early finalize
    with pytest.raises(ValidationError, match="hasn't ended"):
        finalize(NEXT, system_actor="test", now=NOW)
    assert not PayrollRegister.objects.exists()

    client = login_as(org.payroll)
    refused = client.post(reverse("payroll_finalize", args=[PERIOD]))  # after the deadline
    assert "1 of 10 people are not approved yet." in client.get(refused.url).content.decode()
    assert not PayrollRegister.objects.exists()
    company.approve(org.dev2)  # the last approval
    response = client.post(reverse("payroll_finalize", args=[PERIOD]))
    assert response.status_code == 302
    register = PayrollRegister.objects.get()
    assert (register.status, register.export_batch, register.ready_reason) == (
        "FINALIZED",
        "EXP-0001",
        "ALL_APPROVED",
    )
    assert (register.required_count, register.approved_count) == (10, 10)
    assert register.finalized_by_code == "PAYROLL" and register.finalized_at == NOW
    weeks = PayrollWeek.objects.filter(period_start=PERIOD)
    assert set(weeks.values_list("status", "export_batch")) == {("EXPORTED", "EXP-0001")}
    lines = list(register.lines.all())
    assert len(lines) == 10
    paid_ids = sorted(i for line in lines for i in line.week_record_ids)
    assert paid_ids == sorted(weeks.values_list("pk", flat=True))
    audit = AuditLog.objects.get(action="EXPORT", entity_type="PayrollRegister")
    assert audit.actor == org.payroll and audit.after["batch"] == "EXP-0001"
    assert (audit.after["lines"], audit.after["records"], audit.after["total_minutes"]) == (
        10,
        20,
        20 * 2400,
    )

    with pytest.raises(ValidationError, match="already finalized"):
        finalize(PERIOD, system_actor="test", now=NOW)
    assert PayrollRegister.objects.count() == 1 and period_items(PERIOD).total == 0
    assert AuditLog.objects.filter(action="EXPORT").count() == 1


def test_approvable_after_finalizing_is_carried_forward(org, company, make_week):
    """T-208: no 0.00 lines any more — a register is finalized only with everyone approved
    (Change 9, D-142); someone who becomes approvable afterwards (a new hire added with a start
    date inside the finalized period) is carried forward to the next register, once (D-136)."""
    company.everyone()
    register = finalize(PERIOD, system_actor="test", now=NOW)
    assert set(register.lines.values_list("status", flat=True)) == {"APPROVED"}
    assert register.lines.count() == 10
    newcomer = EmployeeFactory(
        employee_code="LATE1", manager=org.manager, hire_date=PERIOD + timedelta(days=1)
    )
    assert period_state(PERIOD, NOW).status == "FINALIZED"  # saved registers never change
    company.approve(newcomer)  # approved after the register was finalized
    late = PayrollWeek.objects.filter(employee_code="LATE1")
    assert set(late.values_list("status", flat=True)) == {"CURRENT"}
    with time_machine.travel(AFTER_NEXT, tick=False):
        assert [r.employee_code for r in period_items(NEXT).late] == ["LATE1", "LATE1"]
        company.rest(NEXT, AFTER_NEXT)
        following = finalize(NEXT, system_actor="test", now=AFTER_NEXT)
    line = following.lines.get(employee_code="LATE1")
    assert (line.carry_regular_minutes, line.carry_total_minutes) == (4800, 4800)
    assert [item["week"] for item in line.carry_from] == ["2026-09-27", "2026-10-04"]
    assert {item["kind"] for item in line.carry_from} == {"LATE_WEEK"}
    assert line.pay_total_minutes == 4800  # its own 0.00 weeks of Oct 11 plus the carry
    assert set(late.values_list("export_batch", flat=True)) == {following.export_batch}
    assert not register.lines.filter(employee_code="LATE1").exists()  # unchanged


def test_corrections_carry_into_the_next_open_register(
    org, company, project, django_capture_on_commit_callbacks
):
    """T-209: a correction to a week of a PAID register is an adjustment in the next register
    that isn't finalized — positive or negative; carry-only people get a line; finalized
    registers never change (D-136)."""
    company.approve(org.dev1, org.dev2, period=EARLIER)
    company.rest(EARLIER)
    first = finalize(EARLIER, system_actor="test", now=NOW)
    mark_paid(EARLIER, system_actor="test", at=NOW)
    frozen = [
        (line.employee_code, line.week1_regular_minutes, line.pay_total_minutes)
        for line in first.lines.all()
    ]
    assert carry_period(EARLIER, NOW) == PERIOD
    correct(org.dev1, EARLIER, time(19), project, django_capture_on_commit_callbacks)  # +2 h OT
    correct(org.dev2, EARLIER, time(15, 30), project, django_capture_on_commit_callbacks)  # −1.5
    PayrollAdjustment.objects.create(
        employee_code="GONE1", employee_name="Old Timer", department="Ops", team="",
        week_start=EARLIER, week_period_start=EARLIER, period_start=PERIOD, old_version=1,
        new_version=2, regular_minutes=60, overtime_minutes=0, pto_minutes=0, sick_minutes=0,
        holiday_minutes=0, total_minutes=60, approved_by_code="MANAGER",
        approved_by_name="Priya Shah", approved_at=NOW, reason="x", source_timesheet_id=1,
    )  # fmt: skip
    company.rest()  # Sep 27 READY: everyone approved (D-142)
    lines = preview(PERIOD, NOW).lines
    dev1, dev2, gone = (line_of(lines, c) for c in ("DEV1", "DEV2", "GONE1"))
    assert (dev1.carry_overtime_minutes, dev1.carry_total_minutes) == (120, 120)
    assert (dev2.carry_regular_minutes, dev2.carry_total_minutes) == (-90, -90)
    assert dev1.carry_from == [{"week": "2026-09-13", "kind": "ADJUSTMENT", "total_minutes": 120}]
    assert gone.status == "CARRY_ONLY" and gone.pay_total_minutes == 60
    first.refresh_from_db()
    assert first.status == "PAID" and frozen == [
        (line.employee_code, line.week1_regular_minutes, line.pay_total_minutes)
        for line in first.lines.all()
    ]

    second = finalize(PERIOD, system_actor="test", now=NOW)
    assert set(PayrollAdjustment.objects.values_list("export_batch", flat=True)) == {
        second.export_batch
    }
    assert second.lines.get(employee_code="DEV2").pay_total_minutes == -90
    assert carry_period(EARLIER, NOW) == NEXT  # Sep 27 is finalized now: skip it


def test_registers_are_append_only(org, company):
    """T-210: registers only move FINALIZED → PAID; lines never change; nothing is deleted."""
    company.approve(org.dev1)
    company.rest()
    register = finalize(PERIOD, system_actor="test", now=NOW)
    register.export_batch = "EXP-9999"
    with pytest.raises(AppendOnlyError, match="frozen"):
        register.save()
    register.refresh_from_db()
    register.status = "PAID"
    with pytest.raises(AppendOnlyError, match="exactly paid_at"):
        register.save()  # paid without paid_at
    register.paid_at = NOW
    register.save()
    register.status, register.paid_at = "FINALIZED", None
    with pytest.raises(AppendOnlyError):
        register.save()
    line = register.lines.first()
    line.week1_regular_minutes = 1
    with pytest.raises(AppendOnlyError, match="never change"):
        line.save()
    for refused in (
        register.delete,
        line.delete,
        PayrollRegister.objects.all().delete,
        PayrollRegisterLine.objects.all().delete,
        lambda: PayrollRegisterLine.objects.update(week1_regular_minutes=0),
        lambda: PayrollRegister.objects.update(status="FINALIZED"),
    ):
        with pytest.raises(AppendOnlyError):
            refused()
    with pytest.raises(AppendOnlyError, match="starts as FINALIZED"):
        PayrollRegister.objects.create(
            period_start=EARLIER, period_end=EARLIER + timedelta(days=13), export_batch="X",
            ready_reason="DEADLINE", required_count=0, approved_count=0, finalized_at=NOW,
            finalized_by_name="test", status="PAID", paid_at=NOW,
        )  # fmt: skip


def test_mark_as_paid(org, company, project, django_capture_on_commit_callbacks):
    """T-211: Mark as paid pays the register and every record of its batch, once (D-135)."""
    company.approve(org.dev1, period=EARLIER)
    company.rest(EARLIER)
    finalize(EARLIER, system_actor="test", now=NOW)
    mark_paid(EARLIER, system_actor="test", at=NOW)
    correct(org.dev1, EARLIER, time(18), project, django_capture_on_commit_callbacks)
    company.approve(org.dev1)
    company.rest()
    register = finalize(PERIOD, actor=org.payroll, now=NOW)
    assert mark_paid(PERIOD, actor=org.payroll, at=NOW) == (20, 1)  # 10 people × 2 weeks
    register.refresh_from_db()
    assert register.status == "PAID" and register.paid_at == NOW
    in_batch = [
        *PayrollWeek.objects.filter(export_batch=register.export_batch),
        *PayrollAdjustment.objects.filter(export_batch=register.export_batch),
    ]
    assert len(in_batch) == 21 and {r.status for r in in_batch} == {"PAID"}
    pay = AuditLog.objects.get(action="PAY", entity_id=PERIOD.isoformat())
    assert pay.actor == org.payroll and (pay.after["records"], pay.after["adjustments"]) == (20, 1)
    assert mark_paid(PERIOD, actor=org.payroll, at=NOW) is None  # nothing paid twice
    assert AuditLog.objects.filter(action="PAY", entity_id=PERIOD.isoformat()).count() == 1


def read_csv(response):
    return list(csv.reader(io.StringIO(response.content.decode("utf-8-sig"))))


def test_register_csv_downloads(org, company, login_as):
    """T-212: Register CSV columns and file names; formula-safe; the detailed CSV unchanged;
    all periods with a date range; downloads change nothing; none before finalizing (D-135)."""
    org.dev1.first_name, org.dev1.last_name = '=HYPERLINK("x")', "@evil"
    org.dev1.save()
    company.approve(org.dev1, period=EARLIER)
    company.rest(EARLIER)
    company.approve(org.dev1, org.dev2)
    company.rest()
    client = login_as(org.payroll)
    assert client.get(reverse("payroll_register_csv", args=[PERIOD])).status_code == 404
    assert client.get(reverse("payroll_detail_csv", args=[PERIOD])).status_code == 404
    finalize(EARLIER, system_actor="test", now=NOW)
    finalize(PERIOD, system_actor="test", now=NOW)

    response = client.get(reverse("payroll_register_csv", args=[PERIOD]))
    name = 'filename="payroll-register_2026-09-27_to_2026-10-10_EXP-0002.csv"'
    assert name in response["Content-Disposition"]
    header, *rows = read_csv(response)
    assert header == list(REGISTER_COLUMNS) and len(rows) == 10
    dev1 = dict(zip(header, next(r for r in rows if r[0] == "DEV1"), strict=True))
    assert dev1["employee_name"] == '\'=HYPERLINK("x") @evil'  # never a formula (D-68)
    assert (dev1["week1_regular_hours"], dev1["period_total_hours"]) == ("40.00", "80.00")
    assert (dev1["carry_total_hours"], dev1["pay_total_hours"]) == ("0.00", "80.00")
    assert dev1["line_status"] == "Approved" and dev1["approved_by"] == "Priya Shah"
    ceo = dict(zip(header, next(r for r in rows if r[0] == "CEO"), strict=True))
    assert ceo["line_status"] == "Approved" and ceo["pay_total_hours"] == "0.00"  # nothing entered
    assert ceo["approved_by"] == "Hana Reed"  # approved without a submission (D-141)

    detail = client.get(reverse("payroll_detail_csv", args=[PERIOD]))
    assert (
        'filename="payroll-detail_2026-09-27_to_2026-10-10_EXP-0002.csv"'
        in (detail["Content-Disposition"])
    )
    detail_header, *detail_rows = read_csv(detail)
    assert detail_header == [name for name, _, _ in CSV_COLUMNS] and len(detail_rows) == 20

    everything = client.get(reverse("payroll_registers_csv"))
    assert (
        'filename="payroll-registers_2026-09-13_to_2026-10-10.csv"'
        in (everything["Content-Disposition"])
    )
    all_header, *all_rows = read_csv(everything)
    assert all_header == ["period_start", "period_end", "batch", *REGISTER_COLUMNS]
    assert {r[0] for r in all_rows} == {"2026-09-13", "2026-09-27"}
    ranged = client.get(reverse("payroll_registers_csv"), {"from": "2026-09-20"})
    assert {r[0] for r in read_csv(ranged)[1:]} == {"2026-09-13", "2026-09-27"}  # its period
    only_last = client.get(reverse("payroll_registers_csv"), {"from": "2026-09-27"})
    assert {r[0] for r in read_csv(only_last)[1:]} == {"2026-09-27"}
    none = client.get(reverse("payroll_registers_csv"), {"to": "2026-01-01"})
    assert read_csv(none) == [all_header]
    assert set(PayrollRegister.objects.values_list("status", flat=True)) == {"FINALIZED"}
    assert AuditLog.objects.filter(action__in=["EXPORT", "PAY"]).count() == 2  # finalize only


def test_payroll_pages(org, company, login_as):
    """T-213: /payroll/ lists ended periods newest first with status, approved x of y and pay
    total; each opens its register; older links redirect; 403 for everyone else (D-138)."""
    company.approve(org.dev1, period=EARLIER)
    company.rest(EARLIER)
    finalize(EARLIER, system_actor="test", now=NOW)
    mark_paid(EARLIER, system_actor="test", at=NOW)
    company.approve(org.dev1, org.dev2)
    client = login_as(org.payroll)
    html = client.get(reverse("payroll")).content.decode()
    table_html = html.split('id="pay-periods"')[1].split("</table>")[0]
    periods = [p for p in table_html.split('data-period="')[1:]]
    assert [p[:10] for p in periods] == ["2026-09-27", "2026-09-13"]  # newest first
    assert "Open" in periods[0] and "2 of 10" in periods[0] and "160.00" not in periods[0]
    assert "Who&#x27;s pending" in periods[0] or "Who's pending" in periods[0]
    assert "Paid" in periods[1] and "10 of 10" in periods[1] and "EXP-0001" in periods[1]
    assert "Register CSV" in periods[1]
    page = client.get(reverse("payroll_period", args=[PERIOD])).content.decode()
    assert "Open" in page.split('id="register-status"')[1]
    assert 'id="register"' not in page and 'id="finalize-dialog"' not in page  # OPEN (D-142)
    assert 'id="pending-by-manager"' in page
    assert client.get(reverse("payroll_period", args=[date(2026, 9, 30)])).url == reverse(
        "payroll_period", args=[PERIOD]
    )
    assert client.get(reverse("payroll_period", args=[NEXT])).status_code == 404  # running
    for person in (org.dev1, org.manager, org.director):
        other = login_as(person)
        assert other.get(reverse("payroll_period", args=[PERIOD])).status_code == 403
        assert other.post(reverse("payroll_finalize", args=[PERIOD])).status_code == 403
    assert not PayrollRegister.objects.filter(period_start=PERIOD).exists()


def test_build_registers_for_earlier_exports(org, company):
    """T-214: build_registers turns periods exported before registers into FINALIZED / PAID
    registers with their own batches; leftovers carry forward; safe to run again (D-137)."""
    company.approve(org.dev1, period=EARLIER)
    pay_batch(export_period(EARLIER, system_actor="test", at=NOW), system_actor="test", at=NOW)
    company.approve(org.dev1)
    export_period(PERIOD, system_actor="test", at=NOW)  # EXP-0002
    company.approve(org.dev2)
    export_period(PERIOD, system_actor="test", at=NOW)  # EXP-0003
    company.approve(org.ops1)  # approved after both exports: never exported
    out = StringIO()
    call_command("build_registers", stdout=out)
    assert "2 register(s) built." in out.getvalue()
    paid, finalized = PayrollRegister.objects.order_by("period_start")
    assert (paid.status, paid.export_batch, paid.ready_reason) == ("PAID", "EXP-0001", "BACKFILL")
    assert (finalized.status, finalized.export_batch) == ("FINALIZED", "EXP-0002+EXP-0003")
    assert sorted(finalized.lines.values_list("employee_code", flat=True)) == ["DEV1", "DEV2"]
    assert finalized.lines.get(employee_code="DEV2").period_total_minutes == 4800
    assert [r.employee_code for r in period_items(NEXT).late] == ["OPS1", "OPS1"]
    assert finalized.finalized_by_name == "build_registers"
    assert AuditLog.objects.filter(action="PUBLISH", entity_type="PayrollRegister").count() == 2
    assert build_registers(at=NOW) == []  # idempotent
    assert PayrollRegister.objects.count() == 2


def test_sync_payroll_builds_missing_registers(org, company, login_as):
    """T-215: sync_payroll builds registers for periods exported before them, once; the banner
    counts them until it does (D-137)."""
    company.approve(org.dev1)
    export_period(PERIOD, system_actor="test", at=NOW)
    client = login_as(org.payroll)
    assert (
        "1 exported pay period without a register"
        in client.get(reverse("payroll")).content.decode()
    )
    assert sync_payroll_report(at=NOW).registers == 1
    assert 'id="out-of-sync"' not in client.get(reverse("payroll")).content.decode()
    assert sync_payroll_report(at=NOW).registers == 0
    syncs = AuditLog.objects.filter(action="SYNC").order_by("pk")
    assert [s.after["registers"] for s in syncs] == [1, 0]
    assert PayrollRegister.objects.get().export_batch == "EXP-0001"
