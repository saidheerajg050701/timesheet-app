"""Shared fixtures (B.11): fixed clock and directory people. More arrive in later phases."""

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
import time_machine
from django.conf import settings

from tests.factories import EmployeeFactory, UserFactory


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
