"""The seeder's weekly history: weeks, entries, leave, holidays, one manager edit (B.7)."""

from datetime import datetime, time, timedelta

from directory.services.demo.constants import (
    DEV1,
    DEV2,
    LATE_RATE,
    MISSED_RATE,
    REASONS,
    TEAM_PROJECTS,
    WEEKEND_REASON,
)
from directory.services.demo.records import (
    _entry_snapshot,
    _timed,
    _Week,
)
from timesheets.models import TimeEntry, Timesheet
from timesheets.services.calendar import (
    deadline_for,
    week_start_for,
    working_days,
)


class HistoryMixin:
    """Part of _Seeder (__init__.py); uses its attributes (self.rng, self.audit, …)."""

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
