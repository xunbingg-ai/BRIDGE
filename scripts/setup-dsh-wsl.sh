#!/bin/bash
set -euo pipefail
export PATH="$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

# Install/refresh the native DeepSeek Harness CLI (dsh) inside WSL.
#
# Why: on Windows the dsh npm shim routes through PowerShell/Windows paths,
# which is exactly the "agents fight PowerShell" pain. Installing dsh natively
# in WSL makes `dsh web` run against a real bash environment.

DSH_VERSION="${DSH_VERSION:-0.1.0-rc.7}"
ALLOW_SCRIPTS="@deepseek-ai/dsh-subprocess-local,koffi,node-pty,@google/genai,protobufjs"

echo "=== Checking prerequisites ==="
command -v node >/dev/null || { echo "FATAL: node not found in WSL. Install Node.js first." >&2; exit 1; }
command -v npm >/dev/null || { echo "FATAL: npm not found in WSL. Install npm first." >&2; exit 1; }
node --version
npm --version

echo "=== Installing @deepseek-ai/dsh@${DSH_VERSION} globally ==="
GLOBAL_PREFIX="$(npm prefix -g)"
if [ "$(id -u)" -eq 0 ]; then
  npm install -g --allow-scripts="$ALLOW_SCRIPTS" "@deepseek-ai/dsh@${DSH_VERSION}"
elif [ -w "$GLOBAL_PREFIX" ]; then
  npm install -g --allow-scripts="$ALLOW_SCRIPTS" "@deepseek-ai/dsh@${DSH_VERSION}"
else
  # WSL user in sudo group; the default Ubuntu image usually has passwordless sudo.
  sudo -n npm install -g --allow-scripts="$ALLOW_SCRIPTS" "@deepseek-ai/dsh@${DSH_VERSION}"
fi

echo "=== Verifying ==="
dsh --version
dsh web --help >/dev/null

echo ""
echo "=== Setup complete ==="
echo "Inside WSL, start the DeepSeek Harness browser UI with:"
echo ""
echo "  dsh web"
echo ""
echo "If port 3080 is busy, use a custom port:"
echo ""
echo "  dsh web --port 8080"
