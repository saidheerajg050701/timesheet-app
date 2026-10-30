# Troubleshooting

## Running the app

| Problem | Fix |
|---|---|
| "That port is already in use" / port 8000 busy | Another copy is still running: stop it with Control + C in its Terminal. Or `lsof -i :8000`, then `kill <PID>`. Or use another port: `uv run python manage.py runserver 8001` and open http://127.0.0.1:8001 |
| "DJANGO_SECRET_KEY is still the example value" or "…is only N characters" | Make a key with `uv run python -c "import secrets; print(secrets.token_urlsafe(50))"` and paste it into `.env` as `DJANGO_SECRET_KEY`. With `DJANGO_DEBUG=False` the app won't start until you do ([D-145](../decisions/D-145-the-secret-key-can-t-stay-the.md)) |
| `PAY_PERIOD_ANCHOR` error at start | It must be a Sunday, e.g. `2026-01-04` ([D-113](../decisions/D-113-pay-periods.md)) |
| `no such table` | Run both migrations: `make migrate` (or the two `migrate` commands) |
| `ModuleNotFoundError` | Use `uv run python …` (not plain `python`), or run `uv sync` |
| `uv: command not found` | `brew install uv`, then open a new Terminal |
| Wrong Python version | `uv python install 3.13`, then `uv sync` |
| A plain "Something went wrong" page | `DJANGO_DEBUG=False` hides details on purpose ([D-96](../decisions/D-096-debug-off-for-daily-use.md)). Read the Terminal running `runserver`, or set `DJANGO_DEBUG=True` in `.env` while investigating |
| A page looks wrong right after an update | Reload it once with ⌘⇧R |
| Terminal shows `dquote>` or `quote>` | A pasted command was split. Press Control + C and copy it again |

## Logging in

| Problem | Fix |
|---|---|
| "Account locked" after wrong passwords | Wait 15 minutes, or ask HR to reset the password (Admin → the employee → Reset password); a reset also clears the lockout |
| Forgot the demo password | It is the `DEMO_PASSWORD` line in your `.env` |
| Sign-up refused | The email must be an ACTIVE employee in the directory, with the company domain and no account yet |

## Data

| Problem | Fix |
|---|---|
| `seed_demo` says the database already has data | It never overwrites. To start over, move the databases aside: [demo data → Start over](demo-data.md#start-over-with-fresh-demo-data) |
| "DEMO_PASSWORD is still the example value" | Put a password of your own (12+ characters) in `.env`, then run `seed_demo` again |
| Payroll says "out of sync", or is empty after approving | `uv run python manage.py sync_payroll` (safe to repeat) |
| Exported payroll before registers existed and see no registers | `uv run python manage.py build_registers` once ([payroll run](payroll-run.md#registers-for-older-exports)) |
| "Task not recorded" on older project work | Weeks saved before tasks existed; choose a task for that row (⋮ → Change row) when the week is saved again |
| Deadline looks an hour off | Check `COMPANY_TZ` in `.env`; the daylight-saving tests (T-15) check the rule |
| Project budget shows "Rate missing" | That person has no pay record for those days: HR adds one in Admin → the employee → Pay |

## Tests and development

| Problem | Fix |
|---|---|
| Browser tests: "browser not found" / "Executable doesn't exist" | `uv run playwright install chromium` once, or `bash scripts/test_all.sh --browser-channel chrome` |
| Git shows the wrong author | `git config --show-origin user.name`; also check your home folder isn't a Git repository ([setup](setup.md#to-change-the-app-developers)) |
| Claude Code uses API billing | Remove `ANTHROPIC_API_KEY` from `~/.zshrc`, open a new Terminal |
| `claude: command not found` | Open a new Terminal or `source ~/.zshrc` |
| "code: command not found" from Claude Code in Antigravity | Harmless if you installed the extension by hand |
| Hit the Claude usage limit | Wait for the reset, then continue the same change |
