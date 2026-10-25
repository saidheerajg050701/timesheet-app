"""sync_payroll: re-check every approved period against the payroll database (D-65)."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from payroll.services.sync import sync_payroll_counts


class Command(BaseCommand):
    help = (
        "Publish missing payroll records, supersede stale ones and create missing pay "
        "adjustments. Safe to run any time."
    )

    def handle(self, *args, **options):
        published, superseded, adjustments = sync_payroll_counts(at=timezone.now())
        self.stdout.write(
            self.style.SUCCESS(
                f"Payroll in sync: {published} record(s) published, {superseded} superseded, "
                f"{adjustments} adjustment(s) created."
            )
        )
