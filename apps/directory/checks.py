"""System check: the secret key must not be the example from .env.example (D-145).

runserver, migrate, seed_demo and every other management command run the checks first, so a
copied-but-unchanged .env is caught before anything starts. The key itself is never printed.
"""

from django.conf import settings
from django.core.checks import Error, Warning, register

EXAMPLE_SECRET_KEY = "change-me-to-a-long-random-string"  # the value in .env.example
MIN_SECRET_KEY_LENGTH = 50  # as Django's own deploy check (security.W009)
HINT = (
    'Generate a secret key: uv run python -c "import secrets; print(secrets.token_urlsafe(50))"'
    " and paste it into .env as DJANGO_SECRET_KEY."
)


def secret_key_problem(key):
    """Why `key` isn't a real secret key, or None."""
    if key == EXAMPLE_SECRET_KEY:
        return "DJANGO_SECRET_KEY is still the example value from .env.example."
    if len(key) < MIN_SECRET_KEY_LENGTH:
        return (
            f"DJANGO_SECRET_KEY is only {len(key)} characters "
            f"(use {MIN_SECRET_KEY_LENGTH} or more)."
        )
    return None


@register()
def secret_key_is_not_the_example(app_configs, **kwargs):
    """A warning while developing (DEBUG on); an error for daily use (DEBUG off), which stops
    runserver and the other commands."""
    problem = secret_key_problem(settings.SECRET_KEY)
    if problem is None:
        return []
    if settings.DEBUG:
        return [Warning(problem, hint=HINT, id="directory.W001")]
    return [Error(problem, hint=HINT, id="directory.E001")]
