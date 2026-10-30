"""The seeder's period approvals and one rejection (B.7)."""

from collections import defaultdict
from datetime import datetime, time, timedelta

from django.conf import settings

from apps.directory.services.demo.constants import (
    HR,
    REJECT_COMMENT,
)
from apps.timesheets.models import PeriodApproval, Timesheet
from apps.timesheets.services.calendar import (
    deadline_for,
    pay_period_for,
)


class ApprovalsMixin:
    """Part of _Seeder (__init__.py); uses its attributes (self.rng, self.audit, …)."""

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
