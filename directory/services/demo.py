"""The demo company built by seed_demo (B.7).

The same seed date always gives the same data: random choices come from a fixed seed and all
dates are relative to `now`. History covers the 6 completed pay periods before the current one
(26 with --large), plus week 1 of the current period when today is in its week 2 (D-27).
"""

import csv
import logging
import random
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from faker import Faker

from audit.models import AuditLog
from audit.services.log import backdate, build, bulk_record
from directory.models import Employee, Team, User
from directory.services.importer import REQUIRED_COLUMNS, import_employees
from timesheets.models import ChangeRequest, PeriodApproval, Project, Task, TimeEntry, Timesheet
from timesheets.services.calendar import (
    deadline_for,
    pay_period_for,
    week_start_for,
    working_days,
)

SYSTEM_ACTOR = "seed_demo"
logger = logging.getLogger(__name__)
SEED = 2026
CORE_CSV = settings.BASE_DIR / "data" / "employees_core.csv"

CEO, ENG_DIRECTOR, ENG_MANAGER = "EMP-0001", "EMP-0002", "EMP-0003"
DEV1, DEV2, HR, OPS_MANAGER, FINANCE_MANAGER = (
    "EMP-0004",
    "EMP-0005",
    "EMP-0007",
    "EMP-0008",
    "EMP-0012",
)
SIGNUP_CANDIDATES = {"EMP-0006", "EMP-0009", "EMP-0010"}  # qa1, ops1, ops2: no account (B.7)
PAYROLL_CLERK = "EMP-0011"  # payroll@: exports and pays batches in the demo history

NORMAL_PERIODS, LARGE_PERIODS = 6, 26
LARGE_FACTOR = 14  # staff per team multiplier for --large (~500 employees)
LATE_RATE, MISSED_RATE = 0.03, 0.02
EARLIEST_HIRE = date(2018, 1, 8)

PROJECTS = (
    ("PRJ-001", "Customer Portal", True),
    ("PRJ-002", "Mobile App", True),
    ("PRJ-003", "Data Warehouse", True),
    ("PRJ-004", "Cloud Migration", True),
    ("PRJ-005", "Service Desk Upgrade", True),
    ("PRJ-006", "CRM Rollout", True),
    ("PRJ-007", "Internal Operations", True),
    ("PRJ-008", "Legacy Billing (closed)", False),  # inactive: never used in entries (D-18)
)
# Change 10 (D-154): the tasks each project allows, and the tasks each team usually books to.
PROJECT_TASKS = {
    "PRJ-001": ("PLN", "DES", "DEV", "TST", "REL", "SUP", "DOC", "MTG"),
    "PRJ-002": ("PLN", "DES", "DEV", "TST", "REL", "MTG"),
    "PRJ-003": ("PLN", "DEV", "TST", "DOC", "MTG"),
    "PRJ-004": ("PLN", "DEV", "REL", "SEC", "DOC", "MTG"),
    "PRJ-005": ("SUP", "DOC", "TST", "MTG"),
    "PRJ-006": ("PLN", "DOC", "MTG", "SUP"),
    "PRJ-007": ("PLN", "DOC", "MTG", "SEC"),
    "PRJ-008": ("DEV", "SUP"),
}
TEAM_TASKS = {
    "Leadership": ("PLN", "MTG"),
    "Engineering": ("DEV", "DES", "PLN", "MTG"),
    "Platform": ("DEV", "TST", "REL", "MTG"),
    "Data": ("DEV", "PLN"),
    "People": ("DOC", "MTG", "PLN"),
    "Operations": ("SUP", "DOC", "MTG"),
    "Support": ("SUP", "DOC"),
    "Payroll": ("DOC", "MTG", "PLN"),
    "Sales": ("PLN", "MTG", "DOC"),
}
TEAM_PROJECTS = {
    "Leadership": ("PRJ-007", "PRJ-004"),
    "Engineering": ("PRJ-001", "PRJ-004"),
    "Platform": ("PRJ-001", "PRJ-002"),
    "Data": ("PRJ-003", "PRJ-004"),
    "People": ("PRJ-007",),
    "Operations": ("PRJ-005", "PRJ-007"),
    "Support": ("PRJ-005",),
    "Payroll": ("PRJ-007",),
    "Sales": ("PRJ-006",),
}

