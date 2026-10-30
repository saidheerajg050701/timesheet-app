from datetime import date
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from audit.models import AuditLog
from directory.models import Employee, Team, User

HEADER = (
    "employee_code,email,first_name,last_name,job_title,team,department,manager_code,"
    "location,hire_date,is_admin,is_payroll,status"
)


def write_csv(tmp_path, lines, header=HEADER, name="people.csv"):
    path = tmp_path / name
    path.write_text("\n".join([header, *lines]) + "\n", encoding="utf-8")
    return path


def run_import(path):
    out = StringIO()
    call_command("import_employees", str(path), stdout=out, stderr=StringIO())
    return out.getvalue()


@pytest.mark.django_db
def test_import_creates_people_teams_and_manager_links(tmp_path):
    """T-53: import creates employees, teams, flags, status, end_date and manager links."""
    path = write_csv(
        tmp_path,
        [
            # The report comes before their manager: linked in the second pass.
            "E-2,Dev.One@YourCompany.com,Dev,One,Engineer,Platform,Technology,E-1,Frisco,"
            "2024-02-01,false,false,ACTIVE,",
            "E-1,boss@yourcompany.com,Big,Boss,CEO,Leadership,Executive,,Dallas,"
            "2019-01-07,TRUE,no,ACTIVE,",
            "E-3,gone@yourcompany.com,Was,Here,Analyst,Payroll,Finance,E-1,,"
            "2021-05-03,false,yes,INACTIVE,2026-06-30",
        ],
        header=HEADER + ",end_date",
    )
    output = run_import(path)

    assert "3 created, 0 updated" in output
    boss, dev, gone = (Employee.objects.get(employee_code=c) for c in ("E-1", "E-2", "E-3"))
    assert dev.manager == boss and gone.manager == boss and boss.manager is None
    assert dev.email == "dev.one@yourcompany.com"
    assert dev.team.name == "Platform" and dev.team.department == "Technology"
    assert boss.is_admin and not boss.is_payroll
    assert gone.is_payroll and gone.status == Employee.Status.INACTIVE
    assert gone.end_date == date(2026, 6, 30) and gone.hire_date == date(2021, 5, 3)
    assert Team.objects.count() == 3
    created = AuditLog.objects.filter(action=AuditLog.Action.CREATE, entity_type="Employee")
    assert set(created.values_list("entity_id", flat=True)) == {"E-1", "E-2", "E-3"}
    assert set(AuditLog.objects.values_list("system_actor", flat=True)) == {"import_employees"}
    assert created.get(entity_id="E-2").after["manager_code"] == "E-1"


@pytest.mark.django_db
def test_reimport_updates_in_place_and_syncs_account(tmp_path):
    """T-54: re-importing the same codes updates in place, syncs the User and audits changes."""
    first = write_csv(
        tmp_path,
        [
            "E-1,boss@yourcompany.com,Big,Boss,CEO,Leadership,Executive,,Dallas,"
            "2019-01-07,true,false,ACTIVE",
            "E-2,dev@yourcompany.com,Dev,One,Engineer,Platform,Technology,E-1,Frisco,"
            "2024-02-01,false,false,ACTIVE",
        ],
    )
    run_import(first)
    dev = Employee.objects.get(employee_code="E-2")
    dev.end_date = date(2030, 1, 1)
    dev.save()
    user = User.objects.create_user(password="Long-Enough-Pass-1", employee=dev)

    second = write_csv(
        tmp_path,
        [
            "E-1,boss@yourcompany.com,Big,Boss,CEO,Leadership,Executive,,Dallas,"
            "2019-01-07,true,false,ACTIVE",
            "E-2,New.Dev@YourCompany.com,Dev,One,Senior Engineer,Platform,Technology,,Frisco,"
            "2024-02-01,true,false,INACTIVE",
        ],
        name="people-v2.csv",
    )
    output = run_import(second)

    assert "0 created, 1 updated, 1 unchanged" in output
    assert Employee.objects.count() == 2
    dev.refresh_from_db()
    user.refresh_from_db()
    assert dev.job_title == "Senior Engineer" and dev.manager is None
    assert dev.end_date == date(2030, 1, 1)  # no end_date column: left untouched
    assert user.email == "new.dev@yourcompany.com"  # D-20
    assert user.is_staff and user.is_superuser and not user.is_active  # D-13
    update = AuditLog.objects.get(action=AuditLog.Action.UPDATE, entity_id="E-2")
    assert update.before == {
        "email": "dev@yourcompany.com",
        "job_title": "Engineer",
        "manager_code": "E-1",
        "status": "ACTIVE",
        "is_admin": False,
    }
    assert update.after["email"] == "new.dev@yourcompany.com"
    assert not AuditLog.objects.filter(action=AuditLog.Action.UPDATE, entity_id="E-1").exists()


