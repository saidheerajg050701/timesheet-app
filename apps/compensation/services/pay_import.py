"""The admin-only Pay CSV (Change 12, D-167): export every pay record, import new ones.

Checked like the employee import (D-92): the whole file is read first; any problem is listed
with its line number and nothing is imported; otherwise the admin sees a summary before
confirming. Importing only ever ADDS pay records (history is never changed): a row identical
to an existing record is "unchanged", a row for a date that already has different pay is a
correction (the newer record wins, D-166). Each added record is audited like a pay change.
Messages never repeat an amount (D-167).
"""

import csv
import io
from dataclasses import dataclass, field
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.audit.models import AuditLog
from apps.audit.services.log import record
from apps.compensation.models import PayRecord
from apps.compensation.services.pay import build_pay, check_pay, current_pay, money, save_audit
from apps.directory.models import Employee
from apps.directory.services.importer import FIRST_DATA_LINE
from apps.payroll.services.export import safe_cell

PAY_COLUMNS = ("employee_code", "pay_type", "annual_salary", "hourly_rate", "effective_from")


class PayImportError(Exception):
    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"{len(errors)} error(s) in pay import")


@dataclass
class PayImportResult:
    added: int = 0
    corrections: int = 0
    unchanged: int = 0
    changes: list = field(default_factory=list)  # [(employee code, effective from, kind)]


def export_pay(actor):
    """Every pay record (the whole history) as CSV in the import's columns; formula-safe;
    audited as EXPORT. Admins only — the view checks can_manage_pay."""
    records = PayRecord.objects.select_related("employee").order_by(
        "employee__employee_code", "effective_from", "pk"
    )
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\r\n")
    writer.writerow(PAY_COLUMNS)
    count = 0
    for pay in records:
        writer.writerow(
            [
                safe_cell(pay.employee.employee_code),
                pay.pay_type,
                pay.annual_salary if pay.annual_salary is not None else "",
                pay.hourly_rate,
                pay.effective_from.isoformat(),
            ]
        )
        count += 1
    record(AuditLog.Action.EXPORT, "Pay", "all", actor=actor, after={"rows": count})
    return out.getvalue()


def _same(pay, existing):
    return (pay.pay_type, pay.annual_salary, pay.hourly_rate) == (
        existing.pay_type,
        existing.annual_salary,
        existing.hourly_rate,
    )


def import_pay(rows, *, columns, actor, dry_run=False):
    """Check every row, then add the new pay records (all or nothing). `dry_run` gives the
    preview: everything is done, audit rows included, and rolled back. Raises PayImportError."""
    missing = [c for c in PAY_COLUMNS if c not in columns]
    if missing:
        raise PayImportError([f"Missing column(s): {', '.join(missing)}"])
    employees = {e.employee_code: e for e in Employee.objects.all()}
    errors, parsed, seen = [], [], {}
    for index, raw in enumerate(rows):
        line = index + FIRST_DATA_LINE
        code = (raw.get("employee_code") or "").strip().upper()
        employee = employees.get(code)
        problems = []
        if employee is None:
            problems.append(f"unknown employee_code {code or '(empty)'}")
        pay_type = (raw.get("pay_type") or "").strip().upper()
        amounts = {}
        for name in ("annual_salary", "hourly_rate"):
            try:
                amounts[name] = money(raw.get(name))
            except ValueError:
                problems.append(f"{name} is not an amount")
                amounts[name] = None
        try:
            effective = date.fromisoformat((raw.get("effective_from") or "").strip())
        except ValueError:
            problems.append("effective_from must look like 2026-10-01")
            effective = None
        if employee is not None and not problems:
            for messages in check_pay(
                employee, pay_type, amounts["annual_salary"], amounts["hourly_rate"], effective
            ).values():
                problems.extend(m[:1].lower() + m[1:].rstrip(".") for m in messages)
        if not problems and (code, effective) in seen:
            problems.append(
                f"{code} already has a row for {effective} on line {seen[code, effective]}"
            )
        if problems:
            errors.extend(f"Line {line}: {p}." for p in problems)
            continue
        seen[code, effective] = line
        parsed.append(
            build_pay(
                employee, pay_type, amounts["annual_salary"], amounts["hourly_rate"], effective
            )
        )
    if errors:
        raise PayImportError(errors)
    result = PayImportResult()
    today = timezone.localdate()
    with transaction.atomic():
        for pay in parsed:
            same_day = list(
                pay.employee.pay_records.filter(effective_from=pay.effective_from).order_by("pk")
            )
            if same_day and _same(pay, same_day[-1]):
                result.unchanged += 1
                continue
            kind = "correction" if same_day else "added"
            before = current_pay(pay.employee, today)
            pay.created_by = actor
            pay.save()
            save_audit(actor, pay.employee, before, pay)
            result.added += 1
            result.corrections += kind == "correction"
            result.changes.append((pay.employee.employee_code, pay.effective_from, kind))
        if dry_run:
            transaction.set_rollback(True)
    return result
