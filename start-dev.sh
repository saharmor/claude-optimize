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

require_command python3
require_command npm
if ! command -v claude &>/dev/null; then
  echo "Warning: 'claude' CLI not found. Live scans will fail, but the sample project will still work."
fi

load_env_file

if [[ -z "${ANTHROPIC_API_KEY:-}" ]]; then
  echo "ANTHROPIC_API_KEY is not set."
  echo "Add it to .env or export it in your shell, then run this script again."
  exit 1
fi

if [[ ! -d "$VENV_DIR" ]]; then
  echo "Creating backend virtual environment"
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

echo "Installing backend dependencies"
python -m pip install -e "$BACKEND_DIR"

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
