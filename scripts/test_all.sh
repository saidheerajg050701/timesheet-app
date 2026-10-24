#!/usr/bin/env bash
# Runs every check from docs/BUILD_GUIDE.md B.11, in order, stopping at the first failure.
# Usage: bash scripts/test_all.sh [extra pytest arguments for the e2e step]
set -euo pipefail
cd "$(dirname "$0")/.."

echo "==> 1/5 Ruff"
uv run ruff check .

echo "==> 2/5 No forgotten migrations"
uv run python manage.py makemigrations --check --dry-run

echo "==> 3/5 Django system check"
uv run python manage.py check

echo "==> 4/5 Unit + integration tests with coverage"
uv run pytest -m "not e2e" --cov --cov-fail-under=80

echo "==> 5/5 End-to-end browser tests"
# Mandatory since Phase 12 (D-95): no tests collected (exit code 5) fails like any other error.
# Needs Chromium once: uv run playwright install chromium. Extra arguments go to this step,
# e.g. bash scripts/test_all.sh --browser-channel chrome (use the installed Google Chrome).
uv run pytest -m e2e "$@"

echo
echo "All checks passed."
