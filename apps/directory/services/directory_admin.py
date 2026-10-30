"""HR changes made in Django Admin (FR-10, D-87–D-92).

Every add, edit, deactivate, reactivate, password reset and export goes through these
functions: they check the directory rules, save, and write the audit row with the acting
admin in the same transaction. Admin classes only call them.
"""

import csv
import io
from datetime import date
from decimal import Decimal

from axes.utils import reset as reset_lockout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services.log import record
from apps.directory.models import Employee, User
from apps.directory.services.importer import OPTIONAL_COLUMNS, REQUIRED_COLUMNS, employee_snapshot
from apps.directory.services.permissions import manager_map
from apps.directory.services.rules import creates_loop, domain_error, in_company_domain
from apps.payroll.services.export import safe_cell
from apps.timesheets.models import TimeEntry

ACTIVE = Employee.Status.ACTIVE
INACTIVE = Employee.Status.INACTIVE


def snapshot(employee):
    """Everything HR can change on an employee, as plain values for the audit row."""
    return {
        **employee_snapshot(employee),
        "expected_weekly_minutes": employee.expected_weekly_minutes,
    }


def diff(before, after):
    changed = [field for field in after if after[field] != before.get(field)]
    return {f: before.get(f) for f in changed}, {f: after[f] for f in changed}


def other_active_admins(*excluded):
    return (
        Employee.objects.filter(is_admin=True, status=ACTIVE)
        .exclude(pk__in=[e.pk for e in excluded if e.pk])
        .exists()
    )


def entry_dates(employee):
    """(first, last) saved work date of the employee's entries, or (None, None)."""
    dates = TimeEntry.objects.filter(timesheet__employee=employee).values_list(
        "work_date", flat=True
    )
    return dates.order_by("work_date").first(), dates.order_by("-work_date").first()


# --- employees ----------------------------------------------------------------------------


def check_employee(actor, employee):
    """Errors for an added or edited employee, as {field: [messages]} (D-89)."""
    errors = {}

    def refuse(field, message):
        errors.setdefault(field, []).append(message)

    before = Employee.objects.filter(pk=employee.pk).first() if employee.pk else None
    email = employee.email.strip().lower()
    if before is None or email != before.email:
        if not in_company_domain(email):
            refuse("email", domain_error(email))
        account = getattr(employee, "account", None) if employee.pk else None
        taken = Employee.objects.filter(email__iexact=email).exclude(pk=employee.pk).exists()
        taken |= (
            User.objects.filter(email__iexact=email)
            .exclude(pk=account.pk if account else None)
            .exists()
        )
        if taken:
            refuse("email", f"{email} already belongs to someone else.")

    manager_id = employee.manager_id
    if manager_id is not None and manager_id == employee.pk:
        refuse("manager", "An employee cannot be their own manager.")
    elif before is None or manager_id != before.manager_id:
        if manager_id is not None and employee.manager.status != ACTIVE:
            refuse("manager", f"{employee.manager} is inactive; choose an active manager.")
        if employee.pk and creates_loop(manager_map(), employee.pk, manager_id):
            refuse("manager", "That manager reports to this employee: it would make a loop.")

    if before is not None and before.is_admin and not employee.is_admin:
        if before.pk == actor.pk:
            refuse("is_admin", "You cannot remove your own admin flag.")
        elif before.status == ACTIVE and not other_active_admins(before):
            refuse("is_admin", "At least one active admin must remain.")

    if employee.hire_date and (before is None or employee.hire_date != before.hire_date):
        first, _ = entry_dates(employee) if employee.pk else (None, None)
        if first and employee.hire_date > first:
            refuse("hire_date", f"This employee has time entries from {first:%b %-d, %Y}.")
        if employee.end_date and employee.hire_date > employee.end_date:
            refuse("hire_date", "The hire date is after the end date.")
    return errors


def save_employee(actor, employee):
    """Add or change an employee and audit it (D-88). Raises ValidationError."""
    errors = check_employee(actor, employee)
    if errors:
        raise ValidationError(errors)
    with transaction.atomic():
        old = Employee.objects.select_related("team", "manager").filter(pk=employee.pk).first()
        before = snapshot(old) if old else None
        employee.save()
        after = snapshot(employee)
        if before is None:
            record(
                AuditLog.Action.CREATE,
                "Employee",
                employee.employee_code,
                actor=actor,
                after=after,
            )
            return employee
        changed_before, changed_after = diff(before, after)
        if changed_after:
            record(
                AuditLog.Action.UPDATE,
                "Employee",
                employee.employee_code,
                actor=actor,
                before=changed_before,
                after=changed_after,
            )
    return employee


