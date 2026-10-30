# Employee Timesheet App

A web app that runs on your own computer for weekly timesheets, two-week approvals and a separate
payroll database. Employees enter their hours in a weekly grid (Sunday to Saturday, due Saturday
12:00), managers approve every two weeks, payroll finalizes one register per pay period, and HR
manages people, projects, pay and budgets. Built with Python 3.13, Django 5.2 and SQLite; no
cloud services.

## Quick start (about 10 minutes)

You need a Mac with macOS 13 or newer (Linux works too), **Git** (`git --version`; on a Mac
`xcode-select --install` if missing) and **uv** (`brew install uv`). Type each command in
Terminal and check the ✅ result. More detail: [setup](docs/runbooks/setup.md).

```bash
git clone https://github.com/saidheerajg050701/timesheet-app.git ~/Documents/timesheet-app
cd ~/Documents/timesheet-app
bash scripts/doctor.sh                # ✅ "Ready to RUN the app."
uv sync                               # ✅ "Installed … packages" (downloads Python 3.13 if needed)
cp .env.example .env
uv run python -c "import secrets; print(secrets.token_urlsafe(50))"
open -e .env                          # any text editor on Linux
```
In `.env`, **change two lines** (the example values are refused): `DJANGO_SECRET_KEY=` → the
long random text just printed; `DEMO_PASSWORD=` → a password of your own, 12+ characters. Then:
```bash
uv run python manage.py check                         # ✅ "System check identified no issues"
uv run python manage.py migrate
uv run python manage.py migrate --database=payroll    # ✅ db.sqlite3 and payroll.sqlite3 exist
uv run python manage.py seed_demo                     # ✅ "Demo company created:"
uv run python manage.py runserver                     # ✅ open http://127.0.0.1:8000
```
Log in as **`dev2@yourcompany.com`** with your `DEMO_PASSWORD`. Other demo logins:
`eng.manager@` (manager), `payroll@` (payroll), `hr@` (HR admin), all `@yourcompany.com` —
see [demo data](docs/runbooks/demo-data.md#logins). Stop the app with Control + C.

> Keep the folder out of iCloud *Desktop & Documents* syncing: it can damage the databases.
> `.env`, `db.sqlite3` and `payroll.sqlite3` are private and never committed.

## Documentation

| For | Read |
|---|---|
| **Using the app** | [Employee](docs/user-guides/employee.md) · [Manager](docs/user-guides/manager.md) · [Payroll](docs/user-guides/payroll.md) · [HR admin](docs/user-guides/hr-admin.md) |
| **Running it** | [Setup and updating](docs/runbooks/setup.md) · [Backup and restore](docs/runbooks/backup-restore.md) · [Payroll run](docs/runbooks/payroll-run.md) · [Demo data](docs/runbooks/demo-data.md) · [Troubleshooting](docs/runbooks/troubleshooting.md) |
| **Changing it** | [Contributing](CONTRIBUTING.md) · [Architecture](docs/architecture.md) · [Requirements](docs/requirements.md) · [Decisions (D-01 … D-174)](docs/decisions/README.md) · [Testing (T-01 … T-270)](docs/testing.md) |
| **History** | [Changelog](CHANGELOG.md) · [Build guide (how it was built, phase by phase)](docs/BUILD_GUIDE.md) |

Everyday commands (`make help` lists them; none deletes or reseeds data):
```bash
make run          # start the app (http://127.0.0.1:8000)
make test         # everything: lint, checks, tests with coverage, browser tests
make test-fast    # unit + integration tests
make backup       # back up both databases
make migrate      # migrate both databases
```

## Known limitations (version 1)

Runs on one computer over plain HTTP — fine for one person or a trusted office network, not the
internet. No notifications or email (HR resets passwords), no holiday calendar, no delegated
approvals, one company time zone. More in [requirements](docs/requirements.md#out-of-scope-for-version-1).

## License

All rights reserved — see [LICENSE](LICENSE).
