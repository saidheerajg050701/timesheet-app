# Everyday commands (D-173). Each one only runs what it says; none deletes or reseeds data.
# Type `make help` to list them.

.PHONY: help run test test-fast e2e lint backup migrate check

help:  ## List the commands
	@grep -E '^[a-z0-9-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  make %-10s %s\n", $$1, $$2}'

run:  ## Start the app on http://127.0.0.1:8000
	uv run python manage.py runserver

test:  ## Everything: lint, checks, tests with coverage, browser tests (scripts/test_all.sh)
	bash scripts/test_all.sh

test-fast:  ## Unit + integration tests (no browser)
	uv run pytest -m "not e2e"

e2e:  ## Browser tests only
	uv run pytest -m e2e

lint:  ## Ruff
	uv run ruff check .

backup:  ## Back up both databases (backup_db)
	uv run python manage.py backup_db

migrate:  ## Apply migrations to both databases (main and payroll)
	uv run python manage.py migrate
	uv run python manage.py migrate --database=payroll

check:  ## Django system check + no forgotten migrations
	uv run python manage.py check
	uv run python manage.py makemigrations --check --dry-run
