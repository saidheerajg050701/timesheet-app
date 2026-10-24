"""backup_db: timestamped copies of BOTH databases (D-72, D.3).

Uses SQLite's online backup API, so it is safe while the app is running.
"""

import sqlite3
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.utils import timezone

DATABASES = (("default", "db"), ("payroll", "payroll"))


class Command(BaseCommand):
    help = "Copy db.sqlite3 and payroll.sqlite3 into backups/ with the same timestamp."

    def add_arguments(self, parser):
        parser.add_argument("--dir", type=Path, help="Folder for the copies (default: backups/).")

    def handle(self, *args, **options):
        folder = options["dir"] or settings.BASE_DIR / "backups"
        folder.mkdir(parents=True, exist_ok=True)
        stamp = timezone.localtime().strftime("%Y%m%d-%H%M%S")
        targets = [(alias, folder / f"{label}-{stamp}.sqlite3") for alias, label in DATABASES]
        if any(path.exists() for _, path in targets):
            raise CommandError("A backup with this timestamp already exists; try again.")
        for alias, path in targets:
            source = _open_read_only(connections[alias].settings_dict["NAME"])
            copy = sqlite3.connect(path)
            try:
                source.backup(copy)  # consistent snapshot, even while the app is writing
            finally:
                copy.close()
                source.close()
            self.stdout.write(f"Backed up {alias} → {path}")
        self.stdout.write(
            self.style.SUCCESS("Both databases backed up. Restore both from the same time (D.3).")
        )


def _open_read_only(name):
    """A separate read-only connection, so a backup never shares the app's transactions."""
    name = str(name)
    if name.startswith("file:"):  # test databases are in-memory URIs
        return sqlite3.connect(name, uri=True)
    return sqlite3.connect(f"{Path(name).resolve().as_uri()}?mode=ro", uri=True)
