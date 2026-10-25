"""System check: pay periods must start on a Sunday (D-113).

runserver, migrate, seed_demo and every other management command run the checks first, so
a wrong PAY_PERIOD_ANCHOR in .env stops the app with a clear message instead of silently
building pay periods that don't line up with the weeks.
"""

from django.conf import settings
from django.core.checks import Error, register

from timesheets.services.calendar import anchor_problem


@register()
def pay_period_anchor_is_a_sunday(app_configs, **kwargs):
    problem = anchor_problem(settings.PAY_PERIOD_ANCHOR)
    if problem is None:
        return []
    return [
        Error(
            problem,
            hint="Change PAY_PERIOD_ANCHOR in .env, e.g. PAY_PERIOD_ANCHOR=2026-01-04.",
            id="timesheets.E001",
        )
    ]
