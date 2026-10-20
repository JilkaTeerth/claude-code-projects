#!/usr/bin/env bash
# homesound launcher
set -euo pipefail
cd "$(dirname "$0")"
PORT="${HOMESOUND_PORT:-8777}"
echo "homesound -> http://127.0.0.1:${PORT}"
exec ./.venv/bin/python -m uvicorn app.server:app --host 127.0.0.1 --port "${PORT}" --log-level warning
