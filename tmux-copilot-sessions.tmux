#!/usr/bin/env bash
# tmux-copilot-sessions.tmux — TPM-compatible plugin entry point
#
# Binds a key (default: prefix+g) to open an fzf popup listing all
# GitHub Copilot CLI sessions, grouped by project directory.

PLUGIN_DIR="$(cd "$(dirname "$0")" && pwd)"

KEY=$(tmux show-option -gv @copilot_sessions_key 2>/dev/null); KEY=${KEY:-g}
WIDTH=$(tmux show-option -gv @copilot_sessions_popup_width 2>/dev/null); WIDTH=${WIDTH:-80%}
HEIGHT=$(tmux show-option -gv @copilot_sessions_popup_height 2>/dev/null); HEIGHT=${HEIGHT:-75%}
DB=$(tmux show-option -gv @copilot_sessions_db 2>/dev/null); DB=${DB:-~/.copilot/session-store.db}
DB="${DB/#\~/$HOME}"
CMD=$(tmux show-option -gv @copilot_sessions_command 2>/dev/null); CMD=${CMD:-copilot}

tmux bind-key "$KEY" display-popup \
  -w "$WIDTH" \
  -h "$HEIGHT" \
  -d "#{pane_current_path}" \
  -e "COPILOT_SESSIONS_DB=$DB" \
  -e "COPILOT_SESSIONS_CMD=$CMD" \
  -e "PLUGIN_DIR=$PLUGIN_DIR" \
  -E "bash $PLUGIN_DIR/scripts/popup.sh"
