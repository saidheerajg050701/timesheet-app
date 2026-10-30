"""sync_payroll: re-check every approved period against the payroll database (D-65)."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.payroll.services.sync import sync_payroll_report


class Command(BaseCommand):
    help = (
        "Publish missing payroll records, supersede stale ones, create missing pay "
        "adjustments and registers. Safe to run any time."
    )

    def handle(self, *args, **options):
        result = sync_payroll_report(at=timezone.now())
        self.stdout.write(
            self.style.SUCCESS(
                f"Payroll in sync: {result.published} record(s) published, "
                f"{result.superseded} superseded, {result.adjustments} adjustment(s) created, "
                f"{result.registers} register(s) built."
            )
        )
