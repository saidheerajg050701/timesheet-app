from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest
from django.db import connections
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from analytics.services.metrics import dashboard_for, outcome
from payroll.models import PayrollWeek
from tests.factories import EmployeeFactory, ProjectFactory, TimeEntryFactory, TimesheetFactory
from timesheets.models import PeriodApproval
from timesheets.services.approvals import approve_period

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now: Wed of the week of Sun Oct 18
THIS_WEEK = date(2026, 10, 18)
W = {n: THIS_WEEK - timedelta(weeks=n) for n in range(1, 13)}  # W[1] = Oct 11 … W[11] = Aug 2
ON_TIME = datetime(2026, 10, 2, 16, 0, tzinfo=TZ)


def submitted(employee, week, *, late=False, status="SUBMITTED", **extra):
    deadline = datetime.combine(week + timedelta(days=6), time(12), tzinfo=TZ)  # Saturday
    at = deadline + timedelta(days=1) if late else deadline - timedelta(hours=20)
    return TimesheetFactory(
        employee=employee, week_start=week, status=status, submitted_at=at, is_late=late, **extra
    )


def work_days(sheet, project, days=5, end=time(17)):
    for offset in range(days):
        TimeEntryFactory(
            timesheet=sheet,
            work_date=sheet.week_start + timedelta(days=1 + offset),  # from Monday
            project=project,
            end_time=end,
            minutes=(end.hour - 9) * 60,
        )
    return sheet


def dash_of(client, **params):
    return client.get(reverse("home"), params).context["dash"]


@pytest.fixture
def me(db):
    return EmployeeFactory(hire_date=date(2024, 1, 8), employee_code="ME1")


def test_dashboard_numbers_for_known_data(me, project, login_as, fixed_now):
    """T-40: on-time rate, overtime and hours by project for known data — exact numbers."""
    other = ProjectFactory(number=2, name="Mobile App")
    work_days(submitted(me, W[3]), project)  # Sep 27: on time, 40 h
    work_days(submitted(me, W[2], late=True), project, end=time(18))  # Oct 4: late, 45 h
    # Oct 11: no timesheet → missed
    draft = TimesheetFactory(employee=me, week_start=THIS_WEEK)  # current week, draft
    work_days(draft, other, days=1, end=time(18))  # 9 h, not counted for overtime (draft)

    dash = dash_of(login_as(me), weeks=4)
    p = dash.punctuality
    assert (p.on_time, p.late, p.missed, p.rate) == (1, 1, 1, 33)
    assert (dash.overtime.minutes, dash.overtime.weeks) == (300, 1)
    assert dash.projects == [("I-001", "Customer Portal", 5100), ("I-002", "Mobile App", 540)]
    assert dash.worked == 5100 + 540 and dash.expected == 4 * 2400

    html = login_as(me).get(reverse("home"), {"weeks": 4}).content.decode()
    assert 'id="on-time-rate">33%<' in html and 'id="overtime-hours">5.00<' in html
    assert 'I-001 Customer Portal</th><td class="text-end">85.00' in html


def test_range_filter(me, project, login_as, fixed_now):
    """T-115: 4 / 12 / 26 weeks ending with the current week; invalid → 12 (D-74)."""
    work_days(submitted(me, W[1]), project)
    client = login_as(me)
    four = dash_of(client, weeks=4)
    assert four.starts == [W[3], W[2], W[1], THIS_WEEK]
    assert four.punctuality.counted == 3  # current week not counted yet
    twelve = dash_of(client, weeks=12)
    assert len(twelve.starts) == 12 and twelve.starts[-1] == THIS_WEEK
    assert twelve.punctuality.counted == 11 and twelve.punctuality.missed == 10
    assert len(dash_of(client, weeks=26).starts) == 26
    for bad in ("7", "abc", "-4", ""):
        assert dash_of(client, weeks=bad).weeks == 12
    html = client.get(reverse("home"), {"weeks": 26}).content.decode()
    assert 'href="?weeks=26" aria-current="page"' in html


