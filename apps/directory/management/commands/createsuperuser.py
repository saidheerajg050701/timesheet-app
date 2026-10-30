"""createsuperuser that starts from the employee directory (D-02, D-23).

Asks for an employee_code; the employee must exist, be ACTIVE, be a directory admin
(is_admin) and have no account yet. Email and flags come from the directory record.
Non-interactive: --noinput --employee-code EMP-0007 with the password in
DJANGO_SUPERUSER_PASSWORD (as in Django's own command).
"""

import getpass
import os

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.directory.services.accounts import superuser_candidate


class Command(BaseCommand):
    help = "Create an admin login account for an existing ACTIVE directory admin employee."

    def add_arguments(self, parser):
        parser.add_argument("--employee-code", help="Employee ID, e.g. EMP-0007.")
        parser.add_argument(
            "--noinput",
            "--no-input",
            action="store_false",
            dest="interactive",
            help="Do not prompt; read the password from DJANGO_SUPERUSER_PASSWORD.",
        )
        parser.add_argument("--database", default="default")

    def handle(self, *args, **options):
        database = options["database"]
        if options["interactive"]:
            employee = self._ask_employee(options["employee_code"])
            password = self._ask_password(employee)
        else:
            if not options["employee_code"]:
                raise CommandError("--employee-code is required with --noinput.")
            employee = self._check_employee(options["employee_code"])
            password = os.environ.get("DJANGO_SUPERUSER_PASSWORD")
            if not password:
                raise CommandError("Set DJANGO_SUPERUSER_PASSWORD when using --noinput.")
            self._check_password(password, employee)

        user = (
            get_user_model()
            .objects.db_manager(database)
            .create_superuser(password=password, employee=employee)
        )
        self.stdout.write(
            self.style.SUCCESS(f"Superuser created for {employee.employee_code} ({user.email}).")
        )

    def _check_employee(self, code):
        try:
            return superuser_candidate(code)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from None

    def _check_password(self, password, employee):
        user = get_user_model()(employee=employee, email=employee.email)
        try:
            validate_password(password, user)
        except ValidationError as exc:
            raise CommandError(" ".join(exc.messages)) from None

    def _ask_employee(self, code):
        while True:
            code = code or input("Employee code (e.g. EMP-0007): ")
            try:
                return superuser_candidate(code)
            except ValidationError as exc:
                self.stderr.write("Error: " + " ".join(exc.messages))
                code = None

    def _ask_password(self, employee):
        while True:
            password = getpass.getpass("Password: ")
            if password != getpass.getpass("Password (again): "):
                self.stderr.write("Error: Your passwords didn't match.")
                continue
            try:
                self._check_password(password, employee)
            except CommandError as exc:
                self.stderr.write(f"Error: {exc}")
                continue
            return password
