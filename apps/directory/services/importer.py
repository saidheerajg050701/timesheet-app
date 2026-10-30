"""Load employees into the directory from CSV-style rows (Phase 2, B.7).

Upsert by employee_code, create teams, link managers in a second pass, and write one audit
row per created or changed employee or team. The whole file is validated first; any error
means nothing is imported. Admin uploads run it twice: a dry run for the preview, then the
real import with the admin as actor and the D-89 rules for that admin (D-92).
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from apps.audit.models import AuditLog
from apps.audit.services.log import record
from apps.directory.models import Employee, Team
from apps.directory.services.rules import cycle_members, domain_error, in_company_domain
from apps.payroll.services.export import FORMULA_STARTS

REQUIRED_COLUMNS = (
    "employee_code",
    "email",
    "first_name",
    "last_name",
    "job_title",
    "team",
    "department",
    "manager_code",
    "location",
    "hire_date",
    "is_admin",
    "is_payroll",
    "status",
)
OPTIONAL_COLUMNS = ("end_date",)  # D-19
TRUE_VALUES = {"true", "yes", "y", "1"}
FALSE_VALUES = {"false", "no", "n", "0", ""}
FIRST_DATA_LINE = 2  # line 1 is the header


class EmployeeImportError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"{len(errors)} error(s) in employee import")


@dataclass
class ImportResult:
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    teams_created: int = 0
    changes: list = field(default_factory=list)  # [(code, "created"|"updated", {f: (old, new)})]


@dataclass
class _Row:
    line: int
    code: str
    email: str
    first_name: str
    last_name: str
    job_title: str
    team: str
    department: str
    manager_code: str
    location: str
    hire_date: date | None
    end_date: date | None
    is_admin: bool
    is_payroll: bool
    status: str


def read_csv(text):
    """(columns, rows) from CSV text; a leading BOM (Excel) is ignored."""
    reader = csv.DictReader(io.StringIO(text.removeprefix("\ufeff")))
    columns = [c.strip() for c in reader.fieldnames or []]
    reader.fieldnames = columns
    return columns, list(reader)


def import_employees(rows, *, columns, actor=None, system_actor="", dry_run=False):
    """Validate and import rows (dicts keyed by column name). Raises EmployeeImportError.

    `actor` (an admin Employee) adds that admin's rules (D-89); `dry_run` does everything,
    audit rows included, and then rolls it all back — the result is the preview.
    """
    who = {"actor": actor, "system_actor": system_actor}
    has_end_date = "end_date" in columns
    parsed = _validate(list(rows), columns)
    result = ImportResult()
    with transaction.atomic():
        existing = {e.employee_code: e for e in Employee.objects.select_related("team", "manager")}
        before = {code: employee_snapshot(e) for code, e in existing.items()}
        had_admin = any(
            b["is_admin"] and b["status"] == Employee.Status.ACTIVE for b in before.values()
        )
        employees = {}
        for row in parsed:  # pass 1: people and teams
            team = _upsert_team(row, result, who) if row.team else None
            employee = existing.get(row.code) or Employee(employee_code=row.code)
            employee.email = row.email
            employee.first_name = row.first_name
            employee.last_name = row.last_name
            employee.job_title = row.job_title
            employee.team = team
            employee.location = row.location
            employee.hire_date = row.hire_date
            if has_end_date:
                employee.end_date = row.end_date
            employee.status = row.status
            employee.is_admin = row.is_admin
            employee.is_payroll = row.is_payroll
            employee.save()
            employees[row.code] = employee
        for row in parsed:  # pass 2: managers (may be listed after their reports)
            employee = employees[row.code]
            manager = _find_employee(row.manager_code, employees) if row.manager_code else None
            if employee.manager_id != (manager.pk if manager else None):
                employee.manager = manager
                employee.save()
        problems = _rule_errors(parsed, before, employees, actor, had_admin)
        if problems:
            raise EmployeeImportError(problems)
        for code, employee in employees.items():
            after = employee_snapshot(employee)
            if code not in before:
                record(AuditLog.Action.CREATE, "Employee", code, after=after, **who)
                result.created += 1
                result.changes.append((code, "created", {}))
                continue
            changed = [f for f in after if after[f] != before[code][f]]
            if not changed:
                result.unchanged += 1
                continue
            record(
                AuditLog.Action.UPDATE,
                "Employee",
                code,
                before={f: before[code][f] for f in changed},
                after={f: after[f] for f in changed},
                **who,
            )
            result.updated += 1
            result.changes.append(
                (code, "updated", {f: (before[code][f], after[f]) for f in changed})
            )
        if dry_run:
            transaction.set_rollback(True)
    return result


def _rule_errors(parsed, before, employees, actor, had_admin):
    """Checks on the imported result, before anything is committed (D-89, D-90)."""
    errors = []
    looping = cycle_members(dict(Employee.objects.values_list("pk", "manager_id")))
    active = Employee.Status.ACTIVE
    for row in parsed:
        employee = employees[row.code]
        old = before.get(row.code)
        if employee.pk in looping:
            errors.append(
                f"Line {row.line}: manager_code {row.manager_code} makes a reporting loop."
            )
        if actor is None:
            continue
        if old is None or row.email != old["email"]:
            if not in_company_domain(row.email):
                errors.append(f"Line {row.line}: {domain_error(row.email)}")
        if row.manager_code and (old is None or row.manager_code != old["manager_code"]):
            if employee.manager.status != active:
                errors.append(f"Line {row.line}: manager {row.manager_code} is inactive.")
        if row.code == actor.employee_code and old is not None:
            if old["is_admin"] and not row.is_admin:
                errors.append(f"Line {row.line}: you cannot remove your own admin flag.")
            if row.status != active:
                errors.append(f"Line {row.line}: you cannot deactivate yourself.")
        if old is not None and old["status"] == active and row.status != active:
            if employee.reports.filter(status=active).exists():
                errors.append(
                    f"Line {row.line}: {row.code} still manages active people; "
                    "reassign their reports first."
                )
    if had_admin and not Employee.objects.filter(is_admin=True, status=active).exists():
        errors.append("The file would leave no active admin; at least one must remain.")
    return errors


def _upsert_team(row, result, who):
    team, created = Team.objects.get_or_create(
        name=row.team, defaults={"department": row.department}
    )
    if created:
        result.teams_created += 1
        record(
            AuditLog.Action.CREATE,
            "Team",
            team.name,
            after={"department": team.department},
            **who,
        )
    elif team.department != row.department:
        old = team.department
        team.department = row.department
        team.save()
        record(
            AuditLog.Action.UPDATE,
            "Team",
            team.name,
            before={"department": old},
            after={"department": team.department},
            **who,
        )
    return team


def _find_employee(code, employees):
    return employees.get(code) or Employee.objects.get(employee_code=code)


def employee_snapshot(employee):
    return {
        "email": employee.email,
        "first_name": employee.first_name,
        "last_name": employee.last_name,
        "job_title": employee.job_title,
        "team": employee.team.name if employee.team else "",
        "manager_code": employee.manager.employee_code if employee.manager else "",
        "location": employee.location,
        "hire_date": employee.hire_date.isoformat() if employee.hire_date else None,
        "end_date": employee.end_date.isoformat() if employee.end_date else None,
        "status": employee.status,
        "is_admin": employee.is_admin,
        "is_payroll": employee.is_payroll,
    }


# --- validation -------------------------------------------------------------------------


def _validate(rows, columns):
    missing = [c for c in REQUIRED_COLUMNS if c not in columns]
    if missing:
        raise EmployeeImportError([f"Missing column(s): {', '.join(missing)}"])
    errors, parsed = [], []
    for index, raw in enumerate(rows):
        line = index + FIRST_DATA_LINE
        row_errors = []
        row = _parse(raw, line, row_errors)
        errors.extend(row_errors)
        if not row_errors:
            parsed.append(row)
    if not errors:
        errors.extend(_cross_check(parsed))
    if errors:
        raise EmployeeImportError(errors)
    return parsed


def _parse(raw, line, errors):
    def text(column):
        value = (raw.get(column) or "").strip()
        if value[:1] == "'" and value[1:2] in FORMULA_STARTS:  # a formula-safe export (D-92)
            value = value[1:]
        return value

    def required(column):
        value = text(column)
        if not value:
            errors.append(f"Line {line}: {column} is required.")
        return value

    def flag(column):
        value = text(column).lower()
        if value in TRUE_VALUES:
            return True
        if value not in FALSE_VALUES:
            errors.append(f"Line {line}: {column} must be true or false, not {text(column)!r}.")
        return False

    def iso_date(column):
        value = text(column)
        if not value:
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            errors.append(f"Line {line}: {column} must be a date like 2024-01-31, not {value!r}.")
            return None

    email = required("email").lower()
    if email:
        try:
            validate_email(email)
        except ValidationError:
            errors.append(f"Line {line}: {email!r} is not a valid email address.")
    status = text("status").upper() or Employee.Status.ACTIVE
    if status not in Employee.Status.values:
        errors.append(f"Line {line}: status must be ACTIVE or INACTIVE, not {text('status')!r}.")
    team, department = text("team"), text("department")
    if team and not department:
        errors.append(f"Line {line}: department is required when team is set.")
    row = _Row(
        line=line,
        code=required("employee_code").upper(),
        email=email,
        first_name=required("first_name"),
        last_name=required("last_name"),
        job_title=required("job_title"),
        team=team,
        department=department,
        manager_code=text("manager_code").upper(),
        location=text("location"),
        hire_date=iso_date("hire_date"),
        end_date=iso_date("end_date"),
        is_admin=flag("is_admin"),
        is_payroll=flag("is_payroll"),
        status=status,
    )
    if row.hire_date and row.end_date and row.end_date < row.hire_date:
        errors.append(f"Line {line}: end_date is before hire_date.")
    if row.manager_code and row.manager_code == row.code:
        errors.append(f"Line {line}: an employee cannot be their own manager.")
    return row


def _cross_check(parsed):
    errors = []
    first_line_for_code, first_line_for_email = {}, {}
    for row in parsed:
        if row.code in first_line_for_code:
            errors.append(
                f"Line {row.line}: employee_code {row.code} repeats line "
                f"{first_line_for_code[row.code]}."
            )
        first_line_for_code.setdefault(row.code, row.line)
        if row.email in first_line_for_email:
            errors.append(
                f"Line {row.line}: email {row.email} repeats line "
                f"{first_line_for_email[row.email]}."
            )
        first_line_for_email.setdefault(row.email, row.line)

    owners = dict(
        Employee.objects.filter(email__in=first_line_for_email).values_list(
            "email", "employee_code"
        )
    )
    known = set(
        Employee.objects.filter(
            employee_code__in={r.manager_code for r in parsed if r.manager_code}
        ).values_list("employee_code", flat=True)
    )
    for row in parsed:
        owner = owners.get(row.email)
        if owner and owner != row.code:
            errors.append(f"Line {row.line}: email {row.email} already belongs to {owner}.")
        if row.manager_code and row.manager_code not in first_line_for_code:
            if row.manager_code not in known:
                errors.append(f"Line {row.line}: manager_code {row.manager_code} does not exist.")
    return errors
