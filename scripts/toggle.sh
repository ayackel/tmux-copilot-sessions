#!/usr/bin/env bash
# toggle.sh — toggles a directory in the collapsed-state file
# Usage: toggle.sh <state-file> <dir-path>

set -euo pipefail

STATE_FILE="$1"
DIR="$2"

[ -z "$DIR" ] && exit 0

touch "$STATE_FILE"

if grep -qxF "$DIR" "$STATE_FILE" 2>/dev/null; then
    { grep -vxF "$DIR" "$STATE_FILE" || true; } > "${STATE_FILE}.tmp"
    mv "${STATE_FILE}.tmp" "$STATE_FILE"
else
    echo "$DIR" >> "$STATE_FILE"
fi
