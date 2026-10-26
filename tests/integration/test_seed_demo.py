from collections import Counter, defaultdict
from datetime import date, time, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from audit.models import AuditLog
from directory.models import Employee, Team, User
from directory.services.demo import us_holidays
from payroll.models import PayrollAdjustment, PayrollRegister, PayrollWeek
from payroll.services.export import corrections
from payroll.services.publish import out_of_sync
from payroll.services.register import READY, period_state, preview, unregistered_periods
from timesheets.models import ChangeRequest, PeriodApproval, Project, TimeEntry, Timesheet
from timesheets.services.validation import validate_entries

# fixed_now = Wednesday 2026-10-21, in week 2 of the pay period that starts Sun 2026-10-11.
CURRENT_PERIOD = date(2026, 10, 11)
LAST_COMPLETED = date(2026, 9, 27)
FIRST_WEEK = date(2026, 7, 19)  # 6 completed periods back (D-27), a Sunday
HISTORY = [FIRST_WEEK + timedelta(weeks=i) for i in range(13)]  # + week 1 of current period
SIGNUP_CANDIDATES = ("qa1", "ops1", "ops2")
MODELS = (
    Employee,
    Team,
    User,
    Project,
    Timesheet,
    TimeEntry,
    PeriodApproval,
    ChangeRequest,
    PayrollWeek,
)
pytestmark = pytest.mark.django_db(databases=["default", "payroll"])  # seed fills both (D-73)


@pytest.fixture
def seeded(db, demo_password, fixed_now):
    out = StringIO()
    call_command("seed_demo", stdout=out)
    return out.getvalue()


def email(local):
    return f"{local}@yourcompany.com"


def depth(employee):
    level, seen = 1, {employee.pk}
    while employee.manager_id and employee.manager_id not in seen:
        employee = employee.manager
        seen.add(employee.pk)
        level += 1
    return level


def test_seed_builds_the_demo_company(seeded, demo_password):
    """T-41: seed_demo builds ~50 employees, 3 sign-up candidates without accounts, history."""
    assert "Demo company created" in seeded
    employees = list(Employee.objects.select_related("team", "manager"))
    assert len(employees) == 50
    # Every week and pay period starts on a Sunday (D-111, D-113).
    assert set(Timesheet.objects.dates("week_start", "day")) == set(HISTORY)
    assert all(d.weekday() == 6 for d in HISTORY)
    starts = PeriodApproval.objects.values_list("period_start", flat=True)
    assert {d.weekday() for d in starts} == {6}
    assert Team.objects.count() == 9
    assert Team.objects.values("department").distinct().count() == 6
    assert max(depth(e) for e in employees) == 4

    # Accounts: every ACTIVE employee except the three sign-up candidates; never former@.
    without_account = Employee.objects.filter(account__isnull=True)
    assert set(without_account.values_list("email", flat=True)) == {
        *(email(n) for n in SIGNUP_CANDIDATES),
        email("former"),
    }
    for local in SIGNUP_CANDIDATES:
        assert Employee.objects.get(email=email(local)).status == Employee.Status.ACTIVE
    assert User.objects.count() == 46
    assert all(p.startswith("argon2") for p in User.objects.values_list("password", flat=True))
    assert User.objects.get(email=email("dev1")).check_password(demo_password)
    assert User.objects.get(email=email("hr")).is_superuser  # admin flag synced (D-13)

    # Projects: 8, one inactive and never used.
    assert Project.objects.count() == 8
    inactive = Project.objects.get(active=False)
    assert not TimeEntry.objects.filter(project=inactive).exists()

    # History: period-aligned weeks (D-27), nothing for the current week.
    weeks = set(Timesheet.objects.values_list("week_start", flat=True))
    assert sorted(weeks) == HISTORY
    dev1_weeks = Timesheet.objects.filter(employee__email=email("dev1"))
    assert sorted(dev1_weeks.values_list("week_start", flat=True)) == HISTORY
    assert dev1_weeks.filter(status=Timesheet.Status.LOCKED).exists()  # a missed week

    # Mix: mostly on time, some late (each unlocked through a change request), a few missed.
    statuses = Counter(Timesheet.objects.values_list("status", flat=True))
    late = Timesheet.objects.filter(is_late=True)
    assert 0 < late.count() < statuses[Timesheet.Status.APPROVED] / 10
    assert 0 < statuses[Timesheet.Status.LOCKED] < statuses[Timesheet.Status.APPROVED] / 10
    for sheet in late:
        assert sheet.change_requests.filter(status=ChangeRequest.Status.UNLOCKED).count() == 1

    # One rejected period (D-07, D-21) and one open change request.
    rejected = PeriodApproval.objects.get(status=PeriodApproval.Status.REJECTED)
    assert rejected.period_start == LAST_COMPLETED and rejected.comment
    reopened = Timesheet.objects.filter(employee=rejected.employee, status="REOPENED")
    assert reopened.count() == 2
    for sheet in reopened:
        assert sheet.manager_note == rejected.comment
        assert sheet.reopen_until >= rejected.decided_at + timedelta(hours=48)
    assert ChangeRequest.objects.filter(status=ChangeRequest.Status.OPEN).count() == 1
    assert ChangeRequest.objects.filter(status=ChangeRequest.Status.EDITED).count() == 1

    # Payroll: every approved week has a live payroll record (B.7, D-73).
    assert PayrollWeek.objects.exists() and out_of_sync() == (0, 0)


