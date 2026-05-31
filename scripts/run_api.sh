#!/usr/bin/env bash
# Run the FastAPI backend WITHOUT Docker.
# Uses the local .venv if present, otherwise whatever `python3`/`python` is active
# (system, conda, pyenv, etc.) — so it works regardless of how you set up Python.
set -e
cd "$(dirname "$0")/.."

export PYTHONPATH="$(pwd)/src"
export CIP_MODE="${CIP_MODE:-MOCK}"

# Pick an interpreter: prefer local venv, then python3, then python.
if [ -x ".venv/bin/python" ]; then
  PY=".venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY="python3"
else
  PY="python"
fi

echo "Starting Certificate Intelligence API (CIP_MODE=$CIP_MODE) using: $PY"
exec "$PY" -m uvicorn cip.app:app --host 0.0.0.0 --port "${CIP_PORT:-8000}"