def test_on_time_late_missed_edge_cases(me, project, login_as, fixed_now):
    """T-116: first submission decides; never submitted = missed; current week not counted."""
    setup = {
        W[1]: TimesheetFactory(employee=me, week_start=W[1], status="DRAFT"),  # draft past deadline
        # W[2]: no timesheet at all
        W[3]: submitted(me, W[3], late=True),  # late
        W[4]: submitted(me, W[4]),  # on time, reopened and resubmitted later (still on time)
        W[5]: submitted(me, W[5], late=True),  # missed, unlocked, then submitted late
        W[6]: submitted(me, W[6], status="LOCKED"),  # on time, reopened, window expired: re-locked
        W[7]: TimesheetFactory(  # missed, reopened, not resubmitted yet
            employee=me, week_start=W[7], status="REOPENED", reopen_until=NOW + timedelta(days=1)
        ),
        THIS_WEEK: submitted(me, THIS_WEEK),  # current week, already submitted
    }
    assert len(setup) == 7  # every case except W[2], which has no timesheet
    dash = dashboard_for(me, 8, NOW)
    kinds = {row.week_start: outcome(row, NOW) for row in dash.rows}
    assert kinds == {
        W[7]: "missed",
        W[6]: "on_time",
        W[5]: "late",
        W[4]: "on_time",
        W[3]: "late",
        W[2]: "missed",
        W[1]: "missed",
        THIS_WEEK: None,
    }
    assert (dash.punctuality.on_time, dash.punctuality.late, dash.punctuality.missed) == (2, 2, 3)

    # The /timesheets/ Missed badge uses the same rule (D-75).
    listing = login_as(me).get(reverse("timesheets")).content.decode()

    def row_of(week):
        return listing.split(f'data-week="{week.isoformat()}"')[1].split("</tr>")[0]

    assert "Missed" in row_of(W[1]) and "Missed" in row_of(W[2]) and "Missed" in row_of(W[7])
    assert "Missed" not in row_of(W[6]) and "Missed" not in row_of(W[3])


def test_new_hire_and_deactivated_employee(project, login_as, fixed_now):
    """T-117: weeks outside employment never count; partial weeks are prorated (D-19)."""
    joiner = EmployeeFactory(hire_date=date(2026, 10, 7), employee_code="NEW1")  # Wed of W[2]
    dash = dashboard_for(joiner, 12, NOW)
    assert [row.week_start for row in dash.rows] == [W[2], W[1], THIS_WEEK]
    assert dash.rows[0].summary.expected == 1440  # Wed–Fri
    assert dash.punctuality.missed == 2  # W[2], W[1]; nothing before the hire date
    html = login_as(joiner).get(reverse("home")).content.decode()
    assert "Started on Oct 7, 2026" in html

    leaver = EmployeeFactory(
        hire_date=date(2024, 1, 8), end_date=date(2026, 9, 30), status="INACTIVE"
    )  # left on Wed of W[3]
    work_days(submitted(leaver, W[3]), project, days=3)
    dash = dashboard_for(leaver, 4, NOW)
    assert [row.week_start for row in dash.rows] == [W[3]]
    assert dash.rows[0].summary.expected == 1440 and dash.rows[0].summary.worked == 1440
    assert dash.punctuality.counted == 1 and dash.punctuality.on_time == 1
    assert dash.overtime.minutes == 0


@pytest.mark.django_db(databases=["default", "payroll"])
def test_dashboard_overtime_matches_payroll(
    org, make_week, login_as, django_capture_on_commit_callbacks
):
    """T-118: dashboard overtime equals the payroll split for approved weeks; drafts excluded."""
    make_week(org.dev1, date(2026, 9, 27))
    make_week(org.dev1, date(2026, 10, 4), end=time(18))  # 45 h → 5 h overtime
    with django_capture_on_commit_callbacks(execute=True):
        approve_period(org.manager, org.dev1, date(2026, 9, 27), now=NOW)
    draft = TimesheetFactory(employee=org.dev1, week_start=THIS_WEEK)
    for offset in range(3):  # 3 × 15 h draft days: would be overtime, but drafts don't count
        TimeEntryFactory(
            timesheet=draft,
            work_date=THIS_WEEK + timedelta(days=1 + offset),  # Mon–Wed
            start_time=time(6),
            end_time=time(21),
            minutes=900,
        )
    dash = dash_of(login_as(org.dev1), weeks=4)
    payroll = sum(PayrollWeek.objects.values_list("overtime_minutes", flat=True))
    assert payroll == 300 and dash.overtime.minutes == payroll
    by_week = {row.week_start: row.split.overtime for row in dash.rows if row.split}
    assert by_week == {r.week_start: r.overtime_minutes for r in PayrollWeek.objects.all()}


