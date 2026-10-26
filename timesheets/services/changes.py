"""Change requests: raise, reject, unlock, edit directly (FR-9, D-46–D-52), and the approver's
edit from Approvals, which needs no change request (Change 9, D-140).

Handlers are whoever can_approve the week's employee: the direct manager, or admins for
employees with no manager — never the employee themselves (D-11, D-47).
"""

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Q

from audit.models import AuditLog
from audit.services.log import record
from directory.services.permissions import can_approve
from timesheets.models import ChangeRequest, Timesheet
from timesheets.services import approvals
from timesheets.services.calendar import (
    company_tz,
    deadline_for,
    pay_period_for,
    week_start_for,
    week_state,
)
from timesheets.services.validation import validate_entries
from timesheets.services.weeks import (
    entries_snapshot,
    load_sheet,
    replace_entries,
    submission_errors,
)

REQUESTABLE = (Timesheet.Status.SUBMITTED, Timesheet.Status.LOCKED, Timesheet.Status.APPROVED)
MAX_REASON = 2000


def can_request_change(state, now):
    """SUBMITTED, LOCKED or APPROVED weeks up to the current week (D-46)."""
    current = week_start_for(now.astimezone(company_tz()).date())
    return state.status in REQUESTABLE and state.week_start <= current


def open_request_for(timesheet):
    if timesheet is None:
        return None
    return timesheet.change_requests.filter(status=ChangeRequest.Status.OPEN).first()


def raise_request(employee, week_start, reason, *, now):
    """The employee asks for a change to their own week. Returns the new ChangeRequest."""
    reason = (reason or "").strip()
    if not reason:
        raise ValidationError("Explain what needs to change.")
    if len(reason) > MAX_REASON:
        raise ValidationError(f"Keep the reason under {MAX_REASON} characters.")
    sheet = load_sheet(employee, week_start)
    state = week_state(employee, week_start, sheet, now)
    if not can_request_change(state, now):
        raise PermissionDenied(
            "A change can only be requested for a submitted, locked or approved week."
        )
    if open_request_for(sheet):
        raise ValidationError("This week already has an open change request.")
    try:
        with transaction.atomic():
            if sheet is None:  # a missed week with no timesheet at all (D-46)
                sheet = Timesheet.objects.create(
                    employee=employee, week_start=week_start, status=Timesheet.Status.LOCKED
                )
            request = ChangeRequest.objects.create(
                timesheet=sheet, requester=employee, reason=reason
            )
            record(
                AuditLog.Action.CREATE,
                "ChangeRequest",
                request.pk,
                actor=employee,
                after={"week_start": week_start, "status": request.status, "reason": reason},
                change_request=request,
            )
    except IntegrityError:  # someone raised one at the same moment (one OPEN per week)
        raise ValidationError("This week already has an open change request.") from None
    return request


def handled_by(handler):
    """Requests this person may handle: direct reports, plus no-manager employees for admins."""
    scope = Q(timesheet__employee__manager=handler)
    if handler.is_admin:
        scope |= Q(timesheet__employee__manager__isnull=True)
    return (
        ChangeRequest.objects.filter(scope)
        .exclude(timesheet__employee=handler)
        .select_related("timesheet__employee", "requester", "reviewer")
    )


def open_request_count(handler):
    return handled_by(handler).filter(status=ChangeRequest.Status.OPEN).count()


def _ensure_can_handle(request, handler):
    if not can_approve(handler, request.timesheet.employee):
        raise PermissionDenied("Only the employee's manager can handle this request.")
    if request.status != ChangeRequest.Status.OPEN:
        raise PermissionDenied("This request has already been handled.")


def _resolve(request, handler, status, note, now):
    request.status = status
    request.reviewer = handler
    request.resolution = (note or "").strip()
    request.resolved_at = now
    request.save(update_fields=["status", "reviewer", "resolution", "resolved_at"])


def reject_request(request, handler, note="", *, now):
    """No change to the week; the request is closed with an optional note (D-48)."""
    _ensure_can_handle(request, handler)
    with transaction.atomic():
        _resolve(request, handler, ChangeRequest.Status.REJECTED, note, now)
        record(
            AuditLog.Action.REJECT,
            "ChangeRequest",
            request.pk,
            actor=handler,
            before={"status": ChangeRequest.Status.OPEN},
            after={"status": request.status, "resolution": request.resolution},
            change_request=request,
        )
    return request


def unlock_request(request, handler, note="", *, now):
    """The week is REOPENED for the employee until the D-21 window ends (D-50)."""
    _ensure_can_handle(request, handler)
    with transaction.atomic():
        approvals.unlock_week(request.timesheet, actor=handler, change_request=request, at=now)
        _resolve(request, handler, ChangeRequest.Status.UNLOCKED, note, now)
    return request


