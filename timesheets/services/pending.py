"""Who still has to approve, per manager (Change 9, D-143): the "Pending approvals by manager"
page for payroll and HR. Read only; built on the same rows and rule as Approvals
(company_period_rows, decision_blockers in approvals.py). Split from approvals.py (D-173)."""

from dataclasses import dataclass, field
from datetime import date

from directory.models import Employee
from timesheets.models import PeriodApproval, Timesheet
from timesheets.services.approvals import company_period_rows
from timesheets.services.calendar import (
    approval_deadline_for,
    company_tz,
)


def person_state(row):
    """Where a not-yet-approved person stands, in words, for payroll and HR."""
    required = [w for w in row.weeks if w.required]
    if any(w.open_request for w in row.weeks):
        return "Change request open"
    reopened = [w for w in required if w.state.status == Timesheet.Status.REOPENED]
    if reopened:
        until = min(w.sheet.reopen_until for w in reopened).astimezone(company_tz())
        return f"Reopened until {until:%a %b %-d, %-I:%M %p}"
    if any(w.state.status == Timesheet.Status.LOCKED for w in required):
        return "Locked – not submitted"
    if any(w.state.status in (Timesheet.Status.DRAFT, "NOT_STARTED") for w in required):
        return "Not submitted yet"
    return "Submitted"


@dataclass
class ManagerGroup:
    """One approver's part of the period: everyone they must approve, and who is still open."""

    approver: Employee | None  # None: staff with no manager, approved by an admin (D-11)
    pending: list = field(default_factory=list)  # [(PeriodRow, state)], by name
    total: int = 0

    @property
    def label(self):
        if self.approver is None:
            return "HR / admins"
        return f"{self.approver.first_name} {self.approver.last_name}"

    @property
    def team(self):
        team = self.approver.team if self.approver else None
        return team.name if team else ""

    @property
    def done(self):
        return not self.pending


@dataclass
class PendingReport:
    period_start: date
    deadline: object
    overdue: bool  # the approval deadline has passed: pending people are Overdue (D-133)
    groups: list  # ManagerGroup, by approver name

    @property
    def open_groups(self):
        return [g for g in self.groups if not g.done]

    @property
    def required(self):
        return sum(g.total for g in self.groups)

    @property
    def approved(self):
        return self.required - sum(len(g.pending) for g in self.groups)

    @property
    def managers_done(self):
        return sum(g.done for g in self.groups)


def pending_by_manager(period_start, now):
    """Who still has people to approve in the period — the same rows and rule as Approvals
    (company_period_rows, decision_blockers). Read only (D-143)."""
    groups = {}
    for row in company_period_rows(period_start, now):
        manager = row.employee.manager
        group = groups.setdefault(row.employee.manager_id, ManagerGroup(manager))
        group.total += 1
        if row.status != PeriodApproval.Status.APPROVED:
            group.pending.append((row, person_state(row)))
    deadline = approval_deadline_for(period_start)
    ordered = sorted(groups.values(), key=lambda g: (g.approver is None, g.label))
    return PendingReport(period_start, deadline, now >= deadline, ordered)
