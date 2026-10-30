"""The demo company's fixed tables: people, teams, projects, tasks, pay, reasons (B.7,
D-154, D-172)."""

from datetime import date
from decimal import Decimal

from django.conf import settings

from apps.timesheets.models import TimeEntry

SYSTEM_ACTOR = "seed_demo"
SEED = 2026
CORE_CSV = settings.BASE_DIR / "data" / "employees_core.csv"

CEO, ENG_DIRECTOR, ENG_MANAGER = "EMP-0001", "EMP-0002", "EMP-0003"
DEV1, DEV2, HR, OPS_MANAGER, FINANCE_MANAGER = (
    "EMP-0004",
    "EMP-0005",
    "EMP-0007",
    "EMP-0008",
    "EMP-0012",
)
SIGNUP_CANDIDATES = {"EMP-0006", "EMP-0009", "EMP-0010"}  # qa1, ops1, ops2: no account (B.7)
PAYROLL_CLERK = "EMP-0011"  # payroll@: exports and pays batches in the demo history

NORMAL_PERIODS, LARGE_PERIODS = 6, 26
LARGE_FACTOR = 14  # staff per team multiplier for --large (~500 employees)
LATE_RATE, MISSED_RATE = 0.03, 0.02
EARLIEST_HIRE = date(2018, 1, 8)

PROJECTS = (  # (name, active), coded I-001 … I-008 in this order by assign_code (D-155)
    ("Customer Portal", True),
    ("Mobile App", True),
    ("Data Warehouse", True),
    ("Cloud Migration", True),
    ("Service Desk Upgrade", True),
    ("CRM Rollout", True),
    ("Internal Operations", True),
    ("Legacy Billing (closed)", False),  # inactive: never used in entries (D-18)
)
# Change 10 (D-154): the tasks each project allows, and the tasks each team usually books to.
PROJECT_TASKS = {
    "I-001": ("PLN", "DES", "DEV", "TST", "REL", "SUP", "DOC", "MTG"),
    "I-002": ("PLN", "DES", "DEV", "TST", "REL", "MTG"),
    "I-003": ("PLN", "DEV", "TST", "DOC", "MTG"),
    "I-004": ("PLN", "DEV", "REL", "SEC", "DOC", "MTG"),
    "I-005": ("SUP", "DOC", "TST", "MTG"),
    "I-006": ("PLN", "DOC", "MTG", "SUP"),
    "I-007": ("PLN", "DOC", "MTG", "SEC"),
    "I-008": ("DEV", "SUP"),
}
TEAM_TASKS = {
    "Leadership": ("PLN", "MTG"),
    "Engineering": ("DEV", "DES", "PLN", "MTG"),
    "Platform": ("DEV", "TST", "REL", "MTG"),
    "Data": ("DEV", "PLN"),
    "People": ("DOC", "MTG", "PLN"),
    "Operations": ("SUP", "DOC", "MTG"),
    "Support": ("SUP", "DOC"),
    "Payroll": ("DOC", "MTG", "PLN"),
    "Sales": ("PLN", "MTG", "DOC"),
}
TEAM_PROJECTS = {
    "Leadership": ("I-007", "I-004"),
    "Engineering": ("I-001", "I-004"),
    "Platform": ("I-001", "I-002"),
    "Data": ("I-003", "I-004"),
    "People": ("I-007",),
    "Operations": ("I-005", "I-007"),
    "Support": ("I-005",),
    "Payroll": ("I-007",),
    "Sales": ("I-006",),
}

# Generated team leads: key → (job title, team, department, manager code)
LEADS = {
    "sales": ("Sales Manager", "Sales", "Sales", CEO),
    "data": ("Data Engineering Lead", "Data", "Technology", ENG_DIRECTOR),
    "support": ("Support Lead", "Support", "Ops", OPS_MANAGER),
}
# Generated staff: (team, department, manager code or lead key, job titles, count)
STAFF = (
    ("Platform", "Technology", ENG_MANAGER, ("Software Engineer", "QA Engineer"), 8),
    ("Engineering", "Technology", ENG_DIRECTOR, ("Solutions Architect", "Program Manager"), 2),
    ("Data", "Technology", "data", ("Data Engineer", "Data Analyst"), 5),
    ("Operations", "Ops", OPS_MANAGER, ("Operations Analyst",), 3),
    ("Support", "Ops", "support", ("Support Specialist",), 5),
    ("People", "HR", HR, ("HR Generalist", "Recruiter"), 2),
    ("Payroll", "Finance", FINANCE_MANAGER, ("Accountant",), 2),
    ("Sales", "Sales", "sales", ("Account Executive",), 6),
    ("Leadership", "Executive", CEO, ("Executive Assistant",), 1),
)
LOCATIONS = ("Dallas", "Frisco", "Remote", "Austin")
# Change 12 (D-172): realistic pay. Salaried: annual salary by job title (± a little), hourly
# rate = salary ÷ 2,080. Hourly: these titles, at an hourly rate.
SALARIES = {
    "CEO": 240000, "Engineering Director": 185000, "Engineering Manager": 155000,
    "Finance Manager": 135000, "HR Manager": 120000, "Operations Manager": 112000,
    "Payroll Specialist": 68000, "QA Engineer": 98000, "Software Engineer": 125000,
    "Sales Manager": 130000, "Data Engineering Lead": 160000, "Support Lead": 85000,
    "Solutions Architect": 165000, "Program Manager": 135000, "Data Engineer": 132000,
    "Data Analyst": 98000, "HR Generalist": 72000, "Recruiter": 70000, "Accountant": 78000,
    "Account Executive": 90000,
}  # fmt: skip
HOURLY_RATES = {"Operations Analyst": 30, "Support Specialist": 26, "Executive Assistant": 32}
RAISE = (DEV1, 6)  # DEV1 gets a 6 % raise four periods before the end of the history
NO_PAY_TEAM = "Data"  # its first staff member gets no pay record: "Rate missing"
BUDGET_USE = {  # project code → share of its budget already used: statuses for the demo
    "I-001": Decimal("0.62"), "I-002": Decimal("1.15"), "I-003": Decimal("0.90"),
    "I-004": Decimal("0.55"), "I-005": Decimal("0.48"), "I-006": Decimal("0.70"),
    "I-007": Decimal("0.40"),
}  # fmt: skip
REJECT_COMMENT = "Please split Wednesday's hours between Customer Portal and Mobile App."
REASONS = {  # the demo gives every row a reason (optional since D-128)
    TimeEntry.Category.PROJECT: (
        "Feature development",
        "Code review",
        "Bug fixes",
        "Customer follow-up",
        "Planning and estimates",
        "Testing",
    ),
    TimeEntry.Category.MEETING: ("Team stand-up and planning", "Client meeting", "One-to-one"),
    TimeEntry.Category.TRAINING: ("Security awareness course", "Internal workshop"),
    TimeEntry.Category.OTHER: ("Admin and email", "Recruiting interview"),
    TimeEntry.Category.BREAK: ("Lunch break",),
    TimeEntry.Category.PTO: ("Vacation", "Personal day"),
    TimeEntry.Category.SICK: ("Sick day", "Doctor's appointment"),
}
WEEKEND_REASON = "Release support (weekend)"
