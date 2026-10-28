import time as clock
from datetime import date, datetime, time, timedelta
from io import StringIO
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.core.management import call_command
from django.db import connections
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from directory.models import Employee, Team
from tests.factories import EmployeeFactory, TeamFactory, TimeEntryFactory, UserFactory
from timesheets.models import PeriodApproval, TimeEntry, Timesheet

TZ = ZoneInfo("America/Chicago")
NOW = datetime(2026, 10, 21, 10, 0, tzinfo=TZ)  # fixed_now
THIS_WEEK = date(2026, 10, 18)
W1, W2, W3 = date(2026, 10, 11), date(2026, 10, 4), date(2026, 9, 27)  # 1–3 weeks back


def board_of(client, **params):
    return client.get(reverse("team"), params).context["board"]


def codes(board):
    return [p.employee.employee_code for p in board.people]


def writes(queries):
    return [q["sql"] for q in queries if q["sql"].split()[0] in ("INSERT", "UPDATE", "DELETE")]


@pytest.fixture
def known_team(org, make_week, project, fixed_now):
    """The director's tree (MANAGER, DEV1, DEV2) with known weeks in the last 4 weeks."""
    make_week(org.dev1, W3)  # 40 h on time
    make_week(org.dev1, W2, end=time(18), is_late=True)  # 45 h late → 5 h overtime
    # dev1, Oct 11: nothing → missed
    make_week(org.dev1, THIS_WEEK, "DRAFT", days=1)  # 8 h draft this week
    week = make_week(org.dev2, W3, days=4)  # 32 h + 8 h PTO on Friday
    TimeEntryFactory(
        timesheet=week,
        work_date=W3 + timedelta(days=5),  # Friday
        category="PTO",
        project=None,
        start_time=None,
        end_time=None,
        minutes=480,
        reason="Vacation",
    )
    make_week(org.dev2, W2)
    make_week(org.dev2, W1)
    PeriodApproval.objects.create(employee=org.dev2, period_start=W3, status="APPROVED")
    return org


def test_team_metrics_for_known_data(known_team, login_as):
    """T-123: team metrics for known data — exact numbers per person and per week."""
    org = known_team
    board = board_of(login_as(org.director), weeks=4)
    people = {p.employee.employee_code: p for p in board.people}
    assert sorted(people) == ["DEV1", "DEV2", "MANAGER"]

    dev1, dev2, manager = people["DEV1"], people["DEV2"], people["MANAGER"]
    assert (dev1.worked, dev1.utilization, dev1.overtime.minutes, dev1.pending) == (
        5580,
        71,
        300,
        1,
    )
    p = dev1.punctuality
    assert (p.on_time, p.late, p.missed, p.rate) == (1, 1, 1, 33)
    assert (dev2.worked, dev2.utilization, dev2.punctuality.rate, dev2.pending) == (
        6720,
        100,
        100,
        0,
    )
    assert (manager.worked, manager.utilization, manager.punctuality.missed) == (0, 0, 3)
    assert board.worked == 12300 and board.utilization == 56  # 11820 / 21120
    assert [(w.week_start, w.worked, w.expected) for w in board.by_week] == [
        (W3, 4320, 7200),
        (W2, 5100, 7200),
        (W1, 2400, 7200),
        (THIS_WEEK, 480, 7200),
    ]
    assert board.projects == [("I-001", "Customer Portal", 12300)]
    html = login_as(org.director).get(reverse("team"), {"weeks": 4}).content.decode()
    assert 'id="team-utilization">56%<' in html and 'id="team-worked">205.00<' in html
    assert 'id="team-data" type="application/json"' in html


