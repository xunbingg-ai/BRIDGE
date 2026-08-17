#!/bin/bash
set -e
export PATH="$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
cd "$(dirname "$0")/.."

echo "=== Backend: uv sync ==="
(cd backend && uv sync)

echo "=== Frontend: npm install ==="
(cd frontend && npm install)

echo "=== Setup complete ==="
