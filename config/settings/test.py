"""Settings pytest uses (pyproject.toml, D-173). The same as base.py today — the test
databases are separate in-memory/test SQLite files created by pytest-django, and the tests set
the few values they depend on themselves (tests/conftest.py)."""

from .base import *  # noqa: F403