def test_utilization_rule(org, make_week, project, login_as, fixed_now):
    """T-124: worked ÷ (expected − leave) on finished weeks; Break never; weighted average."""
    part_timer = EmployeeFactory(
        manager=org.manager, expected_weekly_minutes=1200, employee_code="PT1"
    )
    make_week(part_timer, W1, days=5, end=time(13))  # 5 × 4 h = 20 h of 20 h → 100%
    week = make_week(org.dev1, W1, days=5, end=time(13))  # 20 h of 40 h → 50% …
    for offset in range(5):  # … long breaks never count as hours worked
        TimeEntryFactory(
            timesheet=week,
            work_date=W1 + timedelta(days=1 + offset),  # Mon–Fri
            category="BREAK",
            project=None,
            start_time=time(13),
            end_time=time(17),
            minutes=240,
            reason="Break",
        )
    leave = make_week(org.dev2, W1, days=0)  # a full week of PTO: nothing available
    for offset in range(5):
        TimeEntryFactory(
            timesheet=leave,
            work_date=W1 + timedelta(days=1 + offset),  # Mon–Fri
            category="PTO",
            project=None,
            start_time=None,
            end_time=None,
            minutes=480,
            reason="Vacation",
        )
    make_week(org.dev1, THIS_WEEK, "DRAFT", end=time(21))  # current week: not counted yet
    EmployeeFactory(manager=org.manager, hire_date=THIS_WEEK, employee_code="NEW1")
    client = login_as(org.manager)
    stats = {p.employee.employee_code: p for p in board_of(client, weeks=4).people}

    def numbers(code):
        s = stats[code]
        return s.worked, s.finished_worked, s.available, s.utilization

    # 4 weeks = Sep 27, Oct 4, Oct 11 (finished) + Oct 18 (current, not counted)
    assert numbers("PT1") == (1200, 1200, 3 * 1200, 33)
    assert numbers("DEV1") == (1200 + 3600, 1200, 3 * 2400, 17)  # breaks add nothing
    assert numbers("DEV2") == (0, 0, 2 * 2400, 0)  # the PTO week is not available
    assert numbers("NEW1") == (0, 0, 0, None)  # nothing available yet → "—"
    board = board_of(client, weeks=4)
    assert board.utilization == 15  # weighted: 2400 / 15600, not the mean of 33, 17 and 0
    html = client.get(reverse("team"), {"weeks": 4}).content.decode()
    new1 = html.split('data-employee="NEW1"')[1].split("</tr>")[0]
    assert "—" in new1


def test_whole_tree_vs_direct_and_team_filter(org, login_as, fixed_now):
    """T-125: whole tree vs direct reports; team filter narrows; the viewer is never listed."""
    other = TeamFactory(name="Data", department="Technology")
    EmployeeFactory(manager=org.manager, team=other, employee_code="DATA1")
    client = login_as(org.director)
    tree = set(codes(board_of(client)))
    assert tree == {"MANAGER", "DEV1", "DEV2", "DATA1"} and "DIRECTOR" not in tree
    assert set(codes(board_of(client, scope="direct"))) == {"MANAGER"}
    platform = Team.objects.get(name="Platform")
    filtered = board_of(client, team=platform.pk)
    assert set(codes(filtered)) == {"MANAGER", "DEV1", "DEV2"}
    assert {name for _, name in filtered.teams} == {"Platform", "Data"}
    assert set(codes(board_of(client, team="nope"))) == tree  # bad value = all teams


def test_access_rules(org, login_as, fixed_now):
    """T-126: 403 for employees, payroll-only and outside the tree; payroll managers: own tree."""
    week = reverse("team_member_week", args=["DEV2", W1])
    for person in (org.dev1, org.payroll):  # employee; payroll flag without reports (D-12)
        client = login_as(person)
        assert client.get(reverse("team")).status_code == 403
        assert client.get(reverse("team_member", args=["DEV2"])).status_code == 403
        assert client.get(week).status_code == 403
    manager = login_as(org.manager)
    assert manager.get(reverse("team_member", args=["OPS1"])).status_code == 403
    assert manager.get(reverse("team_member_week", args=["OPS1", W1])).status_code == 403
    assert manager.get(reverse("team_member", args=["MANAGER"])).status_code == 200  # own
    assert manager.get(reverse("team_member", args=["NOPE"])).status_code == 404
    finance = login_as(org.finance)  # payroll + manager: own tree only
    assert codes(board_of(finance)) == ["PAYROLL"]
    assert finance.get(reverse("team_member", args=["DEV1"])).status_code == 403


