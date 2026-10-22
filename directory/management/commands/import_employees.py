"""import_employees <csv>: upsert the employee directory from a CSV file (B.7).

Columns: employee_code, email, first_name, last_name, job_title, team, department,
manager_code, location, hire_date, is_admin, is_payroll, status, and optionally end_date.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from directory.services.importer import EmployeeImportError, import_employees


class Command(BaseCommand):
    help = "Create or update employees from a CSV file (matched by employee_code)."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=Path)

    def handle(self, *args, **options):
        path = options["csv_path"]
        if not path.is_file():
            raise CommandError(f"File not found: {path}")
        with path.open(newline="", encoding="utf-8-sig") as handle:  # utf-8-sig: Excel files
            reader = csv.DictReader(handle)
            columns = [c.strip() for c in reader.fieldnames or []]
            reader.fieldnames = columns
            rows = list(reader)
        try:
            result = import_employees(rows, columns=columns, system_actor="import_employees")
        except EmployeeImportError as exc:
            for error in exc.errors:
                self.stderr.write(error)
            raise CommandError(f"Nothing imported: {len(exc.errors)} error(s) in {path}.") from None
        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {path}: {result.created} created, {result.updated} updated, "
                f"{result.unchanged} unchanged, {result.teams_created} new team(s)."
            )
        )
