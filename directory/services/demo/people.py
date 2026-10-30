"""The seeder's directory: core and generated employees, login accounts (B.7)."""

import csv
import re
from collections import defaultdict
from datetime import timedelta

from django.conf import settings

from directory.models import Employee, User
from directory.services.demo.constants import (
    CORE_CSV,
    EARLIEST_HIRE,
    LARGE_FACTOR,
    LEADS,
    LOCATIONS,
    SIGNUP_CANDIDATES,
    STAFF,
    SYSTEM_ACTOR,
)
from directory.services.importer import REQUIRED_COLUMNS, import_employees


class PeopleMixin:
    """Part of _Seeder (__init__.py); uses its attributes (self.rng, self.audit, …)."""

    def _directory(self):
        with CORE_CSV.open(newline="", encoding="utf-8-sig") as handle:
            core_rows = list(csv.DictReader(handle))
        generated = self._generated_rows(core_rows)
        import_employees(core_rows + generated, columns=REQUIRED_COLUMNS, system_actor=SYSTEM_ACTOR)
        for code, minutes in self.part_time.items():
            Employee.objects.filter(employee_code=code).update(expected_weekly_minutes=minutes)
        return {e.employee_code: e for e in Employee.objects.select_related("team", "manager")}

    def _generated_rows(self, core_rows):
        rows = {}
        used_emails = {row["email"].strip().lower() for row in core_rows}
        next_number = len(core_rows) + 1

        def person(team, department, manager_code, title):
            nonlocal next_number
            code = f"EMP-{next_number:04d}"
            next_number += 1
            first, last = self.fake.first_name(), self.fake.last_name()
            rows[code] = {
                "employee_code": code,
                "email": self._unique_email(first, last, used_emails),
                "first_name": first,
                "last_name": last,
                "job_title": title,
                "team": team,
                "department": department,
                "manager_code": manager_code,
                "location": self.rng.choice(LOCATIONS),
                "hire_date": self._past_hire_date().isoformat(),
                "is_admin": "false",
                "is_payroll": "false",
                "status": "ACTIVE",
            }
            return code

        leads = {
            key: person(team, dept, mgr, title) for key, (title, team, dept, mgr) in LEADS.items()
        }
        team_members = defaultdict(list)
        factor = LARGE_FACTOR if self.large else 1
        for team, department, manager, titles, count in STAFF:
            for i in range(count * factor):
                code = person(
                    team, department, leads.get(manager, manager), titles[i % len(titles)]
                )
                team_members[team].append(code)

        # Recent hires, hired on the Wednesday of a period's week 1: partial first week (D-19).
        for team, period_index in (("Platform", -4), ("Support", -3), ("Sales", -2)):
            hire = self.periods[period_index] + timedelta(days=3)  # Sunday + 3 = Wednesday
            rows[team_members[team][-1]]["hire_date"] = hire.isoformat()

        self.rejected_code = team_members["Platform"][0]
        self.open_request_code = team_members["Platform"][1]
        self.edited_code = team_members["Operations"][0]
        self.part_time = {team_members["Leadership"][0]: 1200, team_members["Support"][1]: 1800}
        return list(rows.values())

    def _unique_email(self, first, last, used):
        base = f"{re.sub(r'[^a-z]', '', first.lower())}.{re.sub(r'[^a-z]', '', last.lower())}"
        email, n = f"{base}{settings.COMPANY_EMAIL_DOMAIN}", 2
        while email in used:
            email, n = f"{base}{n}{settings.COMPANY_EMAIL_DOMAIN}", n + 1
        used.add(email)
        return email

    def _past_hire_date(self):
        span = (self.week_starts[0] - timedelta(days=60) - EARLIEST_HIRE).days
        return EARLIEST_HIRE + timedelta(days=self.rng.randrange(span))

    def _accounts(self, employees):
        with_account = []
        for code in sorted(employees):
            employee = employees[code]
            if employee.status == Employee.Status.ACTIVE and code not in SIGNUP_CANDIDATES:
                User.objects.create_user(password=self.password, employee=employee)
                with_account.append(employee)
        return with_account