def deactivate(actor, employees, end_date):
    """INACTIVE + end_date for every selected employee, or nothing at all (D-90)."""
    employees = list(employees)
    today = timezone.localdate()
    selected = {e.pk for e in employees}
    problems = []
    if end_date > today:
        problems.append("The end date cannot be in the future.")
    for employee in employees:
        name = f"{employee.first_name} {employee.last_name}"
        if employee.pk == actor.pk:
            problems.append("You cannot deactivate yourself.")
            continue
        if employee.status != ACTIVE:
            problems.append(f"{name} is already inactive.")
            continue
        reports = employee.reports.filter(status=ACTIVE).exclude(pk__in=selected)
        if reports.exists():
            problems.append(
                f"{name} still manages {reports.count()} active people; "
                "reassign their reports first."
            )
        if employee.hire_date and end_date < employee.hire_date:
            problems.append(f"{name}: the end date is before their hire date.")
        _, last = entry_dates(employee)
        if last and end_date < last:
            problems.append(f"{name} has time entries up to {last:%b %-d, %Y}; pick a later date.")
    admins = [e for e in employees if e.is_admin and e.status == ACTIVE]
    if admins and not other_active_admins(*admins):
        problems.append("At least one active admin must remain.")
    if problems:
        raise ValidationError(problems)
    with transaction.atomic():
        for employee in employees:
            _set_status(actor, employee, INACTIVE, end_date)
    return len(employees)


def reactivate(actor, employees):
    """ACTIVE again with end_date cleared; hire_date and history unchanged (D-90)."""
    employees = list(employees)
    problems = [
        f"{e.first_name} {e.last_name} is already active." for e in employees if e.status == ACTIVE
    ]
    if problems:
        raise ValidationError(problems)
    with transaction.atomic():
        for employee in employees:
            _set_status(actor, employee, ACTIVE, None)
    return len(employees)


def _set_status(actor, employee, status, end_date):
    before = {"status": employee.status, "end_date": employee.end_date}
    employee.status, employee.end_date = status, end_date
    employee.save()  # the User follows (D-13): an inactive account's session ends
    record(
        AuditLog.Action.UPDATE,
        "Employee",
        employee.employee_code,
        actor=actor,
        before=before,
        after={"status": status, "end_date": end_date},
    )


def reset_password(actor, employee, password):
    """A temporary password HR chooses; the person must change it at next login (D-91).

    The audit row records that the password changed, never the password or its hash.
    """
    user = User.objects.filter(employee=employee).first()
    if user is None:
        raise ValidationError(f"{employee} has no account yet; they can sign up themselves.")
    if employee.pk == actor.pk:
        raise ValidationError("Change your own password on your Profile page.")
    validate_password(password, user)
    with transaction.atomic():
        user.set_password(password)
        user.must_change_password = True
        user.save(update_fields=["password", "must_change_password"])
        cleared = reset_lockout(username=user.email)
        record(
            AuditLog.Action.UPDATE,
            "User",
            user.email,
            actor=actor,
            after={
                "changed": ["password"],
                "must_change_password": True,
                "lockout_cleared": cleared,
            },
        )
    return user


# --- teams and projects -------------------------------------------------------------------


def _plain(value):
    """Audit rows are JSON: amounts and dates are kept as exact text (D-168)."""
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, date):
        return value.isoformat()
    return value


def save_simple(actor, obj, entity_type, key, fields):
    with transaction.atomic():
        old = type(obj).objects.filter(pk=obj.pk).first() if obj.pk else None
        before = {f: _plain(getattr(old, f)) for f in fields} if old else None
        obj.save()
        after = {f: _plain(getattr(obj, f)) for f in fields}
        if before is None:
            record(AuditLog.Action.CREATE, entity_type, key(obj), actor=actor, after=after)
            return obj
        changed_before, changed_after = diff(before, after)
        if changed_after:
            record(
                AuditLog.Action.UPDATE,
                entity_type,
                key(old),
                actor=actor,
                before=changed_before,
                after=changed_after,
            )
    return obj


def save_team(actor, team):
    """Add or change a team; audited by its (old) name like the importer (D-88)."""
    return save_simple(actor, team, "Team", lambda t: t.name, ("name", "department"))


# --- CSV export ---------------------------------------------------------------------------

EXPORT_COLUMNS = REQUIRED_COLUMNS + OPTIONAL_COLUMNS


def export_row(employee):
    s = employee_snapshot(employee)
    return {
        "employee_code": employee.employee_code,
        "email": s["email"],
        "first_name": s["first_name"],
        "last_name": s["last_name"],
        "job_title": s["job_title"],
        "team": s["team"],
        "department": employee.team.department if employee.team else "",
        "manager_code": s["manager_code"],
        "location": s["location"],
        "hire_date": s["hire_date"] or "",
        "is_admin": "true" if s["is_admin"] else "false",
        "is_payroll": "true" if s["is_payroll"] else "false",
        "status": s["status"],
        "end_date": s["end_date"] or "",
    }


def export_employees(actor, employees):
    """CSV in the import's columns, formula-safe (D-68), audited as EXPORT (D-92)."""
    employees = list(employees.select_related("team", "manager").order_by("employee_code"))
    out = io.StringIO()
    writer = csv.DictWriter(out, fieldnames=EXPORT_COLUMNS, lineterminator="\r\n")
    writer.writeheader()
    for employee in employees:
        writer.writerow({k: safe_cell(v) for k, v in export_row(employee).items()})
    record(
        AuditLog.Action.EXPORT,
        "Employee",
        "csv",
        actor=actor,
        after={"rows": len(employees)},
    )
    return out.getvalue()