# Generated team leads: key → (job title, team, department, manager code)
LEADS = {
    "sales": ("Sales Manager", "Sales", "Sales", CEO),
    "data": ("Data Engineering Lead", "Data", "Technology", ENG_DIRECTOR),
    "support": ("Support Lead", "Support", "Ops", OPS_MANAGER),
}
# Generated staff: (team, department, manager code or lead key, job titles, count)
STAFF = (
    ("Platform", "Technology", ENG_MANAGER, ("Software Engineer", "QA Engineer"), 8),
    ("Engineering", "Technology", ENG_DIRECTOR, ("Solutions Architect", "Program Manager"), 2),
    ("Data", "Technology", "data", ("Data Engineer", "Data Analyst"), 5),
    ("Operations", "Ops", OPS_MANAGER, ("Operations Analyst",), 3),
    ("Support", "Ops", "support", ("Support Specialist",), 5),
    ("People", "HR", HR, ("HR Generalist", "Recruiter"), 2),
    ("Payroll", "Finance", FINANCE_MANAGER, ("Accountant",), 2),
    ("Sales", "Sales", "sales", ("Account Executive",), 6),
    ("Leadership", "Executive", CEO, ("Executive Assistant",), 1),
)
LOCATIONS = ("Dallas", "Frisco", "Remote", "Austin")
REJECT_COMMENT = "Please split Wednesday's hours between Customer Portal and Mobile App."
REASONS = {  # the demo gives every row a reason (optional since D-128)
    TimeEntry.Category.PROJECT: (
        "Feature development",
        "Code review",
        "Bug fixes",
        "Customer follow-up",
        "Planning and estimates",
        "Testing",
    ),
    TimeEntry.Category.MEETING: ("Team stand-up and planning", "Client meeting", "One-to-one"),
    TimeEntry.Category.TRAINING: ("Security awareness course", "Internal workshop"),
    TimeEntry.Category.OTHER: ("Admin and email", "Recruiting interview"),
    TimeEntry.Category.BREAK: ("Lunch break",),
    TimeEntry.Category.PTO: ("Vacation", "Personal day"),
    TimeEntry.Category.SICK: ("Sick day", "Doctor's appointment"),
}
WEEKEND_REASON = "Release support (weekend)"


class DemoDataExists(Exception):
    pass


@dataclass
class _Week:
    employee: Employee
    week_start: date
    status: str
    entries: list = field(default_factory=list)
    submitted_at: datetime | None = None
    is_late: bool = False
    reopen_until: datetime | None = None
    manager_note: str = ""
    unlock: tuple | None = None  # (requested_at, unlocked_at) for a late week
    last_event: datetime | None = None
    sheet: Timesheet | None = None


def seed_demo(*, now, password, large=False):
    """Build the demo company. Refuses (DemoDataExists) if the database already has data."""
    if Employee.objects.exists() or Project.objects.exists() or Timesheet.objects.exists():
        raise DemoDataExists(
            "The database already has data, so seed_demo did nothing. "
            "To start over, see docs/BUILD_GUIDE.md D.3."
        )
    with transaction.atomic():
        summary = _Seeder(now, password, large).run()
    # The payroll database is a separate file: it is filled only after the main seed has
    # committed (D-65, D-73). If this part fails, sync_payroll completes it later.
    try:
        summary["payroll"] = seed_payroll(now)
    except Exception:
        logger.exception("seed_demo: payroll part failed")
        summary["payroll"] = "not written — run `uv run python manage.py sync_payroll`"
    return summary


