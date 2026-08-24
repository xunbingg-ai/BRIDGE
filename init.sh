#!/bin/bash
set -e

echo "=== OSCE Harness Initialization ==="

REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"

# ---------- Backend (Flask + SQLite) ----------
echo ""
echo "--- Backend ---"
cd "$REPO_ROOT/backend"

if [ ! -d ".venv" ]; then
  echo "[backend] Creating virtual environment..."
  python3 -m venv .venv || python -m venv .venv
  # ensurepip may fail on some builds; fall back to bootstrapping pip manually.
  if ! ./.venv/bin/python -m pip --version >/dev/null 2>&1; then
    echo "[backend] Bootstrapping pip into venv..."
    ./.venv/bin/python -m ensurepip --upgrade 2>/dev/null || \
      curl -sS https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py && ./.venv/bin/python /tmp/get-pip.py
    rm -f /tmp/get-pip.py
  fi
fi

if ./.venv/bin/python -c "import flask, flask_cors, jwt, requests" 2>/dev/null; then
  echo "[backend] Dependencies already present, skipping install."
else
  echo "[backend] Installing dependencies..."
  ./.venv/bin/python -m pip install -q -r requirements.txt
fi

echo "[backend] Verifying imports..."
./.venv/bin/python -c "import flask, flask_cors, jwt, requests; print('  backend deps OK')"

echo "[backend] Verifying app entry & database..."
if [ ! -f osce.db ]; then
  echo "[backend] No osce.db found; will auto-create on first run."
fi
./.venv/bin/python -c "import app; print('  app import OK')"
# Seed the DB if empty (idempotent)
./.venv/bin/python -c "from database import init_db; init_db(); print('  db init OK')"

# ---------- Frontend (Nuxt 4) ----------
echo ""
echo "--- Frontend ---"
cd "$REPO_ROOT/frontend"

if ! command -v pnpm >/dev/null 2>&1; then
  echo "[frontend] pnpm not found. Install it with: npm i -g pnpm   (or corepack enable)"
  exit 1
fi

if [ ! -d "node_modules" ]; then
  echo "[frontend] Installing dependencies (first run may take a while)..."
  pnpm install
else
  echo "[frontend] node_modules present, skipping install"
fi

echo "[frontend] Verifying Nuxt config + typegen (fast check)..."
pnpm exec nuxt prepare

if [ "${FULL:-0}" = "1" ]; then
  echo "[frontend] Running full production build..."
  pnpm build
else
  echo "[frontend] Full build skipped. Run with FULL=1 ./init.sh to build."
  echo "[frontend]   → cd frontend && pnpm build   (definitive verification / publish gate)"
fi

echo ""
echo "=== Verification Complete ==="
echo ""
echo "Next steps:"
echo "1. Read feature_list.json to see current feature state"
echo "2. Pick ONE unfinished feature to work on"
echo "3. Implement only that feature"
echo "4. Re-run ./init.sh before claiming done"
echo ""
echo "Run the servers with:"
echo "  Backend : backend/.venv/bin/python backend/app.py  (port 5000)"
echo "  Frontend: PORT=3000 node frontend/.output/server/index.mjs  (http://localhost:3000)"