@pytest.mark.django_db
def test_invalid_csv_imports_nothing_and_lists_every_error(tmp_path):
    """T-55: a CSV with errors imports nothing and lists every error with its line."""
    path = write_csv(
        tmp_path,
        [
            "E-1,boss@yourcompany.com,Big,Boss,CEO,Leadership,Executive,,Dallas,"
            "2019-01-07,true,false,ACTIVE",
            "E-2,dev@yourcompany.com,Dev,One,Engineer,Platform,Technology,E-9,Frisco,"
            "2024-02-01,false,false,ACTIVE",
            "E-3,qa@yourcompany.com,Q,A,QA,Platform,Technology,E-1,Frisco,"
            "01/02/2024,maybe,false,RETIRED",
            "E-1,BOSS@yourcompany.com,Copy,Boss,CEO,Leadership,Executive,,Dallas,"
            "2019-01-07,true,false,ACTIVE",
            "E-5,not-an-email,X,Y,Z,Platform,Technology,E-5,Frisco,2024-02-01,false,false,ACTIVE",
        ],
    )
    err = StringIO()
    with pytest.raises(CommandError, match="Nothing imported"):
        call_command("import_employees", str(path), stdout=StringIO(), stderr=err)
    errors = err.getvalue()
    for expected in (
        "Line 4: hire_date must be a date",
        "Line 4: is_admin must be true or false",
        "Line 4: status must be ACTIVE or INACTIVE",
        "Line 6: 'not-an-email' is not a valid email address.",
        "Line 6: an employee cannot be their own manager.",
    ):
        assert expected in errors
    assert not Employee.objects.exists() and not Team.objects.exists()

    # Row-level errors fixed, the cross-row problems remain.
    path = write_csv(
        tmp_path,
        [
            "E-1,boss@yourcompany.com,Big,Boss,CEO,Leadership,Executive,,Dallas,"
            "2019-01-07,true,false,ACTIVE",
            "E-2,dev@yourcompany.com,Dev,One,Engineer,Platform,Technology,E-9,Frisco,"
            "2024-02-01,false,false,ACTIVE",
            "E-1,BOSS@yourcompany.com,Copy,Boss,CEO,Leadership,Executive,,Dallas,"
            "2019-01-07,true,false,ACTIVE",
        ],
    )
    err = StringIO()
    with pytest.raises(CommandError):
        call_command("import_employees", str(path), stdout=StringIO(), stderr=err)
    errors = err.getvalue()
    assert "Line 3: manager_code E-9 does not exist." in errors
    assert "Line 4: employee_code E-1 repeats line 2." in errors
    assert "Line 4: email boss@yourcompany.com repeats line 2." in errors
    assert not Employee.objects.exists()

    missing = write_csv(tmp_path, ["E-1,boss@yourcompany.com"], header="employee_code,email")
    with pytest.raises(CommandError):
        call_command(
            "import_employees", str(missing), stdout=StringIO(), stderr=(err := StringIO())
        )
    assert "Missing column(s): first_name, last_name" in err.getvalue()


@pytest.mark.django_db
def test_import_checks_existing_directory(tmp_path, employee):
    """Helper check: managers may already be in the database; emails may not change owner."""
    path = write_csv(
        tmp_path,
        [
            f"E-2,new@yourcompany.com,New,Person,Engineer,,,{employee.employee_code},,,"
            "false,false,ACTIVE",
            f"E-3,{employee.email},Dup,Email,Engineer,,,,,,false,false,ACTIVE",
        ],
    )
    err = StringIO()
    with pytest.raises(CommandError):
        call_command("import_employees", str(path), stdout=StringIO(), stderr=err)
    assert f"Line 3: email {employee.email} already belongs to {employee.employee_code}." in (
        err.getvalue()
    )

    path = write_csv(
        tmp_path,
        [
            f"E-2,new@yourcompany.com,New,Person,Engineer,,,{employee.employee_code},,,"
            "false,false,",
        ],
    )
    run_import(path)
    new = Employee.objects.get(employee_code="E-2")
    assert new.manager == employee and new.team is None and new.status == Employee.Status.ACTIVE


def test_import_reports_missing_file(tmp_path):
    """Helper check: a missing file is a clear error."""
    with pytest.raises(CommandError, match="File not found"):
        call_command("import_employees", str(tmp_path / "nope.csv"))


@pytest.mark.django_db
def test_team_department_change_is_audited(tmp_path):
    """Helper check: a team whose department changes is updated and audited."""
    row = "E-1,a@yourcompany.com,A,B,Analyst,Data,{dept},,,,false,false,ACTIVE"
    run_import(write_csv(tmp_path, [row.format(dept="Technology")]))
    run_import(write_csv(tmp_path, [row.format(dept="Analytics")]))
    assert Team.objects.get(name="Data").department == "Analytics"
    change = AuditLog.objects.get(entity_type="Team", action=AuditLog.Action.UPDATE)
    assert change.before == {"department": "Technology"}
