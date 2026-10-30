"""A skeleton for a future server (D-173). NOT used yet: nothing points at it, and it needs
`uv add "psycopg[binary]"` before PostgreSQL works. To use it later set
DJANGO_SETTINGS_MODULE=config.settings.production plus, in the environment:
DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, DATABASE_URL and PAYROLL_DATABASE_URL
(e.g. postgres://user:password@host:5432/timesheets)."""

from .base import *  # noqa: F403
from .base import env

DEBUG = False

# Two PostgreSQL databases, as the two SQLite files today (payroll/routers.py, B.6).
DATABASES = {
    "default": env.db("DATABASE_URL"),
    "payroll": env.db("PAYROLL_DATABASE_URL"),
}

# HTTPS only (manage.py check --deploy, D-96)
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Log to standard output, where a hosting service collects it. Never log pay (D-167).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
