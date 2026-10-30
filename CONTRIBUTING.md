# Contributing

How changes are made to the Employee Timesheet App. This is a private project (see
[LICENSE](LICENSE)); these rules are for the people working on it. Start with
[setup](docs/runbooks/setup.md), then read [architecture](docs/architecture.md) and
[requirements](docs/requirements.md).

## How a change is made

1. **One change at a time.** Describe the change; it gets a name (Change 13, Refactor R4, …).
2. **Plan first.** Before any code: explain how the app works today in that area, ask the open
   questions, and agree the plan. Rules that are unclear are asked about, never guessed.
3. **Record the decisions.** Every new rule is a decision with the next number (**D-175**, …):
   a new file in [docs/decisions/](docs/decisions/README.md) (copy the shape of the latest one;
   file name padded, e.g. `D-175-short-title.md`) and a row in the index. A decision that changes
   an earlier one says so, and the earlier file links to it.
4. **Build it** following the conventions below.
5. **Test it.** Every new rule gets tests in the same change, with the next catalogued ID
   (**T-271**, …): the test's docstring starts with its ID, and it gets a row in the table in
   [docs/testing.md](docs/testing.md).
6. **Update the docs**: the user guides and runbooks it affects, the
   [requirements](docs/requirements.md), [architecture](docs/architecture.md) if the structure
   changed, and a [CHANGELOG](CHANGELOG.md) entry.
7. **Run everything** — it must pass:
   ```bash
   bash scripts/test_all.sh          # or: make test
   ```
   This runs ruff, the forgotten-migrations check, Django's check, the unit and integration
   tests with coverage (at least 80 %) and the browser tests. Also start the app
   (`make run`) and click through what changed.
8. **Review and commit.** The project owner reviews the change and commits it.

## Conventions

- **Python only through uv:** `uv run …`; add packages with `uv add`, never pip.
- **Business rules** live in `apps/<app>/services/` as plain, tested functions; views stay thin.
  One rule lives in one place ([architecture → services](docs/architecture.md#the-services-pattern)).
- **Permissions** are checked on the server for every page, filter and download, through
  `apps/directory/services/permissions.py` (pay and costs: `apps/compensation/services/access.py`).
- **Audit:** every manager, admin and payroll action writes an `AuditLog` row; actions by the app
  itself use `system_actor`.
- **Payroll** models live only in the payroll database; no foreign keys across databases; payroll
  records are append-only (supersede, never edit); `publish_period` stays idempotent.
- **Time:** durations are whole minutes; work dates are `DateField`; deadlines are computed in
  `COMPANY_TZ`; weeks and pay periods come from `apps/timesheets/services/calendar.py`, never
  `weekday()` arithmetic.
- **Statuses** are `TextChoices`. **Money** is `Decimal`.
- **Front end:** Django templates, Bootstrap 5, HTMX and Chart.js from `static/vendor/`; no
  JavaScript build step. Each app keeps its templates in `apps/<app>/templates/<app>/` and its JS
  in `apps/<app>/static/<app>/`.
- **Migrations** are committed with the change that needs them. Never squash or delete migrations.
- **Style:** `uv run ruff check .` must pass.

## Never

- Never commit `.env`, `db.sqlite3`, `payroll.sqlite3` or `backups/`.
- Never delete, flush or reset the databases. To start over, move them aside
  ([demo data](docs/runbooks/demo-data.md#start-over-with-fresh-demo-data)).
- Never log, print or store a plain password.
- If you change the example `DJANGO_SECRET_KEY` or `DEMO_PASSWORD` in `.env.example`, also update
  `apps/directory/checks.py` and `seed_demo`, which refuse those values.

## Working with Claude Code

The rules Claude Code follows are in [CLAUDE.md](CLAUDE.md). It plans first, records decisions
and tests as above, runs `bash scripts/test_all.sh` until it passes, and reports what changed —
it never commits; the owner does.
