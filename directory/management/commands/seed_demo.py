"""seed_demo [--large]: build the demo company described in docs/BUILD_GUIDE.md B.7."""

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from directory.services.demo import DemoDataExists, seed_demo

EXAMPLE_DEMO_PASSWORD = "choose-a-strong-demo-password"  # the value in .env.example (D-146)


class Command(BaseCommand):
    help = "Build the demo company (refuses if the database already has data)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--large",
            action="store_true",
            help="~500 employees and 52 weeks (performance testing).",
        )

    def handle(self, *args, **options):
        password = settings.DEMO_PASSWORD
        if not password:
            raise CommandError("Set DEMO_PASSWORD in .env first.")
        if password == EXAMPLE_DEMO_PASSWORD:
            raise CommandError(
                "DEMO_PASSWORD is still the example value from .env.example — choose your own "
                "password (12+ characters) in .env."
            )
        try:
            validate_password(password)
        except ValidationError as exc:  # messages never contain the password itself
            raise CommandError("DEMO_PASSWORD is not allowed: " + " ".join(exc.messages)) from None
        try:
            summary = seed_demo(now=timezone.now(), password=password, large=options["large"])
        except DemoDataExists as exc:
            raise CommandError(str(exc)) from None
        self.stdout.write(self.style.SUCCESS("Demo company created:"))
        for key, value in summary.items():
            self.stdout.write(f"  {key.replace('_', ' ')}: {value}")
        self.stdout.write("Log in with any demo email and the DEMO_PASSWORD from .env.")
