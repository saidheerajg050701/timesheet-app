from collections import Counter, defaultdict
from datetime import date, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from audit.models import AuditLog
from directory.models import Employee, Team, User
from directory.services.demo import us_holidays
from timesheets.models import ChangeRequest, PeriodApproval, Project, TimeEntry, Timesheet

# fixed_now = Wednesday 2026-10-21, in week 2 of the pay period that starts 2026-10-12.
CURRENT_PERIOD = date(2026, 10, 12)
LAST_COMPLETED = date(2026, 9, 28)
FIRST_WEEK = date(2026, 7, 20)  # 6 completed periods back (D-27)
HISTORY = [FIRST_WEEK + timedelta(weeks=i) for i in range(13)]  # + week 1 of current period
SIGNUP_CANDIDATES = ("qa1", "ops1", "ops2")
MODELS = (Employee, Team, User, Project, Timesheet, TimeEntry, PeriodApproval, ChangeRequest)


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
    assert not rows.filter(system_actor="seed_demo").exclude(action=AuditLog.Action.CREATE).exists()
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

    edit = rows.get(action=AuditLog.Action.UPDATE)
    assert edit.actor.email == email("ops.manager")
    assert edit.change_request.status == ChangeRequest.Status.EDITED
    assert edit.before["entries"] != edit.after["entries"]
    assert rows.get(action=AuditLog.Action.REJECT).actor.email == email("eng.manager")
    assert not rows.filter(actor__isnull=True, system_actor="").exists()


def test_seeded_entries_follow_entry_rules(seeded):
    """Helper check: 15-minute steps, ≤ 24 h a day, dates in week and employment, D-18."""
    daily = defaultdict(int)
    for entry in TimeEntry.objects.select_related("timesheet__employee", "project"):
        sheet, employee = entry.timesheet, entry.timesheet.employee
        assert entry.minutes > 0 and entry.minutes % 15 == 0
        assert sheet.week_start <= entry.work_date <= sheet.week_start + timedelta(days=6)
        assert employee.hire_date <= entry.work_date  # D-19
        if entry.category == TimeEntry.Category.PROJECT:
            assert entry.project and entry.project.active  # D-18
        else:
            assert entry.project is None
        daily[(employee.pk, entry.work_date)] += entry.minutes
    assert max(daily.values()) <= 24 * 60


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
    assert us_holidays(2026) == {
        date(2026, 1, 1),
        date(2026, 1, 19),
        date(2026, 5, 25),
        date(2026, 6, 19),
        date(2026, 7, 4),
        date(2026, 9, 7),
        date(2026, 11, 26),
        date(2026, 12, 25),
    }


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
