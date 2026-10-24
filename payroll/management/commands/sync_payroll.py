"""sync_payroll: re-check every approved period against the payroll database (D-65)."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from payroll.services.sync import sync_payroll


class Command(BaseCommand):
    help = "Publish missing payroll records and supersede stale ones. Safe to run any time."

    def handle(self, *args, **options):
        published, superseded = sync_payroll(at=timezone.now())
        self.stdout.write(
            self.style.SUCCESS(
                f"Payroll in sync: {published} record(s) published, {superseded} superseded."
            )
        )