def test_seed_refuses_to_run_twice(seeded):
    """T-42: a second seed_demo run refuses and leaves the data unchanged."""
    counts = {model: model.objects.count() for model in MODELS}
    passwords = dict(User.objects.values_list("email", "password"))
    with pytest.raises(CommandError, match="already has data"):
        call_command("seed_demo", stdout=StringIO())
    assert {model: model.objects.count() for model in MODELS} == counts
    assert dict(User.objects.values_list("email", "password")) == passwords


def test_seed_approvals_follow_the_rules(seeded):
    """T-56: seeded approvals obey D-06 and D-11."""
    sheets = defaultdict(list)
    for sheet in Timesheet.objects.all():
        period_start = sheet.week_start - timedelta(
            weeks=(sheet.week_start - FIRST_WEEK).days // 7 % 2
        )
        sheets[(sheet.employee_id, period_start)].append(sheet)

    approvals = PeriodApproval.objects.select_related("employee", "approver")
    assert not approvals.filter(period_start=CURRENT_PERIOD).exists()
    assert not approvals.filter(period_start=LAST_COMPLETED, status="APPROVED").exists()
    for approval in approvals:
        weeks = sheets[(approval.employee_id, approval.period_start)]
        if approval.status == PeriodApproval.Status.APPROVED:
            assert len(weeks) == 2
            assert all(w.status == Timesheet.Status.APPROVED for w in weeks)
        else:
            assert approval.status == "REJECTED" or approval.approver is None
            assert not any(w.status == Timesheet.Status.APPROVED for w in weeks)
        if approval.period_start not in (LAST_COMPLETED, CURRENT_PERIOD):
            # A completed, older period is approved exactly when nothing is LOCKED (D-06).
            has_locked = any(w.status == Timesheet.Status.LOCKED for w in weeks)
            assert (approval.status == PeriodApproval.Status.APPROVED) == (not has_locked)
        if approval.approver:  # D-11: direct manager, HR for the CEO, never self
            assert approval.approver != approval.employee
            expected = approval.employee.manager or Employee.objects.get(email=email("hr"))
            assert approval.approver == expected
    ceo_approvals = approvals.filter(employee__email=email("ceo"), status="APPROVED")
    assert ceo_approvals.exists()
    assert all(a.approver.email == email("hr") for a in ceo_approvals)


