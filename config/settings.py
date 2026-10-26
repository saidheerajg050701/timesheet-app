"""Django settings for the timesheet app. Values come from .env (see .env.example)."""

from datetime import date, time, timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
    DJANGO_ALLOWED_HOSTS=(list, ["127.0.0.1", "localhost"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")  # required, no default
DEBUG = env("DJANGO_DEBUG")
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS")  # D-03

# Company settings (B.1)
COMPANY_EMAIL_DOMAIN = env("COMPANY_EMAIL_DOMAIN", default="@yourcompany.com")
COMPANY_TZ = env("COMPANY_TZ", default="America/Chicago")
# A Sunday: pay periods start on the first day of a week (D-113, checked by timesheets.E001).
PAY_PERIOD_ANCHOR = date.fromisoformat(env("PAY_PERIOD_ANCHOR", default="2026-01-04"))
# Managers approve a pay period by this many days after its last day (Saturday), at this time
# company time: Monday 12:00 by default (D-133).
APPROVAL_DEADLINE_DAYS = env.int("APPROVAL_DEADLINE_DAYS", default=2)
APPROVAL_DEADLINE_TIME = time.fromisoformat(env("APPROVAL_DEADLINE_TIME", default="12:00"))
DEMO_PASSWORD = env("DEMO_PASSWORD", default="")

INSTALLED_APPS = [
    # "directory" comes before django.contrib.auth so its createsuperuser command
    # (employee_code flow, D-02) replaces Django's built-in one.
    "directory",
    "directory.admin_site.CompanyAdminConfig",  # directory admins only (D-93)
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "axes",
    "timesheets",
    "audit",
    "payroll",
    "analytics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Login required everywhere except views marked @login_not_required (login, sign-up).
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "directory.middleware.PasswordChangeRequiredMiddleware",  # after an HR reset (D-91)
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",  # must be last
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "directory.context_processors.current_employee",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Two SQLite databases (B.6). payroll/routers.py keeps the payroll app in "payroll"
# and every other app in "default".
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    },
    "payroll": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "payroll.sqlite3",
    },
}
DATABASE_ROUTERS = ["payroll.routers.PayrollRouter"]

AUTH_USER_MODEL = "directory.User"
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",  # lockout check first (FR-1)
    "directory.backends.EmployeeBackend",  # email + password; ACTIVE employees only
]
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

# django-axes (FR-1): 5 failed logins lock the account for 15 minutes (D-28).
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(minutes=15)
AXES_LOCKOUT_PARAMETERS = ["username"]
AXES_USERNAME_CALLABLE = "directory.services.login.lockout_username"
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_TEMPLATE = "registration/locked.html"
# axes.W006 recommends adding ip_address to the lockout key; we lock the account itself (D-28).
SILENCED_SYSTEM_CHECKS = ["axes.W006"]

# Argon2 first: new and changed passwords are stored as Argon2 hashes (B.10).
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.ScryptPasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 12},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = COMPANY_TZ
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
