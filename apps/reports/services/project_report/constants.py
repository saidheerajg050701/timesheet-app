"""The report's fixed choices, labels and notes (D-160–D-162)."""

from apps.timesheets.models import TimeEntry, Timesheet

PERIODS = {
    "this": "This pay period",
    "last": "Last pay period",
    "4w": "Last 4 weeks",
    "12w": "Last 12 weeks",
    "custom": "Custom dates",
}
HOURS = {  # the Hours filter: which weeks count, by their stored status (D-161)
    "approved": ("Approved", {Timesheet.Status.APPROVED}),
    "submitted": ("Approved + Submitted", {Timesheet.Status.APPROVED, Timesheet.Status.SUBMITTED}),
    "all": ("Everything entered", None),
}
SCOPES = {"tree": "Whole tree", "direct": "Direct reports only", "manager": "One manager's group"}
GROUPS = {"team": "Team", "manager": "Manager"}
MAX_WEEKS = 53
NON_PROJECT = (TimeEntry.Category.MEETING, TimeEntry.Category.TRAINING, TimeEntry.Category.OTHER)
NO_TEAM = "No team"
NO_MANAGER = "No manager in this report"
FOOTNOTE = "Teams and managers are as they are today (moves are not tracked)."
# Why a listed person has 0.00 project hours, in this order (D-162)
NOT_APPROVED, OTHER_PROJECTS, ONLY_NON_PROJECT, ON_LEAVE, NO_TIME = (
    "Hours not approved yet",
    "Worked on other projects",
    "Only non-project time",
    "On leave",
    "No time entered",
)


def hours(minutes):
    """Minutes → hours as a number with 2 decimals (the page, the Excel and the CSV)."""
    return round(minutes / 60, 2)