def seed_payroll(now):
    """Publish every approved period; older periods' registers finalized & exported and paid,
    the next one finalized, the newest left to finalize; one correction (B.7, D-137)."""
    from payroll.models import PayrollRegister, PayrollWeek
    from payroll.services.publish import PublishResult, audit_result, publish_period, snapshot
    from payroll.services.register import finalize, mark_paid

    tz = ZoneInfo(settings.COMPANY_TZ)
    approve_the_rest(now, tz)
    approvals = list(
        PeriodApproval.objects.filter(status=PeriodApproval.Status.APPROVED)
        .select_related("employee", "approver")
        .order_by("period_start", "employee__employee_code")
    )
    periods = sorted({a.period_start for a in approvals})
    paid, exported_only = periods[:-2], periods[-2:-1]
    correction = next((a for a in approvals if paid and a.period_start == paid[0]), None)
    clerk = Employee.objects.filter(employee_code=PAYROLL_CLERK).first()

    for approval in approvals:
        if approval is not correction:
            publish_period(approval, actor=approval.approver, at=approval.decided_at)
            continue
        # The correction (B.7): week 1 was first published with an hour less, from an earlier
        # decision; it is exported and paid with its period, then superseded below.
        sheets = Timesheet.objects.filter(
            employee=approval.employee,
            week_start__in=(approval.period_start, approval.period_start + timedelta(weeks=1)),
        ).order_by("week_start")
        first = []
        for number, sheet in enumerate(sheets, start=1):
            fields = snapshot(approval, sheet)
            if number == 1:
                fields["regular_minutes"] -= 60
                fields["total_minutes"] -= 60
                fields["approved_at"] = approval.decided_at - timedelta(days=2)
            first.append(PayrollWeek.objects.create(**fields, version=1))
        audit_result(
            PublishResult(created=first), actor=approval.approver, at=fields["approved_at"]
        )

    for period in paid + exported_only:  # the approval deadlines have passed: READY
        exported_at = datetime.combine(period + timedelta(days=19), time(10), tzinfo=tz)  # Fri
        finalize(period, actor=clerk, now=exported_at)
        if period in paid:
            mark_paid(period, actor=clerk, at=exported_at + timedelta(days=7))
    if correction:
        fixed_at = datetime.combine(
            correction.period_start + timedelta(days=29), time(10), tzinfo=tz  # a Monday
        )
        publish_period(correction, system_actor=SYSTEM_ACTOR, at=min(fixed_at, now))
    return {
        "records": PayrollWeek.objects.count(),
        "registers": PayrollRegister.objects.count(),
        "paid_registers": PayrollRegister.objects.filter(status="PAID").count(),
        "corrections": PayrollWeek.objects.filter(status=PayrollWeek.Status.SUPERSEDED).count(),
    }


def approve_the_rest(now, tz):
    """Older periods are fully approved (Change 9, D-144): each manager also approves the
    people the history left pending — a week locked without a submission (approved with what
    was entered, still "not submitted by employee" and missed), or no timesheet at all (sign-up
    candidates) — through the real approvals service. The most recent completed period stays
    pending (B.7). Payroll is published right after, with everything else."""
    from timesheets.services.approvals import approve_period, company_period_rows
    from timesheets.services.calendar import default_period

    hr = Employee.objects.get(employee_code=HR)
    last_completed = default_period(now)
    older = PeriodApproval.objects.filter(period_start__lt=last_completed)
    for period in sorted(set(older.values_list("period_start", flat=True))):
        decided = datetime.combine(period + timedelta(days=16), time(15), tzinfo=tz)  # Tuesday
        for row in company_period_rows(period, decided):
            if row.status == PeriodApproval.Status.APPROVED or row.blockers:
                continue
            approver = row.employee.manager or hr  # the CEO is approved by HR (D-11)
            approve_period(approver, row.employee, period, now=decided, confirm_unsubmitted=True)


def us_holidays(year):
    """US federal holidays {date: name} on their calendar dates (weekend ones are skipped)."""

    def nth_weekday(month, weekday, n):
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7, weeks=n - 1)

    last_may_monday = nth_weekday(6, 0, 1) - timedelta(weeks=1)
    return {
        date(year, 1, 1): "New Year's Day",
        nth_weekday(1, 0, 3): "Martin Luther King Jr. Day",
        last_may_monday: "Memorial Day",
        date(year, 6, 19): "Juneteenth",
        date(year, 7, 4): "Independence Day",
        nth_weekday(9, 0, 1): "Labor Day",
        nth_weekday(11, 3, 4): "Thanksgiving",
        date(year, 12, 25): "Christmas Day",
    }


