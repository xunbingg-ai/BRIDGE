#!/usr/bin/env bash
set -euo pipefail

# Local Playwright e2e runner used by the independent-context EVALUATOR
# subagent. It:
#   - Bypasses the environment's HTTP(s)/SOCKS proxy for localhost (the proxy
#     otherwise breaks app <-> browser traffic to 127.0.0.1).
#   - Invokes the playwright binary directly (never through pnpm) so it works
#     even when the pnpm store is mounted read-only.
#
# The backend (Flask :5000) and frontend (Nuxt :3000) are started automatically
# by playwright.config.ts's `webServer` blocks (reused if already running).
#
# Usage:  cd frontend && pnpm e2e     (or)  bash e2e.sh [playwright args]

export NO_PROXY="127.0.0.1,localhost,0.0.0.0"
export no_proxy="$NO_PROXY"

cd "$(dirname "$0")"
exec ./node_modules/.bin/playwright test "$@"
