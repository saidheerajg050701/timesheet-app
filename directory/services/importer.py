"""Load employees into the directory from CSV-style rows (Phase 2, B.7).

Upsert by employee_code, create teams, link managers in a second pass, and write one audit
row per created or changed employee or team. The whole file is validated first; any error
means nothing is imported.
"""

from dataclasses import dataclass
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from audit.models import AuditLog
from audit.services.log import record
from directory.models import Employee, Team

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


def import_employees(rows, *, columns, system_actor):
    """Validate and import rows (dicts keyed by column name). Raises EmployeeImportError."""
    has_end_date = "end_date" in columns
    parsed = _validate(list(rows), columns)
    result = ImportResult()
    with transaction.atomic():
        existing = {e.employee_code: e for e in Employee.objects.select_related("team", "manager")}
        before = {code: _snapshot(e) for code, e in existing.items()}
        employees = {}
        for row in parsed:  # pass 1: people and teams
            team = _upsert_team(row, result, system_actor) if row.team else None
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
        for code, employee in employees.items():
            after = _snapshot(employee)
            if code not in before:
                record(
                    AuditLog.Action.CREATE, "Employee", code, system_actor=system_actor, after=after
                )
                result.created += 1
                continue
            changed = [field for field in after if after[field] != before[code][field]]
            if not changed:
                result.unchanged += 1
                continue
            record(
                AuditLog.Action.UPDATE,
                "Employee",
                code,
                system_actor=system_actor,
                before={field: before[code][field] for field in changed},
                after={field: after[field] for field in changed},
            )
            result.updated += 1
    return result


def _upsert_team(row, result, system_actor):
    team, created = Team.objects.get_or_create(
        name=row.team, defaults={"department": row.department}
    )
    if created:
        result.teams_created += 1
        record(
            AuditLog.Action.CREATE,
            "Team",
            team.name,
            system_actor=system_actor,
            after={"department": team.department},
        )
    elif team.department != row.department:
        old = team.department
        team.department = row.department
        team.save()
        record(
            AuditLog.Action.UPDATE,
            "Team",
            team.name,
            system_actor=system_actor,
            before={"department": old},
            after={"department": team.department},
        )
    return team


def _find_employee(code, employees):
    return employees.get(code) or Employee.objects.get(employee_code=code)


def _snapshot(employee):
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
        return (raw.get(column) or "").strip()

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
