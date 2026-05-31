#!/usr/bin/env bash
# Run the Next.js dashboard in dev mode WITHOUT Docker.
# Points at the local backend; if the backend is down it falls back to bundled
# mock data automatically (you'll see a MOCK badge instead of LIVE).
set -e
cd "$(dirname "$0")/../dashboard"

if [ ! -d "node_modules" ]; then
  echo "node_modules missing — installing dashboard dependencies first..."
  npm install
fi

export NEXT_PUBLIC_API_BASE="${NEXT_PUBLIC_API_BASE:-http://localhost:8000}"
echo "Starting dashboard (API base: $NEXT_PUBLIC_API_BASE) on http://localhost:3000"
exec npm run dev
