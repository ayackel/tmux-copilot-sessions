#!/usr/bin/env bash
# popup.sh — launches fzf with the session picker and preview.
# Wraps fzf in a loop to support collapsible directory groups:
# Enter on a DIR row toggles collapse and re-runs fzf;
# Enter on a SESSION row opens it in a new tmux window.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DB="${COPILOT_SESSIONS_DB:-$HOME/.copilot/session-store.db}"
STATE_FILE="${TMPDIR:-/tmp}/copilot-sessions-collapsed"

if [ ! -f "$DB" ]; then
  echo "Copilot session database not found: $DB"
  read -r
  exit 1
fi

if ! command -v fzf &>/dev/null; then
  echo "fzf is required but not installed."
  read -r
  exit 1
fi

QUERY=""
while true; do
  output=$(python3 "$SCRIPT_DIR/picker.py" --collapsed-file "$STATE_FILE" | fzf \
    --ansi \
    --delimiter='\t' \
    --with-nth=1 \
    --nth=1 \
    --print-query \
    --query="$QUERY" \
    --preview="python3 $SCRIPT_DIR/preview.py {2} {3} {4}" \
    --preview-window=right:50%:wrap \
    --bind='J:preview-down,K:preview-up' \
    --bind='ctrl-d:preview-half-page-down,ctrl-u:preview-half-page-up' \
    --bind='g:preview-top,G:preview-bottom' \
    --bind='/:toggle-preview' \
    --header='Enter=toggle/open  /=preview  J/K=scroll' \
    --no-sort \
    --reverse \
    --no-info \
  ) || true

  QUERY=$(head -1 <<< "$output")
  line=$(tail -n +2 <<< "$output" | head -1)

  [ -z "$line" ] && break

  row_type=$(printf '%s' "$line" | cut -f2)

  if [ "$row_type" = "DIR" ]; then
    dir=$(printf '%s' "$line" | cut -f3)
    bash "$SCRIPT_DIR/toggle.sh" "$STATE_FILE" "$dir"
    continue
  fi

  cwd=$(printf '%s' "$line" | cut -f3)
  sid=$(printf '%s' "$line" | cut -f4)
  bash "$SCRIPT_DIR/open.sh" "$cwd" "$sid"
  break
done
