"""Employee pay (Change 12, D-166, D-167): the one place for pay rules.

Pay is history. Each PayRecord says how someone is paid from a date on; a pay change — or a
correction with the same date — is a new record, never an edit, so the cost of earlier work
stays what it was. Money is always Decimal (exact cents), never float. Only admins see or
change pay in Admin; project costs use the hourly rate only (analytics/services/project_costs).
"""

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction

from audit.models import AuditLog
from audit.services.log import record
from directory.models import PayRecord

CENT = Decimal("0.01")
YEAR_HOURS = Decimal("2080")  # 40 h × 52 weeks
MAX_MONEY = Decimal("9999999.99")


def money(value):
    """Text or number → Decimal rounded half-up to cents; None for blank; ValueError if not
    a number. Commas and a leading $ are allowed ("$85,000")."""
    text = str(value if value is not None else "").strip().replace(",", "").removeprefix("$")
    if not text:
        return None
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError(f"{value!r} is not an amount") from None
    if not amount.is_finite():
        raise ValueError(f"{value!r} is not an amount")
    return amount.quantize(CENT, rounding=ROUND_HALF_UP)


def suggested_hourly(annual_salary):
    """The hourly rate a salary suggests: salary ÷ 2,080, to the cent (D-166)."""
    return (Decimal(annual_salary) / YEAR_HOURS).quantize(CENT, rounding=ROUND_HALF_UP)


def labour_cost(minutes, rate):
    """The cost of `minutes` of work at an hourly `rate`: hours × rate, rounded half-up to
    cents — one time entry (D-169). Project costs and the demo budgets both use this."""
    return (Decimal(minutes) * rate / Decimal(60)).quantize(CENT, rounding=ROUND_HALF_UP)


def rate_index(employee_ids):
    """{employee id: [PayRecord, …] oldest first} — one query for any number of people."""
    index = {}
    records = PayRecord.objects.filter(employee_id__in=employee_ids).order_by(
        "employee_id", "effective_from", "pk"
    )
    for pay in records:
        index.setdefault(pay.employee_id, []).append(pay)
    return index


def record_on(records, day):
    """The record in force on `day`: the latest effective_from up to that day, and for the
    same date the newest (a correction). None when no record has started yet."""
    found = None
    for pay in records:  # oldest first: a later one in force replaces an earlier one
        if pay.effective_from <= day:
            found = pay
        else:
            break
    return found


def current_pay(employee, today):
    return record_on(list(employee.pay_records.order_by("effective_from", "pk")), today)


def history(employee):
    """[(record, replaced)] newest first; `replaced` marks a record a same-date correction
    replaced."""
    records = list(
        employee.pay_records.select_related("created_by").order_by("effective_from", "pk")
    )
    rows = []
    for i, pay in enumerate(records):
        later = records[i + 1] if i + 1 < len(records) else None
        rows.append((pay, later is not None and later.effective_from == pay.effective_from))
    return list(reversed(rows))


def snapshot(pay):
    """The audit view of a record — text, so the audit row stores exact cents."""
    if pay is None:
        return None
    return {
        "pay_type": pay.pay_type,
        "annual_salary": str(pay.annual_salary) if pay.annual_salary is not None else None,
        "hourly_rate": str(pay.hourly_rate),
        "effective_from": pay.effective_from.isoformat(),
    }


def check_pay(employee, pay_type, annual_salary, hourly_rate, effective_from):
    """{field: [messages]} for a new pay record (empty when fine). Amounts are Decimals (or
    None), the date a date (or None). Never repeats an amount in a message (D-167)."""
    errors = {}

    def problem(field, message):
        errors.setdefault(field, []).append(message)

    if pay_type not in PayRecord.PayType.values:
        problem("pay_type", "Choose Salaried or Hourly.")
    if pay_type == PayRecord.PayType.SALARIED:
        if annual_salary is None or annual_salary <= 0:
            problem("annual_salary", "A salaried employee needs an annual salary above 0.")
    elif pay_type == PayRecord.PayType.HOURLY and annual_salary is not None:
        problem("annual_salary", "Leave the annual salary empty for an hourly employee.")
    if hourly_rate is not None and hourly_rate <= 0:
        problem("hourly_rate", "The hourly rate must be above 0.")
    if pay_type == PayRecord.PayType.HOURLY and hourly_rate is None:
        problem("hourly_rate", "An hourly employee needs an hourly rate.")
    for field, amount in (("annual_salary", annual_salary), ("hourly_rate", hourly_rate)):
        if amount is not None and amount > MAX_MONEY:
            problem(field, "That amount is too large.")
    if effective_from is None:
        problem("effective_from", "Choose the date this pay starts.")
    elif employee.hire_date and effective_from < employee.hire_date:
        problem("effective_from", f"Pay can't start before the hire date ({employee.hire_date}).")
    return errors


def build_pay(employee, pay_type, annual_salary, hourly_rate, effective_from):
    """An unsaved PayRecord; a salaried record without a rate gets the suggested one."""
    cents = [None if a is None else Decimal(a).quantize(CENT, rounding=ROUND_HALF_UP)
             for a in (annual_salary, hourly_rate)]  # fmt: skip
    annual_salary, hourly_rate = cents  # always exact cents, however it was typed
    if pay_type == PayRecord.PayType.SALARIED and hourly_rate is None and annual_salary:
        hourly_rate = suggested_hourly(annual_salary)
    return PayRecord(
        employee=employee,
        pay_type=pay_type,
        annual_salary=annual_salary if pay_type == PayRecord.PayType.SALARIED else None,
        hourly_rate=hourly_rate,
        effective_from=effective_from,
    )


def add_pay(actor, employee, pay_type, annual_salary, hourly_rate, effective_from, *, today):
    """Save a pay change with its audit row (before = pay in force until now) in one
    transaction. Raises ValueError with the messages when check_pay finds problems."""
    errors = check_pay(employee, pay_type, annual_salary, hourly_rate, effective_from)
    if errors:
        raise ValueError(" ".join(m for messages in errors.values() for m in messages))
    pay = build_pay(employee, pay_type, annual_salary, hourly_rate, effective_from)
    pay.created_by = actor
    with transaction.atomic():
        before = current_pay(employee, today)
        pay.save()
        save_audit(actor, employee, before, pay)
    return pay


def save_audit(actor, employee, before, pay, system_actor=""):
    after = {
        **snapshot(pay),
        "correction": employee.pay_records.filter(effective_from=pay.effective_from)
        .exclude(pk=pay.pk)
        .exists(),
    }
    return record(
        AuditLog.Action.CREATE,
        "Pay",
        employee.employee_code,
        actor=actor,
        system_actor=system_actor,
        before=snapshot(before),
        after=after,
    )
