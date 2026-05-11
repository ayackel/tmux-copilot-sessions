#!/usr/bin/env bash
# open.sh — opens a tmux window with `copilot --resume=<session-id>`,
# cd'd to the project directory.
# If a window for the session already exists, switches to it instead.
#
# Usage: open.sh <cwd> <session-id>

set -euo pipefail

DIR="$1"
SID="$2"

[ -z "$SID" ] && exit 0

# Fall back to home if dir doesn't exist
[ ! -d "$DIR" ] && DIR="$HOME"

# Window name from session id (first 8 chars)
WIN_NAME="copilot-${SID:0:8}"

# If a window for this session already exists, switch to it
existing=$(tmux list-windows -a -F "#{session_name}:#{window_name}" 2>/dev/null \
  | grep ":${WIN_NAME}$" | head -1 || true)

if [ -n "$existing" ]; then
  tmux switch-client -t "$existing"
  exit 0
fi

# Create a new window and resume the session
CURRENT_SESSION=$(tmux display-message -p '#S')

tmux new-window -n "$WIN_NAME" -c "$DIR" -t "${CURRENT_SESSION}:"
CMD="${COPILOT_SESSIONS_CMD:-copilot}"
tmux send-keys -t "${CURRENT_SESSION}:${WIN_NAME}" "${CMD} --resume=${SID}" Enter
