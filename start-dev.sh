#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
VENV_DIR="$BACKEND_DIR/.venv"
BACKEND_PID=""

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

load_env_file() {
  if [[ -f "$ROOT_DIR/.env" ]]; then
    echo "Loading environment from .env"
    set -a
    # shellcheck disable=SC1091
    source "$ROOT_DIR/.env"
    set +a
  fi
}

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

require_command uv
require_command python3
require_command npm
if ! command -v claude &>/dev/null; then
  echo "Warning: 'claude' CLI not found. Live scans will fail, but the sample project will still work."
fi

load_env_file

# Determine authentication mode.
# Priority: ANTHROPIC_API_KEY (API billing) → Claude Code subscription (via `claude login`).
if [[ -n "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "Using ANTHROPIC_API_KEY for authentication (billed to your API key)."
else
  # Check if the user is authenticated via Claude Code subscription
  if command -v claude &>/dev/null && claude --version &>/dev/null 2>&1; then
    echo "No ANTHROPIC_API_KEY found. Using Claude Code subscription for authentication."
    echo "To use an API key instead, add ANTHROPIC_API_KEY to .env or export it in your shell."
  else
    echo "No authentication method found."
    echo ""
    echo "Option 1 (recommended): Log in with your Claude Code subscription:"
    echo "  claude login"
    echo ""
    echo "Option 2: Add an API key to .env (billed to your Anthropic API account):"
    echo "  echo 'ANTHROPIC_API_KEY=sk-ant-...' >> .env"
    exit 1
  fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating backend virtual environment"
  uv venv "$VENV_DIR"
fi

echo "Installing backend dependencies"
uv pip install --python "$VENV_DIR/bin/python" -e "$BACKEND_DIR"

if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
  echo "Installing frontend dependencies"
  (
    cd "$FRONTEND_DIR"
    npm install
  )
fi

echo "Starting backend on http://localhost:8000"
(
  cd "$BACKEND_DIR"
  # shellcheck disable=SC1091
  source "$VENV_DIR/bin/activate"
  exec python -m uvicorn main:app --reload --port 8000
) &
BACKEND_PID=$!

sleep 2

if ! kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
  echo "Backend failed to start."
  exit 1
fi

echo "Starting frontend on http://localhost:5173"
echo "Press Ctrl+C to stop both servers."
(
  cd "$FRONTEND_DIR"
  npm run dev
)
