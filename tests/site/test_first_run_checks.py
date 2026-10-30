"""First-run safety (D-145, D-146): example values from .env.example are refused clearly."""

import re
import secrets
import subprocess
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.directory.checks import EXAMPLE_SECRET_KEY, secret_key_is_not_the_example
from apps.directory.management.commands.seed_demo import EXAMPLE_DEMO_PASSWORD
from apps.directory.models import Employee

ROOT = Path(settings.BASE_DIR)


def example_value(name):
    """The value .env.example gives `name` (the example file — never the real .env)."""
    text = (ROOT / ".env.example").read_text()
    return re.search(rf"^{name}=(.*)$", text, re.M)[1]


def test_secret_key_must_not_be_the_example(settings):
    """T-225: the example or a short DJANGO_SECRET_KEY gives a warning while developing and an
    error for daily use, with the way to generate one; a real key passes (D-145)."""
    assert EXAMPLE_SECRET_KEY == example_value("DJANGO_SECRET_KEY")
    settings.SECRET_KEY, settings.DEBUG = EXAMPLE_SECRET_KEY, True
    (warning,) = secret_key_is_not_the_example(None)
    assert warning.id == "directory.W001" and warning.level == 30  # WARNING
    assert warning.msg == "DJANGO_SECRET_KEY is still the example value from .env.example."
    assert "secrets.token_urlsafe(50)" in warning.hint
    settings.DEBUG = False
    (error,) = secret_key_is_not_the_example(None)
    assert error.id == "directory.E001" and error.level == 40  # ERROR: stops the app
    short = "x" * 49
    settings.SECRET_KEY = short
    (error,) = secret_key_is_not_the_example(None)
    assert error.msg == "DJANGO_SECRET_KEY is only 49 characters (use 50 or more)."
    assert short not in error.msg + error.hint  # the key itself is never shown
    settings.SECRET_KEY = secrets.token_urlsafe(50)
    assert secret_key_is_not_the_example(None) == []


@pytest.mark.django_db
def test_seed_refuses_the_example_demo_password(settings):
    """T-226: seed_demo refuses the example DEMO_PASSWORD with a clear message, before writing
    anything (D-146)."""
    assert EXAMPLE_DEMO_PASSWORD == example_value("DEMO_PASSWORD")
    settings.DEMO_PASSWORD = EXAMPLE_DEMO_PASSWORD
    with pytest.raises(CommandError, match="still the example value from .env.example"):
        call_command("seed_demo", stdout=StringIO())
    assert not Employee.objects.exists()


def test_doctor_script_is_valid_bash():
    """Helper check: scripts/doctor.sh parses (bash -n) and has its two result lines (D-147)."""
    script = ROOT / "scripts" / "doctor.sh"
    subprocess.run(["bash", "-n", str(script)], check=True)
    text = script.read_text()
    assert "Ready to RUN the app" in text and "Ready to BUILD with Claude Code" in text