def test_admin_sees_everyone(org, login_as, fixed_now):
    """T-127: an admin's whole-tree view lists everyone except themselves (D-81)."""
    everyone = set(Employee.objects.exclude(pk=org.hr.pk).values_list("employee_code", flat=True))
    assert set(codes(board_of(login_as(org.hr)))) == everyone
    assert codes(board_of(login_as(org.hr), scope="direct")) == []
    html = login_as(org.hr).get(reverse("team"), {"scope": "direct"}).content.decode()
    assert "Nobody matches these filters" in html
    assert set(codes(board_of(login_as(org.ceo), scope="direct"))) == {
        "HR",
        "DIRECTOR",
        "OPSMGR",
        "FINANCE",
    }
    assert login_as(org.hr).get(reverse("team_member", args=["OPS1"])).status_code == 200


def test_this_weeks_compliance(org, make_week, login_as, fixed_now):
    """T-128: not submitted yet before Saturday 12:00, missed after; others not listed (D-83)."""
    make_week(org.dev1, THIS_WEEK)  # submitted
    leaver = EmployeeFactory(
        manager=org.manager, end_date=date(2026, 10, 16), employee_code="LEFT1"
    )
    make_week(leaver, W1, days=4)
    client = login_as(org.manager)
    items = {i.employee.employee_code: i.label for i in board_of(client).compliance}
    assert items == {"DEV2": "Not submitted yet"}  # not DEV1 (submitted), not LEFT1 (left)
    assert "LEFT1" in codes(board_of(client))  # still in the table
    with time_machine.travel(datetime(2026, 10, 24, 12, 0, tzinfo=TZ), tick=False):
        items = {i.employee.employee_code: i.label for i in board_of(client).compliance}
    assert items == {"DEV2": "Missed"}


def test_inactive_employees_only_with_timesheets(org, make_week, login_as, fixed_now):
    """T-129: inactive employees appear only with a timesheet in the range (D-81)."""
    EmployeeFactory(manager=org.manager, status="INACTIVE", employee_code="GONE1")
    gone = EmployeeFactory(manager=org.manager, status="INACTIVE", employee_code="GONE2")
    make_week(gone, W2)
    old = EmployeeFactory(manager=org.manager, status="INACTIVE", employee_code="GONE3")
    make_week(old, date(2026, 5, 31))  # outside a 4-week range
    client = login_as(org.manager)
    listed = set(codes(board_of(client, weeks=4)))
    assert "GONE2" in listed and "GONE1" not in listed and "GONE3" not in listed
    assert "inactive" in client.get(reverse("team"), {"weeks": 4}).content.decode()


def test_drill_down_is_read_only(known_team, login_as):
    """T-130: drill-down reuses the dashboard parts read-only; week view shows rows read-only."""
    org = known_team
    client = login_as(org.manager)
    response = client.get(reverse("team_member", args=["DEV1"]), {"weeks": 4})
    html = response.content.decode()
    dash = response.context["dash"]
    assert dash.employee == org.dev1 and dash.punctuality.rate == 33
    assert 'id="current-week"' in html and 'id="punctuality"' in html and "Read-only" in html
    for control in ("Open this week", 'value="save"', 'value="submit"', 'value="approve"', "<form"):
        assert control not in html.split('id="dashboard"')[1], control
    week_url = reverse("team_member_week", args=["DEV1", W2])
    assert f'href="{week_url}"' in html
    week = client.get(week_url).content.decode()
    entries = week.split('id="entries"')[1].split("</table>")[0]
    assert "Feature development" in entries and "<input" not in entries and "<select" not in entries
    assert 'id="week-status">Submitted<' in week and "Late" in week
    off_sunday = client.get(reverse("team_member_week", args=["DEV1", W2 + timedelta(days=2)]))
    assert off_sunday.status_code == 302
    future = reverse("team_member_week", args=["DEV1", THIS_WEEK + timedelta(weeks=1)])
    assert client.get(future).status_code == 404