def edit_directly(request, handler, entries, note="", *, now):
    """The handler replaces the week's rows; the week ends SUBMITTED (D-49).

    Same validation as the employee's own page (Phase 5b). If the week was approved, its
    period goes back to PENDING through approvals.reset_approval (D-10).
    """
    _ensure_can_handle(request, handler)
    sheet = request.timesheet
    employee = sheet.employee
    errors = validate_entries(employee, sheet.week_start, entries) + submission_errors(entries)
    if errors:
        raise ValidationError(errors)
    with transaction.atomic():
        sheet = Timesheet.objects.select_for_update().get(pk=sheet.pk)
        before = {
            "status": sheet.status,
            "entries": entries_snapshot(sheet.entries.select_related("project")),
        }
        if sheet.status == Timesheet.Status.APPROVED:
            period_start = pay_period_for(sheet.week_start, settings.PAY_PERIOD_ANCHOR)[0]
            approvals.reset_approval(
                employee, period_start, actor=handler, change_request=request, at=now
            )
            sheet.refresh_from_db()
        replace_entries(sheet, entries)
        if sheet.submitted_at is None:  # never submitted: the edit is its first submission (D-52)
            sheet.submitted_at = now
            sheet.is_late = now > deadline_for(sheet.week_start, company_tz())
        sheet.status = Timesheet.Status.SUBMITTED
        sheet.reopen_until = None
        sheet.save(update_fields=["status", "submitted_at", "is_late", "reopen_until"])
        record(
            AuditLog.Action.UPDATE,
            "Timesheet",
            sheet.pk,
            actor=handler,
            before=before,
            after={"status": sheet.status, "entries": entries_snapshot(entries)},
            change_request=request,
        )
        _resolve(request, handler, ChangeRequest.Status.EDITED, note, now)
    return request


def approval_week(viewer, employee, week_start, now):
    """(period row, week view) for the approver; 403 unless the viewer approves this employee."""
    period_start = pay_period_for(week_start, settings.PAY_PERIOD_ANCHOR)[0]
    row = approvals.period_row(viewer, employee, period_start, now)
    week = next(w for w in row.weeks if w.week_start == week_start)
    return row, week


def edit_for_approval(viewer, employee, week_start, entries, *, now):
    """The approver replaces a SUBMITTED or LOCKED week's rows from Approvals (D-140).

    Same validation as everywhere (submission rules only for a submitted week). The week keeps
    its status and its submission time: a locked week stays locked and "not submitted by
    employee" (D-141). Not while the employee's reopen window is open, with an open change
    request, or once the period is approved (approvals.edit_blockers).
    """
    row, week = approval_week(viewer, employee, week_start, now)
    problems = approvals.edit_blockers(row, week)
    if problems:
        raise ValidationError(problems)
    status = week.state.status
    errors = validate_entries(employee, week_start, entries)
    if status == Timesheet.Status.SUBMITTED:
        errors += submission_errors(entries)
    if errors:
        raise ValidationError(errors)
    with transaction.atomic():
        sheet = (
            Timesheet.objects.select_for_update()
            .filter(employee=employee, week_start=week_start)
            .first()
        )
        if sheet is None:  # a locked week nobody ever opened
            sheet = Timesheet.objects.create(
                employee=employee, week_start=week_start, status=Timesheet.Status.LOCKED
            )
        before = entries_snapshot(sheet.entries.select_related("project"))
        replace_entries(sheet, entries)
        record(
            AuditLog.Action.UPDATE,
            "Timesheet",
            sheet.pk,
            actor=viewer,
            before={"status": status, "entries": before},
            after={"status": status, "entries": entries_snapshot(entries), "via": "approvals"},
        )
    return sheet


def unlock_from_approvals(manager, employee, week_start, *, now):
    """The Unlock button on the approvals page, for a LOCKED week (D-06, D-59).

    Resolves the employee's open request if there is one; otherwise records a
    manager-authored request (status UNLOCKED). Either way the unlock is audited.
    """
    if not can_approve(manager, employee):
        raise PermissionDenied("Only the employee's approver can unlock this week.")
    sheet = load_sheet(employee, week_start)
    if week_state(employee, week_start, sheet, now).status != Timesheet.Status.LOCKED:
        raise ValidationError("Only a locked week can be unlocked here.")
    with transaction.atomic():
        if sheet is None:  # a missed week with no timesheet at all
            sheet = Timesheet.objects.create(
                employee=employee, week_start=week_start, status=Timesheet.Status.LOCKED
            )
        existing = open_request_for(sheet)
        if existing:
            return unlock_request(existing, manager, "Unlocked from the approvals page.", now=now)
        request = ChangeRequest.objects.create(
            timesheet=sheet,
            requester=manager,
            reason="Unlocked by the manager from the approvals page.",
            status=ChangeRequest.Status.UNLOCKED,
            reviewer=manager,
            resolved_at=now,
        )
        approvals.unlock_week(sheet, actor=manager, change_request=request, at=now)
    return request
