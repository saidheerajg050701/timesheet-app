# Employee Timesheet App

A local-only Django web app for weekly timesheets, biweekly approvals and a separate payroll
database. The full specification is [docs/BUILD_GUIDE.md](docs/BUILD_GUIDE.md).

## Requirements
macOS with the tools from the guide's Part A. Check them with `bash scripts/doctor.sh`.

## First-time setup
```bash
uv sync                                    # installs Python 3.13 packages into .venv
cp .env.example .env                       # then edit .env (never commit it)
uv run python -c "import secrets; print(secrets.token_urlsafe(50))"   # paste as DJANGO_SECRET_KEY
uv run python manage.py migrate                      # main database  → db.sqlite3
uv run python manage.py migrate --database=payroll   # payroll database → payroll.sqlite3
```

## Run
```bash
uv run python manage.py runserver          # http://127.0.0.1:8000
```

## Logging in
Every page needs a login except `/login/` and `/signup/`. Sign-up only works for an ACTIVE
employee in the directory, using their company email. Five wrong passwords lock that account
for 15 minutes. There is no self-service password reset: ask an admin.

## Roles and menus
Everyone gets Dashboard, Timesheets, Requests and Profile. Team and Approvals appear for
managers (anyone with reports) and directory admins; Payroll for payroll users and admins;
Admin only for directory admins. Every page also checks permissions on the server
(`directory/services/permissions.py`). Pages from later build phases show a placeholder.

## Demo data and the employee directory
```bash
uv run python manage.py seed_demo            # demo company: ~50 employees, 12–13 weeks of history
uv run python manage.py seed_demo --large    # ~500 employees, 52 weeks (performance testing)
uv run python manage.py import_employees data/your_file.csv   # create/update employees by employee_code
```
`seed_demo` refuses to run when the database already has data. Every demo login uses the
`DEMO_PASSWORD` from `.env`. The admin at http://127.0.0.1:8000/admin/ is view-only for now.

To create an admin login for an existing directory admin employee (ACTIVE, `is_admin` on,
no account yet):
```bash
uv run python manage.py createsuperuser    # asks for the employee code, e.g. EMP-0007
```

## Test
```bash
uv run pytest -m "not e2e"                 # fast unit + integration tests
bash scripts/test_all.sh                   # ruff, migrations check, Django check, coverage, e2e
```
Tests use temporary databases and never touch `db.sqlite3` or `payroll.sqlite3`.

## Layout
- `config/`: settings (read from `.env`), URLs
- `directory/`, `timesheets/`, `audit/`, `payroll/`, `analytics/`: Django apps. Business rules live in each app's `services/` package
- `payroll/routers.py`: sends the payroll app to `payroll.sqlite3` and keeps every other app out of it
- `templates/`, `static/vendor/`: Bootstrap 5, HTMX and Chart.js, saved locally (no JS build step)
- `tests/`: pytest suite (see B.11 in the guide)
