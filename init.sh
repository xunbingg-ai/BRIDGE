#!/bin/bash
set -e
export PATH="$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
cd "$(dirname "$0")"

echo "=== Secret hygiene check ==="
if ! git check-ignore -q backend/.env; then
  echo "FATAL: backend/.env is NOT git-ignored; refusing to continue" >&2
  exit 1
fi
if [ -n "$(git ls-files backend/.env)" ]; then
  echo "FATAL: backend/.env is tracked by git; remove it first" >&2
  exit 1
fi
echo "backend/.env is git-ignored (OK)"

echo "=== BRIDGE Harness Verification ==="

if [ ! -d backend/.venv ] || [ ! -d frontend/node_modules ]; then
  echo "Dependencies missing — running scripts/setup-dev.sh first"
  bash scripts/setup-dev.sh
fi

echo "=== Backend tests (pytest) ==="
(cd backend && uv run pytest -q)

echo "=== Frontend typecheck ==="
(cd frontend && npm run typecheck)

echo "=== Frontend build ==="
(cd frontend && npm run build)

echo "=== Verification Complete ==="
echo ""
echo "Next steps:"
echo "1. Read feature_list.json to see current feature state"
echo "2. Pick ONE unfinished feature to work on"
echo "3. Implement only that feature"
echo "4. Re-run ./init.sh before claiming done"
