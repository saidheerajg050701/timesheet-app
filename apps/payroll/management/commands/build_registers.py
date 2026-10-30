"""build_registers: registers for pay periods exported before registers existed (D-137)."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.payroll.services.register import build_registers


class Command(BaseCommand):
    help = (
        "Build a finalized (or paid) register for every pay period that was already exported, "
        "from exactly what was exported. Safe to run again: periods with a register are skipped."
    )

    def handle(self, *args, **options):
        created = build_registers(at=timezone.now())
        for register in created:
            self.stdout.write(
                f"{register.period_start} – {register.period_end}: {register.get_status_display()}"
                f" ({register.export_batch}, {register.lines.count()} line(s))"
            )
        self.stdout.write(self.style.SUCCESS(f"{len(created)} register(s) built."))
