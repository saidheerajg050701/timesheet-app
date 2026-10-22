#!/usr/bin/env bash
# Timesheet project (Python/Django) — environment doctor for macOS
pass(){ printf "✅ %s\n" "$1"; }
fail(){ printf "❌ %s\n" "$1"; FAILED=1; }
warn(){ printf "⚠️  %s\n" "$1"; }
FAILED=0
echo "=== Timesheet app — environment check ($(date '+%Y-%m-%d %H:%M')) ==="

OSV=$(sw_vers -productVersion); MAJOR=${OSV%%.*}
[ "$MAJOR" -ge 13 ] && pass "macOS $OSV" || fail "macOS $OSV (need 13+)"
ARCH=$(uname -m); CHIP=$(sysctl -n machdep.cpu.brand_string 2>/dev/null)
[ "$ARCH" = "arm64" ] && pass "Apple Silicon ($CHIP)" || warn "Intel Mac ($CHIP) — Antigravity may not support Intel"
RAM_GB=$(( $(sysctl -n hw.memsize) / 1073741824 ))
if [ "$RAM_GB" -ge 16 ]; then pass "RAM ${RAM_GB} GB"; elif [ "$RAM_GB" -ge 8 ]; then warn "RAM ${RAM_GB} GB (16 GB recommended)"; else fail "RAM ${RAM_GB} GB"; fi
FREE_GB=$(df -g ~ | awk 'NR==2{print $4}')
[ "$FREE_GB" -ge 5 ] && pass "Free disk ${FREE_GB} GB" || fail "Free disk ${FREE_GB} GB (need 5+)"

xcode-select -p >/dev/null 2>&1 && pass "Xcode Command Line Tools" || fail "Xcode CLT missing → xcode-select --install"
command -v brew >/dev/null && pass "Homebrew $(brew --version | head -1 | awk '{print $2}')" || fail "Homebrew missing"
command -v git  >/dev/null && pass "$(git --version)" || fail "git missing"

if (cd ~ && git rev-parse --show-toplevel >/dev/null 2>&1); then
  warn "Home folder is a Git repo → mv ~/.git ~/.git-backup-old"
else pass "Home folder is not a Git repo"; fi
N=$(cd ~ && git config user.name); E=$(cd ~ && git config user.email)
[ -n "$N" ] && [ -n "$E" ] && pass "Git identity: $N <$E>" || fail "Git name/email not set"

if command -v uv >/dev/null; then
  pass "$(uv --version)"
  if PY=$(uv python find '>=3.12' 2>/dev/null); then
    pass "Python $("$PY" -c 'import sys;print(sys.version.split()[0])') (via uv)"
  else fail "No Python 3.12+ → uv python install 3.13"; fi
else fail "uv missing → brew install uv"; fi

command -v sqlite3 >/dev/null && pass "sqlite3 $(sqlite3 --version | awk '{print $1}')" || warn "sqlite3 CLI missing (optional)"
command -v claude >/dev/null && pass "Claude Code $(claude --version 2>/dev/null | head -1)" || fail "Claude Code CLI missing"
[ -n "$ANTHROPIC_API_KEY" ] && warn "ANTHROPIC_API_KEY is set — Claude Code will bill the API instead of your Pro plan" || pass "No ANTHROPIC_API_KEY set (uses your Claude plan)"
[ -d "/Applications/Antigravity.app" ] && pass "Antigravity installed" || warn "Antigravity.app not found in /Applications"

if lsof -i :8000 >/dev/null 2>&1; then
  warn "Port 8000 busy: $(lsof -i :8000 | awk 'NR==2{print $1" (PID "$2")"}')"
else pass "Port 8000 free (the app's port)"; fi

echo; [ $FAILED -eq 0 ] && echo "🎉 Ready to build." || echo "Fix the ❌ items above, then re-run."
