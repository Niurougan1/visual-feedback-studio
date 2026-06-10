#!/usr/bin/env bash
set -euo pipefail

REPO_URL="${VFS_REPO_URL:-https://github.com/Niurougan1/visual-feedback-studio.git}"
INSTALL_DIR="${VFS_INSTALL_DIR:-$HOME/visual-feedback-studio}"
CHANNEL="${VFS_CHANNEL:-beta}"
PORT="${VFS_PORT:-3456}"
PROJECT_ROOT="${VFS_PROJECT_ROOT:-$PWD}"

if command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="${PYTHON_BIN:-python3}"
else
  echo "python3 is required but was not found in PATH." >&2
  exit 127
fi

if ! command -v git >/dev/null 2>&1; then
  echo "git is required but was not found in PATH." >&2
  exit 127
fi

if [ -d "$INSTALL_DIR/.git" ]; then
  git -C "$INSTALL_DIR" pull --ff-only
else
  git clone "$REPO_URL" "$INSTALL_DIR"
fi

exec "$PYTHON_BIN" "$INSTALL_DIR/scripts/setup.py" "$PROJECT_ROOT" --channel "$CHANNEL" --port "$PORT"
