#!/usr/bin/env bash
# Prepare a session to develop and test INVISABLE OS core.
# Idempotent: safe to run repeatedly. Used by the Claude Code SessionStart hook.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "› Setting up INVISABLE OS core…"
cd core

if ! python3 -c "import venv" >/dev/null 2>&1; then
  echo "  python venv module unavailable; skipping venv setup." >&2
  exit 0
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
. .venv/bin/activate

pip install --quiet --upgrade pip >/dev/null 2>&1 || true
pip install --quiet -e ".[dev]" >/dev/null 2>&1 || {
  echo "  dependency install failed (offline?); core still importable for editing." >&2
  exit 0
}

echo "  ready. Run: cd core && . .venv/bin/activate && pytest"
