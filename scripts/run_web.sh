#!/usr/bin/env bash
# Start Plant Wiki web control panel (http://127.0.0.1:8765)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/uvicorn" ]]; then
  PY="$ROOT/.venv/bin/python"
  UVICORN="$ROOT/.venv/bin/uvicorn"
elif command -v uvicorn >/dev/null 2>&1; then
  PY="$(command -v python3)"
  UVICORN="$(command -v uvicorn)"
else
  echo "Install web deps first: $ROOT/.venv/bin/pip install -r requirements-web.txt" >&2
  exit 1
fi

if ! "$PY" -c "import fastapi" 2>/dev/null; then
  echo "Installing requirements-web.txt..."
  "$ROOT/.venv/bin/pip" install -q -r "$ROOT/requirements-web.txt"
fi

HOST="${PLANT_WIKI_WEB_HOST:-127.0.0.1}"
PORT="${PLANT_WIKI_WEB_PORT:-8765}"
echo "Plant Wiki UI: http://${HOST}:${PORT}"
exec "$UVICORN" app.main:app --reload --host "$HOST" --port "$PORT"
