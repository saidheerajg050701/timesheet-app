#!/usr/bin/env bash
# Timesheet app — environment check (macOS; Linux works too). See docs/BUILD_GUIDE.md A.4.
#
# Two answers (D-147):
#   "Ready to RUN the app"            needs only Git, uv, Python 3.13 (via uv) and a free port 8000.
#                                     Anything missing here is ❌ and the script exits with 1.
#   "Ready to BUILD with Claude Code" Claude Code, Antigravity, Git identity, Xcode tools, …
#                                     Only needed to change the app: missing items are ⚠️ only.
pass(){ printf "✅ %s\n" "$1"; }
fail(){ printf "❌ %s\n" "$1"; RUN_OK=0; }
warn(){ printf "⚠️  %s\n" "$1"; }
build_warn(){ printf "⚠️  %s\n" "$1"; BUILD_OK=0; }
RUN_OK=1
BUILD_OK=1
OS=$(uname -s)
echo "=== Timesheet app — environment check ($(date '+%Y-%m-%d %H:%M')) ==="

echo
echo "--- Your computer (information) ---"
if [ "$OS" = "Darwin" ]; then
  OSV=$(sw_vers -productVersion); MAJOR=${OSV%%.*}
  [ "$MAJOR" -ge 13 ] && pass "macOS $OSV" || warn "macOS $OSV (13+ recommended)"
  CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
  [ "$(uname -m)" = "arm64" ] && pass "Apple Silicon ($CHIP)" || warn "Intel Mac ($CHIP) — Antigravity may not support Intel"
  RAM_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
else
  pass "$OS $(uname -r) (macOS-only checks are skipped)"
  RAM_GB=$(( $(awk '/MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo 0) / 1048576 ))
fi
if [ "$RAM_GB" -ge 8 ]; then pass "RAM ${RAM_GB} GB"; else warn "RAM ${RAM_GB} GB (8 GB or more recommended)"; fi
FREE_GB=$(( $(df -k ~ | awk 'NR==2{print $4}') / 1048576 ))
[ "$FREE_GB" -ge 5 ] && pass "Free disk ${FREE_GB} GB" || warn "Free disk ${FREE_GB} GB (5 GB or more recommended)"

echo
echo "--- Needed to RUN the app ---"
command -v git >/dev/null && pass "$(git --version)" || fail "Git missing → macOS: xcode-select --install · Linux: install git with your package manager"
if command -v uv >/dev/null; then
  pass "$(uv --version)"
  if PY=$(uv python find 3.13 2>/dev/null); then
    pass "Python $("$PY" -c 'import sys;print(sys.version.split()[0])') (via uv, matches .python-version)"
  else fail "Python 3.13 missing → uv python install 3.13   (uv sync also installs it)"; fi
else
  fail "uv missing → macOS: brew install uv · Linux: curl -LsSf https://astral.sh/uv/install.sh | sh"
  fail "Python 3.13 can't be checked without uv"
fi
if command -v lsof >/dev/null && lsof -i :8000 >/dev/null 2>&1; then
  fail "Port 8000 busy: $(lsof -i :8000 | awk 'NR==2{print $1" (PID "$2")"}') → stop that server, or use: uv run python manage.py runserver 8001"
else pass "Port 8000 free (the app's port)"; fi

echo
echo "--- Needed to BUILD with Claude Code (only to change the app) ---"
command -v claude >/dev/null && pass "Claude Code $(claude --version 2>/dev/null | head -1)" || build_warn "Claude Code CLI missing"
[ -n "$ANTHROPIC_API_KEY" ] && build_warn "ANTHROPIC_API_KEY is set — Claude Code will bill the API instead of your Claude plan" || pass "No ANTHROPIC_API_KEY set (uses your Claude plan)"
N=$(cd ~ && git config user.name 2>/dev/null); E=$(cd ~ && git config user.email 2>/dev/null)
[ -n "$N" ] && [ -n "$E" ] && pass "Git identity: $N <$E>" || build_warn "Git name/email not set → git config --global user.name \"…\"; git config --global user.email \"…\""
if command -v git >/dev/null && (cd ~ && git rev-parse --show-toplevel >/dev/null 2>&1); then
  build_warn "Home folder is a Git repo → mv ~/.git ~/.git-backup-old"
else pass "Home folder is not a Git repo"; fi
if [ "$OS" = "Darwin" ]; then
  xcode-select -p >/dev/null 2>&1 && pass "Xcode Command Line Tools" || build_warn "Xcode Command Line Tools missing → xcode-select --install"
  command -v brew >/dev/null && pass "Homebrew $(brew --version | head -1 | awk '{print $2}')" || build_warn "Homebrew missing (see BUILD_GUIDE A.3)"
  [ -d "/Applications/Antigravity.app" ] && pass "Antigravity installed" || build_warn "Antigravity.app not found in /Applications"
else
  pass "Xcode tools, Homebrew and Antigravity checks skipped (not macOS)"
fi
command -v sqlite3 >/dev/null && pass "sqlite3 $(sqlite3 --version | awk '{print $1}')" || warn "sqlite3 command-line tool missing (optional)"

echo
if [ $RUN_OK -eq 1 ]; then echo "✅ Ready to RUN the app."; else echo "❌ Not ready to run — fix the ❌ items above, then run this again."; fi
if [ $BUILD_OK -eq 1 ]; then echo "✅ Ready to BUILD with Claude Code."; else echo "⚠️  Not ready to BUILD with Claude Code yet (only needed to change the app) — see the ⚠️ items."; fi
[ $RUN_OK -eq 1 ]