def test_viewing_writes_nothing(known_team, login_as):
    """T-131: the team page, drill-down and week view never write (D-34)."""
    org = known_team
    client = login_as(org.director)
    client.get(reverse("team"))
    for url in (
        reverse("team"),
        reverse("team_member", args=["DEV1"]),
        reverse("team_member_week", args=["DEV1", W2]),
    ):
        with CaptureQueriesContext(connections["default"]) as queries:
            assert client.get(url).status_code == 200
        assert writes(queries) == [], url


def build_large_company(project, staff_per_manager=24):
    """~500 employees over 4 levels and 12 weeks of entries, written with bulk_create."""
    team = TeamFactory(name="Big", department="Ops")
    seq = iter(range(1, 10_000))

    def people(manager, count, title):
        return Employee.objects.bulk_create(
            Employee(
                employee_code=f"L{(n := next(seq)):04d}",
                email=f"l{n}@yourcompany.com",
                first_name="Person",
                last_name=f"{n:04d}",
                job_title=title,
                team=team,
                manager=manager,
                hire_date=date(2024, 1, 8),
            )
            for _ in range(count)
        )

    ceo = Employee.objects.create(
        employee_code="LCEO",
        email="lceo@yourcompany.com",
        first_name="Big",
        last_name="Boss",
        job_title="CEO",
        team=team,
        hire_date=date(2020, 1, 6),
        is_admin=True,
    )
    directors = people(ceo, 4, "Director")
    managers = [m for d in directors for m in people(d, 5, "Manager")]
    staff = [s for m in managers for s in people(m, staff_per_manager, "Analyst")]
    everyone = directors + managers + staff
    weeks = [THIS_WEEK - timedelta(weeks=i) for i in range(1, 13)]
    sheets = Timesheet.objects.bulk_create(
        Timesheet(employee=e, week_start=w, status="SUBMITTED", submitted_at=NOW)
        for e in everyone
        for w in weeks
    )
    TimeEntry.objects.bulk_create(
        (
            TimeEntry(
                timesheet=s,
                work_date=s.week_start + timedelta(days=1 + d),  # Mon–Fri
                category="PROJECT",
                project=project,
                start_time=time(9),
                end_time=time(17),
                minutes=480,
                reason="Work",
            )
            for s in sheets
            for d in range(5)
        ),
        batch_size=2000,
    )
    return ceo, directors[0], managers[0], len(everyone) + 1


def test_query_count_is_fixed_for_large_teams(project, fixed_now):
    """T-132: fixed query count — same for 24, 125 or 500 people and 4 or 26 weeks (D-86)."""
    ceo, director, manager, total = build_large_company(project)
    assert total > 500
    counts, timings = {}, {}
    for person in (ceo, director, manager):
        user = UserFactory(employee=person)
        for weeks in ("4", "26"):
            out = StringIO()
            started = clock.perf_counter()
            call_command("time_team_page", user.email, "--weeks", weeks, "--runs", "1", stdout=out)
            timings[(person.employee_code, weeks)] = clock.perf_counter() - started
            text = out.getvalue()
            assert ", 0 writes" in text
            counts[(person.employee_code, weeks)] = int(text.split(" queries")[0].split()[-1])
    for person in (ceo, director, manager):  # 4 weeks and 26 weeks cost the same
        assert counts[(person.employee_code, "4")] == counts[(person.employee_code, "26")], counts
    small = counts[(manager.employee_code, "4")]
    assert counts[(director.employee_code, "4")] == small  # 125 people cost the same as 24
    assert counts[("LCEO", "4")] == small - 1  # an admin skips the "manages anyone?" check
    assert small <= 10, counts
    people = {"LCEO": total - 1, director.employee_code: 125, manager.employee_code: 24}
    for code, expected in people.items():
        user = Employee.objects.get(employee_code=code).account
        out = StringIO()
        call_command("time_team_page", user.email, "--runs", "1", stdout=out)
        assert f": {expected} people," in out.getvalue()
    print(
        f"\nteam page timings with {total} employees (s):",
        {k: round(v, 2) for k, v in timings.items()},
    )
