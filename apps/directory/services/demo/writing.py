"""The seeder writes the history, change requests and its summary (B.7)."""

from collections import Counter
from datetime import timedelta

from apps.audit.models import AuditLog
from apps.audit.services.log import backdate, build
from apps.directory.models import Employee, Team, User
from apps.projects.models import Project
from apps.timesheets.models import ChangeRequest, PeriodApproval, TimeEntry, Timesheet


class WritingMixin:
    """Part of _Seeder (__init__.py); uses its attributes (self.rng, self.audit, …)."""

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
