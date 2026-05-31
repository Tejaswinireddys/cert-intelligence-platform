#!/usr/bin/env bash
# One-time setup for running WITHOUT Docker.
# Creates a Python virtualenv, installs the backend (editable) + dev deps,
# and installs the dashboard's npm dependencies.
set -e
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

echo "==> [1/3] Creating Python virtualenv (.venv)"
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate

echo "==> [2/3] Installing backend (editable) + dev extras"
python -m pip install --upgrade pip >/dev/null
pip install -e ".[dev]"

echo "==> [3/3] Installing dashboard dependencies (npm)"
if command -v npm >/dev/null 2>&1; then
  ( cd "$ROOT/dashboard" && npm install )
else
  echo "    npm not found — skipping dashboard deps. Install Node 18+ then run:"
  echo "    (cd dashboard && npm install)"
fi

cat <<'EOF'

Setup complete. To run WITHOUT Docker, open two terminals:

  Terminal 1 (backend):
    bash scripts/run_api.sh
    # -> http://localhost:8000  (docs at /docs)

  Terminal 2 (dashboard):
    bash scripts/run_dashboard.sh
    # -> http://localhost:3000

Backend defaults to CIP_MODE=MOCK with a seeded simulated fleet, so it runs
fully offline. Add real credentials to .env later and set CIP_MODE=LIVE.
EOF
