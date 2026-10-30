"""time_team_page: how long /team/ takes for one person, and how many queries (D-86).

Read-only: the page is rendered in memory, with no session and no database writes.
"""

import time

from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext

from apps.analytics.views.team import team
from apps.directory.models import User


class Command(BaseCommand):
    help = "Render /team/ for a user (read-only) and print the time and query count."

    def add_arguments(self, parser):
        parser.add_argument("email", help="Login email of a manager or admin.")
        parser.add_argument("--weeks", default="12", help="4, 12 or 26 (default 12).")
        parser.add_argument("--direct", action="store_true", help="Direct reports only.")
        parser.add_argument("--runs", type=int, default=3, help="Renders to time (default 3).")

    def handle(self, *args, **options):
        user = User.objects.select_related("employee").filter(email=options["email"]).first()
        if user is None:
            raise CommandError(f"No login account for {options['email']}.")
        params = {"weeks": options["weeks"], "scope": "direct" if options["direct"] else "tree"}
        timings = []
        for _ in range(max(options["runs"], 1)):
            request = RequestFactory().get("/team/", params)
            request.user = user
            with CaptureQueriesContext(connections["default"]) as queries:
                start = time.perf_counter()
                response = team(request)
                timings.append(time.perf_counter() - start)
            if response.status_code != 200:
                raise CommandError(f"/team/ answered {response.status_code} for this user.")
        writes = [q for q in queries if q["sql"].split()[0] in ("INSERT", "UPDATE", "DELETE")]
        people = response.content.decode().count("<tr data-employee=")
        self.stdout.write(
            f"/team/ for {options['email']} ({params['scope']}, {params['weeks']} weeks): "
            f"{people} people, best {min(timings):.3f} s, worst {max(timings):.3f} s, "
            f"{len(queries)} queries, {len(writes)} writes"
        )
