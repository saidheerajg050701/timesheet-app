"""Reports → Project hours (Change 11, D-160–D-164): the one place for the report's numbers.

The page, the Excel workbook and the CSV all read one ProjectReport, for every role, so they
always agree. Who is in it comes from the same hierarchy rules as Team (permissions.py); weeks
and pay periods from calendar.py; "employed in the range" from team.people_in_range.

Counting (D-161):
- Project hours: Project-work entries for the selected projects (all when none is selected).
- Non-project time: Meetings, Training and Other — never filtered by project.
- Total time = project hours + non-project time. Break and leave never count; leave is shown
  per person for context only.
- Only weeks whose status matches the Hours filter count (approved / + submitted / all).

Loading is a fixed number of database reads, whatever the number of people or weeks (D-164).

The package (D-173): constants.py (choices, labels, notes), filters.py (the URL filters),
scope.py (who is in it), rows.py (the rows and ProjectReport), aggregate.py (the numbers, no
database reads) and queries.py (the reads). Everything public is importable from here.
"""

from analytics.services.project_report.aggregate import build_report, by_manager, by_team
from analytics.services.project_report.constants import (
    FOOTNOTE,
    GROUPS,
    HOURS,
    MAX_WEEKS,
    NO_MANAGER,
    NO_TEAM,
    NO_TIME,
    NON_PROJECT,
    NOT_APPROVED,
    ON_LEAVE,
    ONLY_NON_PROJECT,
    OTHER_PROJECTS,
    PERIODS,
    SCOPES,
    hours,
)
from analytics.services.project_report.filters import Filters, period_range, read_filters
from analytics.services.project_report.queries import project_report
from analytics.services.project_report.rows import DetailRow, GroupRow, PersonRow, ProjectReport
from analytics.services.project_report.scope import (
    group_options,
    manager_choices,
    manages_anyone,
    report_people,
    scope_options,
)

__all__ = [
    "FOOTNOTE", "GROUPS", "HOURS", "MAX_WEEKS", "NO_MANAGER", "NO_TEAM", "NO_TIME",
    "NON_PROJECT", "NOT_APPROVED", "ON_LEAVE", "ONLY_NON_PROJECT", "OTHER_PROJECTS", "PERIODS",
    "SCOPES", "DetailRow", "Filters", "GroupRow", "PersonRow", "ProjectReport", "build_report",
    "by_manager", "by_team", "group_options", "hours", "manager_choices", "manages_anyone",
    "period_range", "project_report", "read_filters", "report_people", "scope_options",
]  # fmt: skip
