# D-147: doctor.sh gives two answers

- **Status:** Accepted
- **Area:** Setup
- **From:** README & first-run checks (commit `e17cc7d`)
- **Recorded:** 2026-10-28

## Context

A decision in the **Setup** area, recorded during README & first-run checks. It affects these parts of the specification: A.3, A.4.

## Decision

**`doctor.sh` gives two answers.** "Ready to RUN the app" needs Git, uv, Python 3.13 via uv (as `.python-version` / `pyproject.toml`) and a free port 8000: missing ones are ❌ and the script exits with an error. "Ready to BUILD with Claude Code" (Claude Code, no `ANTHROPIC_API_KEY`, Git identity, home folder not a repository; on macOS Xcode tools, Homebrew, Antigravity) only gives ⚠️ warnings. Computer information (macOS version, chip, RAM, disk) is a warning only; macOS-only checks are skipped on Linux.

## Consequences

- **Checked by:** no catalogued test cites this decision directly.
- **Cited in code:** [`scripts/doctor.sh`](../../scripts/doctor.sh), [`tests/site/test_first_run_checks.py`](../../tests/site/test_first_run_checks.py)