def test_seed_audit_rows_name_the_right_actor(seeded):
    """T-57: seed's own rows use system_actor seed_demo; human decisions name the manager (D-14)."""
    rows = AuditLog.objects.select_related("actor", "change_request")
    assert set(rows.exclude(system_actor="").values_list("system_actor", flat=True)) == {
        "seed_demo"
    }
    seed_actions = {AuditLog.Action.CREATE, AuditLog.Action.PUBLISH, AuditLog.Action.SUPERSEDE}
    assert not rows.filter(system_actor="seed_demo").exclude(action__in=seed_actions).exists()
    assert rows.filter(system_actor="seed_demo", entity_type="Employee").count() == 50
    assert rows.filter(system_actor="seed_demo", entity_type="DemoData").count() == 1

    approved = PeriodApproval.objects.filter(status="APPROVED").count()
    assert rows.filter(action=AuditLog.Action.APPROVE).count() == approved
    for row in rows.filter(action__in=["APPROVE", "REJECT"]):
        approval = PeriodApproval.objects.get(pk=row.entity_id)
        assert row.actor == approval.approver and row.created_at == approval.decided_at

    hr = Employee.objects.get(email=email("hr"))
    unlocks = rows.filter(action=AuditLog.Action.UNLOCK)
    assert unlocks.count() == Timesheet.objects.filter(is_late=True).count()
    for row in unlocks:
        request = row.change_request
        assert request.status == ChangeRequest.Status.UNLOCKED
        assert row.actor == request.reviewer == (request.requester.manager or hr)

    raised = rows.filter(action=AuditLog.Action.CREATE, entity_type="ChangeRequest")
    assert raised.count() == ChangeRequest.objects.count()
    for row in raised:  # raising a request names the employee who raised it (D-46)
        assert row.actor == row.change_request.requester and not row.system_actor

    edit = rows.get(action=AuditLog.Action.UPDATE)
    assert edit.actor.email == email("ops.manager")
    assert edit.change_request.status == ChangeRequest.Status.EDITED
    assert edit.before["entries"] != edit.after["entries"]
    assert rows.get(action=AuditLog.Action.REJECT).actor.email == email("eng.manager")
    assert not rows.filter(actor__isnull=True, system_actor="").exists()


def test_seeded_entries_pass_the_entry_rules(seeded):
    """T-80: every seeded week passes validate_entries, with reasons, times and lunch breaks."""
    sheets = Timesheet.objects.select_related("employee").prefetch_related("entries__project")
    for sheet in sheets:
        entries = list(sheet.entries.all())
        assert validate_entries(sheet.employee, sheet.week_start, entries) == [], sheet
        for entry in entries:
            assert entry.reason.strip()
            timed = entry.category in TimeEntry.TIMED
            assert (entry.start_time is not None) == timed == (entry.end_time is not None)
    breaks = TimeEntry.objects.filter(category="BREAK")
    assert breaks.count() > 1000 and not breaks.filter(project__isnull=False).exists()
    assert set(breaks.values_list("reason", flat=True)) == {"Lunch break"}
    assert TimeEntry.objects.filter(category__in=TimeEntry.LEAVE, start_time__isnull=True).exists()
    holiday = TimeEntry.objects.filter(category="HOLIDAY").first()
    assert holiday.reason == "Public holiday: Labor Day"
    earliest = TimeEntry.objects.filter(start_time__isnull=False).order_by("start_time").first()
    assert time(8, 0) <= earliest.start_time <= time(9, 30)


def test_seed_history_includes_holidays_part_timers_and_new_hires(seeded):
    """Helper check: Labor Day is a HOLIDAY, part-timers exist, recent hires have partial weeks."""
    labor_day = date(2026, 9, 7)
    assert labor_day in us_holidays(2026)
    assert TimeEntry.objects.filter(work_date=labor_day, category="HOLIDAY").count() >= 40
    assert set(Employee.objects.values_list("expected_weekly_minutes", flat=True)) == {
        2400,
        1800,
        1200,
    }
    recent = Employee.objects.filter(hire_date__gt=FIRST_WEEK)
    assert recent.count() == 3
    for employee in recent:
        first_sheet = employee.timesheets.order_by("week_start").first()
        assert first_sheet.week_start < employee.hire_date
        assert first_sheet.entries.order_by("work_date").first().work_date >= employee.hire_date


def test_us_holidays_2026():
    """Helper check: holiday dates for 2026."""
    holidays = us_holidays(2026)
    assert set(holidays) == {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 4),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }
    assert holidays[date(2026, 9, 7)] == "Labor Day"


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("password", "message"), [("", "Set DEMO_PASSWORD"), ("password", "not allowed")]
)
def test_seed_needs_a_strong_demo_password(settings, password, message):
    """Helper check: an empty or weak DEMO_PASSWORD is refused before anything is written."""
    settings.DEMO_PASSWORD = password
    with pytest.raises(CommandError, match=message):
        call_command("seed_demo", stdout=StringIO())
    assert not Employee.objects.exists()


