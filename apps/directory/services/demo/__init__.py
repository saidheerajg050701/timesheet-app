"""The demo company built by seed_demo (B.7).

The same seed date always gives the same data: random choices come from a fixed seed and all
dates are relative to `now`. History covers the 6 completed pay periods before the current one
(26 with --large), plus week 1 of the current period when today is in its week 2 (D-27).

The package (D-173): constants.py (the tables), people.py, projects.py, history.py, pay.py,
approvals.py and writing.py (the parts of the seeder), payroll.py (the payroll database),
calendar.py (holidays) and records.py (small shared records). seed_demo, DemoDataExists and
us_holidays are importable from here.
"""

import logging
import random
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db import transaction
from faker import Faker

from apps.audit.models import AuditLog
from apps.audit.services.log import build, bulk_record
from apps.directory.models import Employee
from apps.directory.services.demo.approvals import ApprovalsMixin
from apps.directory.services.demo.calendar import us_holidays
from apps.directory.services.demo.constants import LARGE_PERIODS, NORMAL_PERIODS, SEED, SYSTEM_ACTOR
from apps.directory.services.demo.history import HistoryMixin
from apps.directory.services.demo.pay import PayMixin
from apps.directory.services.demo.payroll import approve_the_rest, seed_payroll
from apps.directory.services.demo.people import PeopleMixin
from apps.directory.services.demo.projects import ProjectsMixin
from apps.directory.services.demo.writing import WritingMixin
from apps.projects.models import Project
from apps.timesheets.models import Timesheet
from apps.timesheets.services.calendar import pay_period_for, week_start_for

logger = logging.getLogger(__name__)


class DemoDataExists(Exception):
    pass


def seed_demo(*, now, password, large=False):
    """Build the demo company. Refuses (DemoDataExists) if the database already has data."""
    if Employee.objects.exists() or Project.objects.exists() or Timesheet.objects.exists():
        raise DemoDataExists(
            "The database already has data, so seed_demo did nothing. "
            "To start over, see docs/BUILD_GUIDE.md D.3."
        )
    with transaction.atomic():
        summary = _Seeder(now, password, large).run()
    # The payroll database is a separate file: it is filled only after the main seed has
    # committed (D-65, D-73). If this part fails, sync_payroll completes it later.
    try:
        summary["payroll"] = seed_payroll(now)
    except Exception:
        logger.exception("seed_demo: payroll part failed")
        summary["payroll"] = "not written — run `uv run python manage.py sync_payroll`"
    return summary


class _Seeder(PeopleMixin, ProjectsMixin, HistoryMixin, PayMixin, ApprovalsMixin, WritingMixin):
    """Builds the demo company; each topic is a mixin in its own file (D-173)."""

    def __init__(self, now, password, large):
        self.tz = ZoneInfo(settings.COMPANY_TZ)
        self.now = now.astimezone(self.tz)
        self.password = password
        self.large = large
        self.rng = random.Random(SEED)
        self.fake = Faker("en_US")
        self.fake.seed_instance(SEED)
        self.audit = []

        today = self.now.date()
        current_period, _, current_week2 = pay_period_for(today, settings.PAY_PERIOD_ANCHOR)
        n_periods = LARGE_PERIODS if large else NORMAL_PERIODS
        self.periods = [
            current_period - timedelta(weeks=2 * (n_periods - i)) for i in range(n_periods)
        ]
        self.week_starts = [p + timedelta(weeks=k) for p in self.periods for k in (0, 1)]
        self.current_period = current_period
        if week_start_for(today) == current_week2:
            self.week_starts.append(current_period)
        self.last_completed = self.periods[-1]
        years = {self.week_starts[0].year, today.year}
        self.holidays = {d: name for y in sorted(years) for d, name in us_holidays(y).items()}

    def run(self):
        employees = self._directory()
        with_account = self._accounts(employees)
        projects = self._projects()
        weeks = self._history(with_account, projects)
        approvals = self._approvals(employees, weeks)
        self._write(employees, weeks, approvals)
        self._pay(employees)
        self._budgets()
        summary = self._summary()
        bulk_record(
            self.audit
            + [
                build(
                    AuditLog.Action.CREATE,
                    "DemoData",
                    "seed_demo",
                    system_actor=SYSTEM_ACTOR,
                    after=summary,
                )
            ]
        )
        return summary


__all__ = ["DemoDataExists", "approve_the_rest", "seed_demo", "seed_payroll", "us_holidays"]
