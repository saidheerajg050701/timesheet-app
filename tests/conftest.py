"""Shared fixtures (B.11): fixed clock and directory people. More arrive in later phases."""

from datetime import date, datetime, time, timedelta
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.conf import settings

from apps.directory.models import User
from tests.factories import (
    EmployeeFactory,
    ProjectFactory,
    TeamFactory,
    TimeEntryFactory,
    TimesheetFactory,
    UserFactory,
)


@pytest.fixture(autouse=True)
def pay_period_anchor(settings):
    """Every test uses the Sunday anchor, whatever .env says (D-113)."""
    settings.PAY_PERIOD_ANCHOR = date(2026, 1, 4)
    return settings.PAY_PERIOD_ANCHOR


@pytest.fixture
def company_tz():
    return ZoneInfo(settings.COMPANY_TZ)


@pytest.fixture
def fixed_now(company_tz):
    """Freeze the clock at Wednesday 2026-10-21 10:00 company time."""
    now = datetime(2026, 10, 21, 10, 0, tzinfo=company_tz)
    with time_machine.travel(now, tick=False):
        yield now


@pytest.fixture
def employee(db):
    return EmployeeFactory()


@pytest.fixture
def admin_employee(db):
    return EmployeeFactory(is_admin=True)


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def demo_password(settings):
    settings.DEMO_PASSWORD = "Demo-Password-2026!"
    return settings.DEMO_PASSWORD


@pytest.fixture
def admin_client(client, db):
    """A logged-in directory admin (is_staff/is_superuser come from is_admin, D-13)."""
    admin = UserFactory(employee__is_admin=True)
    client.force_login(admin)
    return client


@pytest.fixture
def org(db):
    """A small company mirroring the core demo roles (B.7).

    ceo (admin) → hr (admin), director → manager → dev1, dev2; ceo → ops_manager → ops1;
    ceo → finance (payroll + manager) → payroll (payroll only).
    """

    # Fixed names: random ones depend on test order and can collide with searches ("Kim").
    names = {
        "CEO": ("Asha", "Rao"),
        "HR": ("Hana", "Reed"),
        "DIRECTOR": ("Mark", "Lee"),
        "MANAGER": ("Priya", "Shah"),
        "DEV1": ("John", "Kim"),
        "DEV2": ("Sara", "Ng"),
        "OPSMGR": ("Omar", "Diaz"),
        "OPS1": ("Lena", "Park"),
        "FINANCE": ("Fay", "Moss"),
        "PAYROLL": ("Paul", "Ames"),
    }

    def person(code, manager=None, **extra):
        first, last = names[code]
        extra = {"first_name": first, "last_name": last, **extra}
        return EmployeeFactory(
            employee_code=code, email=f"{code.lower()}@yourcompany.com", manager=manager, **extra
        )

    platform = TeamFactory(name="Platform", department="Technology")
    ceo = person("CEO", is_admin=True, job_title="CEO")
    hr = person("HR", ceo, is_admin=True, job_title="HR Manager")
    director = person("DIRECTOR", ceo, job_title="Engineering Director")
    manager = person("MANAGER", director, job_title="Engineering Manager", team=platform)
    dev1 = person("DEV1", manager, team=platform)
    dev2 = person("DEV2", manager, team=platform)
    ops_manager = person("OPSMGR", ceo, job_title="Operations Manager")
    ops1 = person("OPS1", ops_manager, job_title="Operations Analyst")
    finance = person("FINANCE", ceo, is_payroll=True, job_title="Finance Manager")
    payroll = person("PAYROLL", finance, is_payroll=True, job_title="Payroll Specialist")
    return SimpleNamespace(
        ceo=ceo,
        hr=hr,
        director=director,
        manager=manager,
        dev1=dev1,
        dev2=dev2,
        ops_manager=ops_manager,
        ops1=ops1,
        finance=finance,
        payroll=payroll,
    )


@pytest.fixture
def login_as(client):
    """Log the client in as an employee, creating their account if needed."""

    def _login(employee):
        user = User.objects.filter(employee=employee).first() or UserFactory(employee=employee)
        client.force_login(user)
        return client

    return _login


@pytest.fixture
def project(db):
    return ProjectFactory(number=1, name="Customer Portal")


@pytest.fixture
def draft_sheet_week_of_oct_18(db):
    """A DRAFT timesheet for the week of Sunday 2026-10-18 (deadline Sat 24 Oct 12:00)."""
    return TimesheetFactory(week_start=date(2026, 10, 18))


@pytest.fixture
def make_week(project, fixed_now):
    """A week (its Sunday) with full 09:00–17:00 days Mon–Fri (40 h, no flags) unless told
    otherwise; `days` counts working days from Monday (D-114)."""

    def make(employee, week, status="SUBMITTED", days=5, end=time(17), **extra):
        on_time = datetime(2026, 10, 2, 16, 0, tzinfo=ZoneInfo("America/Chicago"))
        extra.setdefault("submitted_at", on_time if status != "DRAFT" else None)
        sheet = TimesheetFactory(employee=employee, week_start=week, status=status, **extra)
        minutes = (end.hour - 9) * 60
        for offset in range(days):
            TimeEntryFactory(
                timesheet=sheet,
                work_date=week + timedelta(days=1 + offset),  # Monday is the week's 2nd day
                project=project,
                end_time=end,
                minutes=minutes,
            )
        return sheet

    return make


@pytest.fixture
def approve_everyone(django_capture_on_commit_callbacks):
    """Approve everyone still pending in a period, as their manager (an admin for no-manager
    staff), the Change 9 way: weeks they never submitted are approved with what is entered —
    usually nothing, 0.00. A register is READY only once everyone is approved (D-142)."""
    from apps.directory.models import Employee
    from apps.timesheets.models import PeriodApproval
    from apps.timesheets.services.approvals import approve_period, company_period_rows

    def _approve(period_start, now):
        for row in company_period_rows(period_start, now):
            if row.status == PeriodApproval.Status.APPROVED:
                continue
            person = row.employee
            admins = Employee.objects.filter(is_admin=True).exclude(pk=person.pk)
            approver = person.manager or admins.order_by("employee_code").first()
            with django_capture_on_commit_callbacks(execute=True):
                approve_period(approver, person, period_start, now=now, confirm_unsubmitted=True)

    return _approve