def test_only_own_data(org, project, login_as, fixed_now):
    """T-119: / always shows the logged-in user's numbers; no parameter selects someone else."""
    work_days(submitted(org.dev2, W[1]), project, end=time(19))  # dev2: 50 h
    client = login_as(org.dev1)
    for params in ({}, {"employee": "DEV2"}, {"employee_code": "DEV2", "weeks": 4}):
        dash = dash_of(client, **params)
        assert dash.employee == org.dev1 and dash.worked == 0 and dash.overtime.minutes == 0
    html = client.get(reverse("home"), {"employee": "DEV2"}).content.decode()
    assert 'data-employee="DEV1"' in html and "DEV2" not in html.split('id="dashboard"')[1]


@pytest.mark.django_db
def test_empty_state(login_as, fixed_now):
    """T-120: a new hire with no history gets friendly messages instead of charts."""
    newbie = EmployeeFactory(hire_date=THIS_WEEK, employee_code="NEW2")
    response = login_as(newbie).get(reverse("home"))
    html = response.content.decode()
    assert response.status_code == 200
    assert "No timesheets in this range yet." in html
    assert "No finished weeks in this range yet." in html
    assert "<canvas" not in html
    assert 'id="current-status">Not started<' in html


def test_viewing_writes_nothing_and_queries_are_bounded(me, project, login_as, fixed_now):
    """T-121: viewing never writes; the same number of queries for 4 and 26 weeks (D-34)."""
    for n in range(1, 12):
        work_days(submitted(me, W[n], late=n % 3 == 0), project, days=2)
    PeriodApproval.objects.create(employee=me, period_start=date(2026, 9, 27), status="APPROVED")
    client = login_as(me)
    client.get(reverse("home"))  # warm up the session

    counts = {}
    for weeks in (4, 26):
        with CaptureQueriesContext(connections["default"]) as queries:
            assert client.get(reverse("home"), {"weeks": weeks}).status_code == 200
        writes = [
            q["sql"] for q in queries if q["sql"].split()[0] in ("INSERT", "UPDATE", "DELETE")
        ]
        assert writes == []
        counts[weeks] = len(queries)
    assert counts[4] == counts[26]


def test_categories_break_outcomes_and_current_week(me, project, login_as, fixed_now):
    """T-122: Break shown apart and never in totals; outcomes per period; current-week card."""
    sheet = submitted(me, W[3])
    rows = [
        ("PROJECT", time(9), time(12), 180, project),
        ("BREAK", time(12), time(12, 30), 30, None),
        ("MEETING", time(12, 30), time(17, 30), 300, None),
    ]
    for category, start, end, minutes, prj in rows:
        TimeEntryFactory(
            timesheet=sheet,
            work_date=W[3] + timedelta(days=1),  # Monday
            category=category,
            project=prj,
            start_time=start,
            end_time=end,
            minutes=minutes,
        )
    TimeEntryFactory(
        timesheet=sheet,
        work_date=W[3] + timedelta(days=2),  # Tuesday
        category="PTO",
        project=None,
        start_time=None,
        end_time=None,
        minutes=480,
        reason="Vacation",
    )
    PeriodApproval.objects.create(employee=me, period_start=date(2026, 9, 27), status="APPROVED")
    PeriodApproval.objects.create(employee=me, period_start=date(2026, 9, 13), status="REJECTED")
    client = login_as(me)
    dash = dash_of(client, weeks=12)
    assert dash.categories.rows == [("Project work", 180), ("Meetings", 300), ("PTO", 480)]
    assert dash.categories.total == 960 and dash.categories.break_minutes == 30
    assert dash.worked == 480  # Break and leave are not hours worked
    statuses = {p.period_start: p.status for p in dash.periods}
    assert statuses[date(2026, 9, 27)] == "APPROVED" and statuses[date(2026, 9, 13)] == "REJECTED"
    assert statuses[date(2026, 10, 11)] == "IN_PROGRESS" and statuses[date(2026, 8, 2)] == "PENDING"
    assert dash.outcome_counts == {"APPROVED": 1, "REJECTED": 1, "PENDING": 3}

    html = client.get(reverse("home"), {"weeks": 12}).content.decode()
    assert 'id="categories-total">16.00<' in html and 'id="break-hours">0.50<' in html
    assert 'data-deadline="2026-10-24T12:00:00-05:00"' in html  # the server's deadline
    assert 'id="current-status">Not started<' in html and "3 d 2 h 0 min" in html
    assert 'id="dashboard-data" type="application/json"' in html  # chart data via json_script
