from types import SimpleNamespace

from django.db import router

from directory.models import User
from payroll.routers import PayrollRouter

payroll_router = PayrollRouter()


def model_in(app_label):
    return SimpleNamespace(_meta=SimpleNamespace(app_label=app_label))


def test_payroll_app_reads_and_writes_payroll_database():
    """Helper check: payroll models are routed to the payroll database."""
    assert payroll_router.db_for_read(model_in("payroll")) == "payroll"
    assert payroll_router.db_for_write(model_in("payroll")) == "payroll"


def test_other_apps_use_default_database():
    """Helper check: every other app stays on the default database."""
    assert payroll_router.db_for_read(model_in("directory")) is None
    assert payroll_router.db_for_write(model_in("timesheets")) is None
    assert router.db_for_write(User) == "default"


def test_migrations_stay_in_their_own_database():
    """Helper check: payroll tables only in payroll.sqlite3, other tables never there."""
    assert payroll_router.allow_migrate("payroll", "payroll") is True
    assert payroll_router.allow_migrate("default", "payroll") is False
    assert payroll_router.allow_migrate("default", "directory") is True
    assert payroll_router.allow_migrate("payroll", "directory") is False
    assert payroll_router.allow_migrate("payroll", "auth") is False


def test_no_relations_across_databases():
    """Helper check: relations only between objects in the same database."""
    assert payroll_router.allow_relation(model_in("payroll"), model_in("payroll")) is True
    assert payroll_router.allow_relation(model_in("directory"), model_in("audit")) is True
    assert payroll_router.allow_relation(model_in("payroll"), model_in("directory")) is False
