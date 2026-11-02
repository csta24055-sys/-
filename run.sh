#!/usr/bin/env bash
# Air Quality Research OS 起動スクリプト
set -euo pipefail
cd "$(dirname "$0")"
if [ ! -x .venv/bin/uvicorn ]; then python3 -m venv .venv && .venv/bin/pip install -q -r backend/requirements.txt; fi
if [ ! -f frontend/dist/index.html ]; then (cd frontend && npm install && npm run build); fi
echo "Air Quality Research OS: http://localhost:${PORT:-8000}"
exec .venv/bin/uvicorn app.main:app --app-dir backend --host "${HOST:-0.0.0.0}" --port "${PORT:-8000}"
