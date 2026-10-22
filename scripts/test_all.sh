#!/usr/bin/env bash
# Runs every check from docs/BUILD_GUIDE.md B.11, in order, stopping at the first failure.
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
# D-01: until Phase 12, "no tests collected" (pytest exit code 5) counts as success for this
# step only. Phase 12 removes this rule and makes e2e mandatory.
status=0
uv run pytest -m e2e || status=$?
if [ "$status" -eq 5 ]; then
  echo "e2e: skipped - no e2e tests yet"
elif [ "$status" -ne 0 ]; then
  exit "$status"
fi

echo
echo "All checks passed."
