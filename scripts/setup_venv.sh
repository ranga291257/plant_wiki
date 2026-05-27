#!/usr/bin/env bash
# Create (or refresh) the project virtual environment at .venv/
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$ROOT/.venv"

venv_is_stale() {
  [[ ! -f "$VENV/bin/activate" ]] && return 0
  local repo_name
  repo_name="$(basename "$ROOT")"
  # Copied venvs keep the old project name in bin/activate
  grep -q "${repo_name}/.venv" "$VENV/bin/activate" 2>/dev/null && return 1
  return 0
}

if venv_is_stale; then
  echo "Removing stale .venv (activate script points at another project)..."
  rm -rf "$VENV"
fi

if [[ ! -d "$VENV" ]]; then
  echo "Creating $VENV ..."
  python3 -m venv "$VENV"
else
  echo "Using existing $VENV"
fi

if [[ -f "$ROOT/requirements.txt" ]]; then
  "$VENV/bin/pip" install -q -r "$ROOT/requirements.txt"
fi

echo "Python: $("$VENV/bin/python" --version)"
echo ""
echo "The venv exists at .venv/ but your current shell is unchanged until you activate it."
echo ""
echo "Option A — activate in this terminal (then 'which python3' shows .venv):"
echo "  source scripts/activate"
echo ""
echo "Option B — run scripts without activating:"
echo "  ./run scripts/convert_raw_to_wiki.py"
echo ""
echo "Option C — in Cursor: open a NEW terminal tab (settings prepend .venv to PATH)."
