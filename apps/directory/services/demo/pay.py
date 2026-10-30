"""The seeder's pay records and project budgets (Change 12, D-172)."""

from decimal import Decimal

from apps.audit.models import AuditLog
from apps.audit.services.log import build
from apps.compensation.models import PayRecord
from apps.compensation.services.pay import labour_cost, rate_index, record_on, suggested_hourly
from apps.compensation.services.pay import snapshot as pay_snapshot
from apps.directory.models import Employee
from apps.directory.services.demo.constants import (
    BUDGET_USE,
    HOURLY_RATES,
    NO_PAY_TEAM,
    RAISE,
    SALARIES,
    SYSTEM_ACTOR,
)
from apps.projects.models import Project
from apps.timesheets.models import TimeEntry, Timesheet


class PayMixin:
    """Part of _Seeder (__init__.py); uses its attributes (self.rng, self.audit, …)."""

    def _pay(self, employees):
        """Everyone's pay from the start of the history (or their hire date), one raise, and
        one person with no pay record ("Rate missing")."""
        start = self.week_starts[0]
        no_pay = next(
            (e for e in sorted(employees.values(), key=lambda e: e.employee_code)
             if e.team and e.team.name == NO_PAY_TEAM and not e.reports.exists()),
            None,
        )  # fmt: skip
        records = []
        for employee in sorted(employees.values(), key=lambda e: e.employee_code):
            if employee == no_pay:
                continue
            effective = max(start, employee.hire_date or start)
            if employee.job_title in HOURLY_RATES:
                cents = self.rng.choice((-200, -100, 0, 50, 100, 150))
                rate = Decimal(HOURLY_RATES[employee.job_title]) + Decimal(cents) / 100
                pay = PayRecord(employee=employee, pay_type="HOURLY", hourly_rate=rate)
            else:
                base = SALARIES.get(employee.job_title, 90000)
                salary = Decimal(base + self.rng.randrange(-6, 7) * 500)
                pay = PayRecord(
                    employee=employee,
                    pay_type="SALARIED",
                    annual_salary=salary,
                    hourly_rate=suggested_hourly(salary),
                )
            pay.effective_from, pay.system_actor = effective, SYSTEM_ACTOR
            records.append(pay)
            if employee.employee_code == RAISE[0]:
                salary = (pay.annual_salary * (100 + RAISE[1]) / 100).quantize(Decimal("1"))
                records.append(
                    PayRecord(
                        employee=employee,
                        pay_type="SALARIED",
                        annual_salary=salary,
                        hourly_rate=suggested_hourly(salary),
                        effective_from=self.periods[-4],
                        system_actor=SYSTEM_ACTOR,
                    )
                )
        PayRecord.objects.bulk_create(records)
        for pay in records:
            self.audit.append(
                build(
                    AuditLog.Action.CREATE,
                    "Pay",
                    pay.employee.employee_code,
                    system_actor=SYSTEM_ACTOR,
                    after=pay_snapshot(pay),
                )
            )

    def _budgets(self):
        """Budgets on I-001 … I-007 from their approved cost so far, so the demo shows On
        track, At risk and Over budget; I-008 (closed) has none."""
        costs = {}
        pay = rate_index(list(Employee.objects.values_list("pk", flat=True)))
        entries = TimeEntry.objects.filter(
            category=TimeEntry.Category.PROJECT, timesheet__status=Timesheet.Status.APPROVED
        ).values_list("project__code", "timesheet__employee_id", "work_date", "minutes")
        for code, employee, day, minutes in entries:
            found = record_on(pay.get(employee, []), day)
            if found is not None:
                costs[code] = costs.get(code, Decimal(0)) + labour_cost(minutes, found.hourly_rate)
        for project in Project.objects.filter(code__in=BUDGET_USE):
            cost = costs.get(project.code, Decimal(0))
            budget = (cost / BUDGET_USE[project.code]).quantize(Decimal("1")) or Decimal(50000)
            Project.objects.filter(pk=project.pk).update(budget=budget)
            for row in self.audit:  # the project's CREATE row (written at the end) has it too
                if row.entity_type == "Project" and row.entity_id == project.code:
                    row.after = {**row.after, "budget": str(budget)}
