from datetime import date, datetime
from zoneinfo import ZoneInfo

import pytest
from django.db import IntegrityError, transaction

from audit.models import AuditLog
from audit.services.log import record


@pytest.mark.django_db
def test_audit_row_needs_exactly_one_actor(employee):
    """T-52: an AuditLog row with both or neither actor/system_actor is refused (D-14)."""
    with pytest.raises(ValueError, match="exactly one"):
        record(AuditLog.Action.UPDATE, "Employee", 1, actor=employee, system_actor="seed_demo")
    with pytest.raises(ValueError, match="exactly one"):
        record(AuditLog.Action.UPDATE, "Employee", 1)

    for bad in ({"actor": employee, "system_actor": "seed_demo"}, {"system_actor": ""}):
        with pytest.raises(IntegrityError), transaction.atomic():
            AuditLog.objects.create(action="UPDATE", entity_type="Employee", entity_id="1", **bad)
    assert not AuditLog.objects.exists()

    record(AuditLog.Action.UPDATE, "Employee", 1, actor=employee)
    record(AuditLog.Action.SYNC, "PayrollWeek", "all", system_actor="sync_payroll")
    assert AuditLog.objects.count() == 2


@pytest.mark.django_db
def test_record_serialises_values_and_can_backdate(employee):
    """Helper check: dates become JSON strings and `at` back-dates created_at."""
    at = datetime(2026, 9, 1, 10, 0, tzinfo=ZoneInfo("America/Chicago"))
    row = record(
        AuditLog.Action.UPDATE,
        "Employee",
        employee.employee_code,
        actor=employee,
        before={"hire_date": date(2024, 1, 8)},
        after={"hire_date": date(2024, 2, 1)},
        at=at,
    )
    row.refresh_from_db()
    assert row.before == {"hire_date": "2024-01-08"}
    assert row.created_at == at
    assert str(row) == f"UPDATE Employee {employee.employee_code} by {employee.employee_code}"