def test_seed_fills_the_payroll_database(seeded, fixed_now):
    """T-114: seed payroll: approved weeks live; older periods' registers PAID, the next one
    FINALIZED, the newest READY; one correction, settled with a +1 h adjustment carried
    forward to the register that isn't finalized yet (D-118, D-126, D-137)."""
    assert out_of_sync() == (0, 0)
    by_period = defaultdict(Counter)
    for period, status in PayrollWeek.objects.values_list("period_start", "status"):
        by_period[period][status] += 1
    periods = sorted(by_period)  # Jul 20, Aug 3, Aug 17, Aug 31, Sep 14 (approved periods)
    assert len(periods) == 5
    for period in periods[:3]:  # oldest: paid (plus the correction in the first one)
        assert set(by_period[period]) <= {"PAID", "SUPERSEDED", "SETTLED"}
        assert by_period[period]["PAID"] > 0
    assert set(by_period[periods[3]]) == {"EXPORTED"}
    assert set(by_period[periods[4]]) == {"CURRENT"}
    batches = sorted(
        set(PayrollWeek.objects.exclude(export_batch="").values_list("export_batch", flat=True))
    )
    assert batches == ["EXP-0001", "EXP-0002", "EXP-0003", "EXP-0004"]

    (correction,) = corrections()
    assert correction.old.status == "SUPERSEDED" and correction.old.paid_at is not None
    assert correction.new.version == 2 and correction.new.status == "SETTLED"  # not re-exported
    assert correction.difference == 60
    (adjustment,) = PayrollAdjustment.objects.all()
    assert correction.adjustment == adjustment and adjustment.status == "CURRENT"  # Scheduled
    assert (adjustment.regular_minutes, adjustment.total_minutes) == (60, 60)
    # Carried to the first period without an export batch: Sep 13, whose weeks still wait to
    # be exported, so the +1 h goes out in that same pay run (D-121).
    assert adjustment.week_period_start == periods[0] and adjustment.period_start == periods[4]
    clerk = Employee.objects.get(email="payroll@yourcompany.com")
    assert set(
        AuditLog.objects.filter(action__in=["EXPORT", "PAY"]).values_list("actor", flat=True)
    ) == {clerk.pk}
    published = AuditLog.objects.filter(action="PUBLISH")
    assert published.filter(entity_type="PayrollWeek").count() == PayrollWeek.objects.count()
    assert published.filter(entity_type="PayrollAdjustment").count() == 1

    registers = list(PayrollRegister.objects.order_by("period_start"))  # Change 8
    assert [(r.period_start, r.status) for r in registers] == [
        (periods[0], "PAID"),
        (periods[1], "PAID"),
        (periods[2], "PAID"),
        (periods[3], "FINALIZED"),
    ]
    assert [r.export_batch for r in registers] == batches and not unregistered_periods()
    for register in registers:  # one line per person who had to be approved
        assert register.lines.count() == register.required_count >= register.approved_count
        unpaid = register.lines.exclude(status="APPROVED").count()
        assert unpaid == register.required_count - register.approved_count
        assert (
            register.ready_reason == "DEADLINE"
            and register.finalized_by_code == clerk.employee_code
        )
    newest = period_state(periods[4], fixed_now)
    assert newest.status == READY and not newest.finalized
    carried = next(
        line for line in preview(periods[4], fixed_now).lines
        if line.employee_code == adjustment.employee_code
    )  # fmt: skip
    assert carried.carry_total_minutes == 60 and carried.carry_from[0]["kind"] == "ADJUSTMENT"


def test_seed_still_refuses_when_payroll_has_data(seeded):
    """Helper check: the second run refuses before touching either database (T-42 with payroll)."""
    before = PayrollWeek.objects.count()
    with pytest.raises(CommandError, match="already has data"):
        call_command("seed_demo", stdout=StringIO())
    assert PayrollWeek.objects.count() == before
