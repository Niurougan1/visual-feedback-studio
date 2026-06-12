#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${VFS_REPO_URL:-https://github.com/Niurougan1/visual-feedback-studio.git}"
INSTALL_DIR="${VFS_INSTALL_DIR:-$HOME/visual-feedback-studio}"
CHANNEL="${VFS_CHANNEL:-beta}"
PORT="${VFS_PORT:-3456}"
PROJECT_ROOT="${VFS_PROJECT_ROOT:-$PWD}"
PYTHON_BIN="${PYTHON_BIN:-python3}"

log() {
  printf '[vfs] %s\n' "$*" >&2
}

fail() {
  local message="$1"
  local code="${2:-1}"
  printf '[vfs] ERROR: %s\n' "$message" >&2
  exit "$code"
}

need_command() {
  local name="$1"
  local hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    fail "$name is required but was not found in PATH. $hint" 127
  fi
}

need_command "$PYTHON_BIN" "Install Python 3, then rerun the install command."
need_command git "Install Git, then rerun the install command."
need_command node "Install Node.js, then rerun the install command."

log "Visual Feedback Studio installer"
log "Project root: $PROJECT_ROOT"
log "Install dir:  $INSTALL_DIR"
log "Channel:      $CHANNEL"
log "Receiver:     http://127.0.0.1:$PORT"

if [ -e "$INSTALL_DIR" ] && [ ! -d "$INSTALL_DIR/.git" ]; then
  fail "VFS_INSTALL_DIR exists but is not a Git checkout: $INSTALL_DIR. Set VFS_INSTALL_DIR to another path or move that directory aside."
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  log "Updating existing checkout..."
  if ! git -C "$INSTALL_DIR" pull --ff-only; then
    fail "Could not fast-forward $INSTALL_DIR. Commit/stash local changes there, or rerun with VFS_INSTALL_DIR pointing to a clean path."
  fi
else
  log "Cloning public repository..."
  if ! git clone --depth 1 "$REPO_URL" "$INSTALL_DIR"; then
    fail "Could not clone $REPO_URL. Check your network/GitHub access, or set VFS_REPO_URL to a reachable mirror."
  fi
fi

if [ ! -f "$INSTALL_DIR/scripts/setup.py" ]; then
  fail "setup.py was not found after install: $INSTALL_DIR/scripts/setup.py"
fi

setup_args=("$PROJECT_ROOT" "--channel" "$CHANNEL" "--port" "$PORT")
if [ -n "${VFS_INSTALL_MODE:-}" ]; then
  setup_args+=("--install" "$VFS_INSTALL_MODE")
fi
if [ -n "${VFS_ALLOWED_ORIGIN:-}" ]; then
  setup_args+=("--allowed-origin" "$VFS_ALLOWED_ORIGIN")
fi

log "Running setup..."
if "$PYTHON_BIN" "$INSTALL_DIR/scripts/setup.py" "${setup_args[@]}"; then
  log "Setup complete. Load the printed chrome-extension path in chrome://extensions/."
else
  status=$?
  log "Setup failed. Read the JSON above for error, next_step, receiver.log_tail, and commands.status."
  exit "$status"
fi