class _Seeder:
    def __init__(self, now, password, large):
        self.tz = ZoneInfo(settings.COMPANY_TZ)
        self.now = now.astimezone(self.tz)
        self.password = password
        self.large = large
        self.rng = random.Random(SEED)
        self.fake = Faker("en_US")
        self.fake.seed_instance(SEED)
        self.audit = []

        today = self.now.date()
        current_period, _, current_week2 = pay_period_for(today, settings.PAY_PERIOD_ANCHOR)
        n_periods = LARGE_PERIODS if large else NORMAL_PERIODS
        self.periods = [
            current_period - timedelta(weeks=2 * (n_periods - i)) for i in range(n_periods)
        ]
        self.week_starts = [p + timedelta(weeks=k) for p in self.periods for k in (0, 1)]
        self.current_period = current_period
        if week_start_for(today) == current_week2:
            self.week_starts.append(current_period)
        self.last_completed = self.periods[-1]
        years = {self.week_starts[0].year, today.year}
        self.holidays = {d: name for y in sorted(years) for d, name in us_holidays(y).items()}

    # --- orchestration ---------------------------------------------------------------------

    def run(self):
        employees = self._directory()
        with_account = self._accounts(employees)
        projects = self._projects()
        weeks = self._history(with_account, projects)
        approvals = self._approvals(employees, weeks)
        self._write(employees, weeks, approvals)
        summary = self._summary()
        bulk_record(
            self.audit
            + [
                build(
                    AuditLog.Action.CREATE,
                    "DemoData",
                    "seed_demo",
                    system_actor=SYSTEM_ACTOR,
                    after=summary,
                )
            ]
        )
        return summary

    # --- directory and accounts ------------------------------------------------------------

    def _directory(self):
        with CORE_CSV.open(newline="", encoding="utf-8-sig") as handle:
            core_rows = list(csv.DictReader(handle))
        generated = self._generated_rows(core_rows)
        import_employees(core_rows + generated, columns=REQUIRED_COLUMNS, system_actor=SYSTEM_ACTOR)
        for code, minutes in self.part_time.items():
            Employee.objects.filter(employee_code=code).update(expected_weekly_minutes=minutes)
        return {e.employee_code: e for e in Employee.objects.select_related("team", "manager")}

    def _generated_rows(self, core_rows):
        rows = {}
        used_emails = {row["email"].strip().lower() for row in core_rows}
        next_number = len(core_rows) + 1

        def person(team, department, manager_code, title):
            nonlocal next_number
            code = f"EMP-{next_number:04d}"
            next_number += 1
            first, last = self.fake.first_name(), self.fake.last_name()
            rows[code] = {
                "employee_code": code,
                "email": self._unique_email(first, last, used_emails),
                "first_name": first,
                "last_name": last,
                "job_title": title,
                "team": team,
                "department": department,
                "manager_code": manager_code,
                "location": self.rng.choice(LOCATIONS),
                "hire_date": self._past_hire_date().isoformat(),
                "is_admin": "false",
                "is_payroll": "false",
                "status": "ACTIVE",
            }
            return code

        leads = {
            key: person(team, dept, mgr, title) for key, (title, team, dept, mgr) in LEADS.items()
        }
        team_members = defaultdict(list)
        factor = LARGE_FACTOR if self.large else 1
        for team, department, manager, titles, count in STAFF:
            for i in range(count * factor):
                code = person(
                    team, department, leads.get(manager, manager), titles[i % len(titles)]
                )
                team_members[team].append(code)

        # Recent hires, hired on the Wednesday of a period's week 1: partial first week (D-19).
        for team, period_index in (("Platform", -4), ("Support", -3), ("Sales", -2)):
            hire = self.periods[period_index] + timedelta(days=3)  # Sunday + 3 = Wednesday
            rows[team_members[team][-1]]["hire_date"] = hire.isoformat()

        self.rejected_code = team_members["Platform"][0]
        self.open_request_code = team_members["Platform"][1]
        self.edited_code = team_members["Operations"][0]
        self.part_time = {team_members["Leadership"][0]: 1200, team_members["Support"][1]: 1800}
        return list(rows.values())

    def _unique_email(self, first, last, used):
        base = f"{re.sub(r'[^a-z]', '', first.lower())}.{re.sub(r'[^a-z]', '', last.lower())}"
        email, n = f"{base}{settings.COMPANY_EMAIL_DOMAIN}", 2
        while email in used:
            email, n = f"{base}{n}{settings.COMPANY_EMAIL_DOMAIN}", n + 1
        used.add(email)
        return email

    def _past_hire_date(self):
        span = (self.week_starts[0] - timedelta(days=60) - EARLIEST_HIRE).days
        return EARLIEST_HIRE + timedelta(days=self.rng.randrange(span))

    def _accounts(self, employees):
        with_account = []
        for code in sorted(employees):
            employee = employees[code]
            if employee.status == Employee.Status.ACTIVE and code not in SIGNUP_CANDIDATES:
                User.objects.create_user(password=self.password, employee=employee)
                with_account.append(employee)
        return with_account

    def _projects(self):
        """The projects, each with its allowed tasks (the 9 default tasks come from migration
        timesheets/0007, D-148, D-154)."""
        projects = Project.objects.bulk_create(
            Project(code=code, name=name, active=active) for code, name, active in PROJECTS
        )
        self.tasks = {t.code: t for t in Task.objects.all()}
        for project in projects:
            codes = PROJECT_TASKS[project.code]
            project.tasks.set([self.tasks[c] for c in codes])
            self.audit.append(
                build(
                    AuditLog.Action.CREATE,
                    "Project",
                    project.code,
                    system_actor=SYSTEM_ACTOR,
                    after={"name": project.name, "active": project.active, "tasks": list(codes)},
                )
            )
        return {p.code: p for p in projects}

    def _task_for(self, project, team):
        """A task the team usually books to and the project allows (D-154)."""
        allowed = PROJECT_TASKS[project.code]
        usual = [c for c in TEAM_TASKS[team] if c in allowed] or list(allowed)
        return self.tasks[self.rng.choice(usual)]

    def _book_tasks(self, week):
        for entry in week.entries:
            if entry.category == TimeEntry.Category.PROJECT:
                entry.task = self._task_for(entry.project, week.employee.team.name)

    # --- weekly history --------------------------------------------------------------------

    def _forced_kinds(self):
        """Weeks whose outcome the demo scenarios depend on."""
        forced = {}
        last = self.last_completed
        for code in (DEV1, DEV2, self.rejected_code):
            forced[(code, last)] = forced[(code, last + timedelta(weeks=1))] = "on_time"
        forced[(self.open_request_code, last + timedelta(weeks=1))] = "on_time"
        edited_period = self.periods[-4]
        forced[(self.edited_code, edited_period)] = "on_time"
        forced[(self.edited_code, edited_period + timedelta(weeks=1))] = "on_time"
        forced[(DEV1, self.periods[-5] + timedelta(weeks=1))] = "missed"  # D.1 row 6
        return forced

    def _history(self, with_account, projects):
        forced = self._forced_kinds()
        weeks = []
        for employee in with_account:
            team_projects = [projects[c] for c in TEAM_PROJECTS[employee.team.name]]
            for week_start in self.week_starts:
                workdays = [d for d in working_days(week_start) if self._employed(employee, d)]
                if not workdays:
                    continue  # fully outside employment: never missed (D-19)
                kind = forced.get((employee.employee_code, week_start)) or self._random_kind(
                    week_start
                )
                week = self._week(employee, week_start, kind, workdays, team_projects)
                self._book_tasks(week)
                weeks.append(week)
        self._manager_edit(weeks, projects)
        return weeks

    def _random_kind(self, week_start):
        roll = self.rng.random()
        if roll < LATE_RATE and week_start < self.last_completed:
            return "late"
        if roll < LATE_RATE + MISSED_RATE:
            return "missed"
        return "on_time"

    def _employed(self, employee, day):
        if employee.hire_date and day < employee.hire_date:
            return False
        return not (employee.end_date and day > employee.end_date)

    def _week(self, employee, week_start, kind, workdays, team_projects):
        deadline = deadline_for(week_start, self.tz)
        if kind == "missed":
            partial = workdays[: self.rng.randint(1, 3)] if self.rng.random() < 0.5 else []
            return _Week(
                employee,
                week_start,
                Timesheet.Status.LOCKED,
                entries=self._entries(employee, partial, team_projects, weekend=False),
            )
        week = _Week(
            employee,
            week_start,
            Timesheet.Status.SUBMITTED,
            entries=self._entries(employee, workdays, team_projects, weekend=True),
        )
        if kind == "on_time":
            if self.rng.random() < 0.5:  # Friday afternoon
                week.submitted_at = datetime.combine(
                    week_start + timedelta(days=5), time(15), tzinfo=self.tz
                ) + timedelta(minutes=15 * self.rng.randint(0, 12))
            else:  # Saturday morning, before the noon deadline
                week.submitted_at = deadline - timedelta(minutes=15 * self.rng.randint(1, 16))
        else:  # late: locked, unlocked through a change request, resubmitted (D-08, D-21)
            requested = deadline + timedelta(hours=self.rng.randint(20, 40))
            unlocked = requested + timedelta(hours=self.rng.randint(1, 6))
            week.unlock = (requested, unlocked)
            week.reopen_until = max(unlocked + timedelta(hours=48), deadline)
            week.submitted_at = unlocked + timedelta(hours=self.rng.randint(2, 20))
            week.is_late = True
        week.last_event = week.submitted_at
        return week

    def _entries(self, employee, days, team_projects, *, weekend):
        """Unsaved rows with times, reasons and lunch breaks; nothing overlaps (D-35–D-44)."""
        daily = employee.expected_weekly_minutes // 5
        overtime_week = daily >= 480 and self.rng.random() < 0.15
        entries = []
        for day in days:
            if day in self.holidays:
                reason = f"Public holiday: {self.holidays[day]}"
                entries.append(self._leave(day, TimeEntry.Category.HOLIDAY, daily, reason))
                continue
            roll = self.rng.random()
            if roll < 0.03:
                entries.append(self._leave(day, TimeEntry.Category.PTO, daily))
                continue
            if roll < 0.05:
                entries.append(self._leave(day, TimeEntry.Category.SICK, daily))
                continue
            extra = self.rng.choice((60, 90, 120)) if overtime_week and roll < 0.75 else 0
            entries.extend(self._workday(day, daily + extra, team_projects))
        if weekend and days and self.rng.random() < 0.03:  # weekend hours entered in advance (D-09)
            saturday = week_start_for(days[0]) + timedelta(days=6)  # the week's last day
            minutes = self.rng.choice((120, 180, 240))
            entries.append(
                _timed(
                    saturday,
                    TimeEntry.Category.PROJECT,
                    10 * 60,
                    minutes,
                    WEEKEND_REASON,
                    team_projects[0],
                )
            )
        return entries

    def _leave(self, day, category, minutes, reason=None):
        """Leave rows are hours only, without times (D-40)."""
        reason = reason or self.rng.choice(REASONS[category])
        return TimeEntry(work_date=day, category=category, minutes=minutes, reason=reason)

    def _workday(self, day, work_minutes, team_projects):
        """Back-to-back blocks from a start between 08:00 and 09:30, with a lunch break."""
        meeting = self.rng.choice((0, 30, 60, 60, 90)) if work_minutes >= 240 else 0
        training = 60 if self.rng.random() < 0.05 else 0
        other = 30 if self.rng.random() < 0.05 else 0
        project_minutes = work_minutes - meeting - training - other
        second = team_projects[1] if len(team_projects) > 1 and self.rng.random() < 0.4 else None
        first = team_projects[0] if second else self.rng.choice(team_projects)
        morning = project_minutes
        if project_minutes > 15:
            morning = 15 * round(project_minutes * self.rng.uniform(0.4, 0.6) / 15)
            morning = min(max(morning, 15), project_minutes - 15)
        lunch = self.rng.choice((30, 45, 60)) if work_minutes >= 360 else 0
        blocks = (
            (TimeEntry.Category.PROJECT, morning, first),
            (TimeEntry.Category.MEETING, meeting, None),
            (TimeEntry.Category.BREAK, lunch, None),  # unpaid (D-39)
            (TimeEntry.Category.PROJECT, project_minutes - morning, second or first),
            (TimeEntry.Category.TRAINING, training, None),
            (TimeEntry.Category.OTHER, other, None),
        )
        cursor = 8 * 60 + 15 * self.rng.randint(0, 6)
        rows = []
        for category, minutes, project in blocks:
            if minutes > 0:
                reason = self.rng.choice(REASONS[category])
                rows.append(_timed(day, category, cursor, minutes, reason, project))
                cursor += minutes
        return rows

    def _manager_edit(self, weeks, projects):
        """ops.manager moves a mis-logged project entry on request, before approval (B.7)."""
        edited_period = self.periods[-4]
        candidates = [
            w
            for w in weeks
            if w.employee.employee_code == self.edited_code
            and w.week_start in (edited_period, edited_period + timedelta(weeks=1))
        ]
        for week in candidates:
            entry = next(
                (e for e in week.entries if e.category == TimeEntry.Category.PROJECT), None
            )
            if entry is None:
                continue
            before = _entry_snapshot(week.entries)
            other = next(c for c in TEAM_PROJECTS["Operations"] if c != entry.project.code)
            entry.project = projects[other]
            entry.task = self._task_for(entry.project, week.employee.team.name)
            requested = deadline_for(week.week_start, self.tz) + timedelta(days=1)
            edited = requested + timedelta(hours=3)
            week.last_event = edited
            self.edit = {
                "week": week,
                "requested": requested,
                "edited": edited,
                "before": before,
                "after": _entry_snapshot(week.entries),
                "project": other,
            }
            return
        raise RuntimeError("Demo data has no project entry to edit.")

    # --- approvals -------------------------------------------------------------------------

    def _approver(self, employee, employees):
        """Direct manager; an admin (never self) for employees with no manager (D-11)."""
        if employee.manager_id:
            return employee.manager
        admins = sorted(
            (e for e in employees.values() if e.is_admin and e.pk != employee.pk),
            key=lambda e: (e.employee_code != HR, e.employee_code),
        )
        return admins[0]

    def _approvals(self, employees, weeks):
        by_period = defaultdict(list)
        for week in weeks:
            period_start = pay_period_for(week.week_start, settings.PAY_PERIOD_ANCHOR)[0]
            by_period[(week.employee.employee_code, period_start)].append(week)
        approvals = []
        for (code, period_start), period_weeks in sorted(by_period.items()):
            if period_start == self.current_period:
                continue  # current period is still running
            employee = employees[code]
            approval = PeriodApproval(employee=employee, period_start=period_start)
            approvals.append((approval, period_weeks))
            both_submitted = len(period_weeks) == 2 and all(
                w.status == Timesheet.Status.SUBMITTED for w in period_weeks
            )
            if period_start == self.last_completed:
                if code == self.rejected_code:
                    self._reject(approval, period_weeks, employees)
                continue  # most recent completed period stays PENDING (B.7)
            if not both_submitted:
                continue  # a LOCKED week blocks approval (D-06)
            # Decided on the Monday after the period (it ends on a Saturday).
            base = datetime.combine(period_start + timedelta(days=15), time(9), tzinfo=self.tz)
            decided = base + timedelta(days=self.rng.randint(0, 2), hours=self.rng.randint(0, 8))
            latest = max(w.last_event for w in period_weeks)
            approval.status = PeriodApproval.Status.APPROVED
            approval.approver = self._approver(employee, employees)
            approval.decided_at = max(decided, latest + timedelta(hours=1))
            for week in period_weeks:
                week.status = (
                    Timesheet.Status.APPROVED
                )  # built as history, not a status change (D-10)
        return approvals

    def _reject(self, approval, period_weeks, employees):
        decided = min(
            datetime.combine(approval.period_start + timedelta(days=15), time(10), tzinfo=self.tz),
            self.now - timedelta(hours=1),
        )
        approval.status = PeriodApproval.Status.REJECTED
        approval.approver = self._approver(approval.employee, employees)
        approval.decided_at = decided
        approval.comment = REJECT_COMMENT
        for week in period_weeks:  # D-07, D-21
            week.status = Timesheet.Status.REOPENED
            week.manager_note = REJECT_COMMENT
            week.reopen_until = max(
                decided + timedelta(hours=48), deadline_for(week.week_start, self.tz)
            )

    # --- writing ---------------------------------------------------------------------------

    def _write(self, employees, weeks, approvals):
        sheets = Timesheet.objects.bulk_create(
            (
                Timesheet(
                    employee=w.employee,
                    week_start=w.week_start,
                    status=w.status,
                    submitted_at=w.submitted_at,
                    is_late=w.is_late,
                    reopen_until=w.reopen_until,
                    manager_note=w.manager_note,
                )
                for w in weeks
            ),
            batch_size=500,
        )
        for week, sheet in zip(weeks, sheets, strict=True):
            week.sheet = sheet
            for entry in week.entries:
                entry.timesheet = sheet
        TimeEntry.objects.bulk_create((e for w in weeks for e in w.entries), batch_size=500)
        self._change_requests(employees, weeks)
        PeriodApproval.objects.bulk_create((a for a, _ in approvals), batch_size=500)
        for approval, _ in approvals:
            if approval.status == PeriodApproval.Status.PENDING:
                continue
            action = (
                AuditLog.Action.APPROVE
                if approval.status == PeriodApproval.Status.APPROVED
                else AuditLog.Action.REJECT
            )
            self.audit.append(
                build(
                    action,
                    "PeriodApproval",
                    approval.pk,
                    actor=approval.approver,
                    before={"status": PeriodApproval.Status.PENDING},
                    after={"status": approval.status, "comment": approval.comment},
                    at=approval.decided_at,
                )
            )

    def _change_requests(self, employees, weeks):
        created_at = {}
        late = [w for w in weeks if w.unlock]
        for week in late:
            requested, unlocked = week.unlock
            reviewer = self._approver(week.employee, employees)
            request = ChangeRequest.objects.create(
                timesheet=week.sheet,
                requester=week.employee,
                reason="I missed the Saturday deadline. Please unlock my week.",
                status=ChangeRequest.Status.UNLOCKED,
                reviewer=reviewer,
                resolution="Unlocked for resubmission.",
                resolved_at=unlocked,
            )
            created_at[request.pk] = requested
            self.audit.append(
                build(
                    AuditLog.Action.UNLOCK,
                    "Timesheet",
                    week.sheet.pk,
                    actor=reviewer,
                    before={"status": Timesheet.Status.LOCKED},
                    after={"status": Timesheet.Status.REOPENED, "reopen_until": week.reopen_until},
                    change_request=request,
                    at=unlocked,
                )
            )

        edit = self.edit
        reviewer = self._approver(edit["week"].employee, employees)
        request = ChangeRequest.objects.create(
            timesheet=edit["week"].sheet,
            requester=edit["week"].employee,
            reason="My first project entry this week went to the wrong project.",
            status=ChangeRequest.Status.EDITED,
            reviewer=reviewer,
            resolution=f"Moved the entry to {edit['project']}.",
            resolved_at=edit["edited"],
        )
        created_at[request.pk] = edit["requested"]
        self.audit.append(
            build(
                AuditLog.Action.UPDATE,
                "Timesheet",
                edit["week"].sheet.pk,
                actor=reviewer,
                before={"entries": edit["before"]},
                after={"entries": edit["after"]},
                change_request=request,
                at=edit["edited"],
            )
        )

        open_week = next(
            w
            for w in weeks
            if w.employee.employee_code == self.open_request_code
            and w.week_start == self.last_completed + timedelta(weeks=1)
        )
        request = ChangeRequest.objects.create(
            timesheet=open_week.sheet,
            requester=open_week.employee,
            reason="I forgot to log Thursday's training session.",
        )
        created_at[request.pk] = min(
            open_week.submitted_at + timedelta(days=1), self.now - timedelta(hours=2)
        )
        backdate(ChangeRequest, "created_at", created_at)
        raised = ChangeRequest.objects.filter(pk__in=created_at).select_related(
            "timesheet", "requester"
        )
        for change in raised:  # raising a request is audited too (D-46)
            self.audit.append(
                build(
                    AuditLog.Action.CREATE,
                    "ChangeRequest",
                    change.pk,
                    actor=change.requester,
                    after={
                        "week_start": change.timesheet.week_start,
                        "status": ChangeRequest.Status.OPEN,
                        "reason": change.reason,
                    },
                    change_request=change,
                    at=created_at[change.pk],
                )
            )

    def _summary(self):
        approvals = Counter(PeriodApproval.objects.values_list("status", flat=True))
        return {
            "employees": Employee.objects.count(),
            "accounts": User.objects.count(),
            "departments": Team.objects.values("department").distinct().count(),
            "teams": Team.objects.count(),
            "projects": Project.objects.count(),
            "weeks_of_history": len(self.week_starts),
            "timesheets": Timesheet.objects.count(),
            "time_entries": TimeEntry.objects.count(),
            "approvals": dict(sorted(approvals.items())),
            "change_requests": ChangeRequest.objects.count(),
        }


def _timed(day, category, start_minute, minutes, reason, project=None):
    """A row with start and end times on `day`; minutes = end − start (D-37)."""
    end_minute = start_minute + minutes
    return TimeEntry(
        work_date=day,
        category=category,
        project=project,
        minutes=minutes,
        reason=reason,
        start_time=time(start_minute // 60, start_minute % 60),
        end_time=time(end_minute // 60, end_minute % 60),
    )


def _entry_snapshot(entries):
    return [
        {
            "work_date": e.work_date.isoformat(),
            "category": e.category,
            "project": e.project.code if e.project else None,
            "task": e.task.code if e.task else None,
            "start": e.start_time.strftime("%H:%M") if e.start_time else None,
            "end": e.end_time.strftime("%H:%M") if e.end_time else None,
            "minutes": e.minutes,
            "reason": e.reason,
        }
        for e in entries
    ]
