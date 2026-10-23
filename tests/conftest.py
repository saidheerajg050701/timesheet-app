"""Shared fixtures (B.11): fixed clock and directory people. More arrive in later phases."""

from datetime import datetime
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.conf import settings

from directory.models import User
from tests.factories import EmployeeFactory, TeamFactory, UserFactory


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

    def person(code, manager=None, **extra):
        return EmployeeFactory(
            employee_code=code, email=f"{code.lower()}@yourcompany.com", manager=manager, **extra
        )

    platform = TeamFactory(name="Platform", department="Technology")
    ceo = person("CEO", is_admin=True, job_title="CEO")
    hr = person("HR", ceo, is_admin=True, job_title="HR Manager")
    director = person("DIRECTOR", ceo, job_title="Engineering Director")
    manager = person("MANAGER", director, job_title="Engineering Manager", team=platform)
    dev1 = person("DEV1", manager, first_name="John", last_name="Kim", team=platform)
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
