"""time_project_report: how long Reports → Project hours takes for one person, and how many
database reads (D-164). Read-only: the page is rendered in memory, with no session and no
database writes (downloads are not timed, so no EXPORT audit row is written)."""

import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from apps.directory.models import User
from apps.reports.services.project_report import HOURS, PERIODS
from apps.reports.views import project_hours


class Command(BaseCommand):
    help = "Render /reports/project-hours/ for a user (read-only) and print time and queries."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Login email of the person viewing the report.")
        parser.add_argument("--period", default="last", choices=list(PERIODS), help="Default last.")
        parser.add_argument("--from", dest="start", default="", help="Custom period: first day.")
        parser.add_argument("--to", dest="end", default="", help="Custom period: last day.")
        parser.add_argument("--hours", default="all", choices=list(HOURS), help="Default all.")
        parser.add_argument("--runs", type=int, default=3, help="Renders to time (default 3).")

    def handle(self, *args, **options):
        user = User.objects.select_related("employee").filter(email=options["email"]).first()
        if user is None:
            raise CommandError(f"No login account for {options['email']}.")
        params = {"period": options["period"], "hours": options["hours"]}
        if options["period"] == "custom":
            params.update({"from": options["start"], "to": options["end"]})
        timings = []
        for _ in range(max(options["runs"], 1)):
            request = RequestFactory().get("/reports/project-hours/", params)
            request.user = user
            with CaptureQueriesContext(connections["default"]) as queries:
                start = time.perf_counter()
                response = project_hours(request)
                timings.append(time.perf_counter() - start)
            if response.status_code != 200:
                raise CommandError(f"The report answered {response.status_code} for this user.")
        writes = [q for q in queries if q["sql"].split()[0] in ("INSERT", "UPDATE", "DELETE")]
        people = response.content.decode().count("<tr data-employee=") or 1  # own report: 1
        self.stdout.write(
            f"/reports/project-hours/ for {options['email']} ({params['period']}, "
            f"{params['hours']} hours): {people} people, best {min(timings):.3f} s, "
            f"worst {max(timings):.3f} s, {len(queries)} queries, {len(writes)} writes"
        )
