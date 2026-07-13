#!/usr/bin/env bash
# KIRIS installer — standalone assistant HTTP server. No panel, no laris needed.
# Usage: bash scripts/install.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_ROOT"

echo "=== KIRIS installer ==="
echo "Repo: $REPO_ROOT"
echo ""

if ! python3.11 --version &>/dev/null; then
  echo "ERROR: Python 3.11 not found. Install it via 'brew install python@3.11' or pyenv." >&2
  exit 1
fi

if [[ ! -d ".venv" ]]; then
  python3.11 -m venv .venv
fi

.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .

echo ""
echo "Verifying..."
.venv/bin/python -c "import kiris; print('KIRIS import OK')"
.venv/bin/python -c "from kiris.daemon import build_app, PanelClient; print('daemon OK')"

echo ""
echo "=== KIRIS installed successfully ==="
echo ""
echo "To start:"
echo "  .venv/bin/python -m kiris         # HTTP server on :8422"
echo ""
echo "Test with curl:"
echo "  curl -X POST http://127.0.0.1:8422/ask -H 'Content-Type: application/json' -d '{\"request\": \"hello\"}'"
echo ""
echo "To stop: pkill -9 -f 'python -m kiris'"
