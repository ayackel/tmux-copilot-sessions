# Copilot Instructions — tmux-copilot-sessions

## What This Is

A tmux plugin (TPM-compatible) that provides a fuzzy-finder popup for browsing and resuming GitHub Copilot CLI sessions. Prefix+g opens an fzf-based floating popup with session list and conversation preview.

## Architecture

```
tmux-copilot-sessions.tmux   ← TPM entry point: reads tmux options, binds key to popup
scripts/
  popup.sh                   ← Launched inside the popup: pipes picker → fzf → open
  picker.py                  ← Reads session-store.db, emits tab-delimited lines for fzf
  preview.py                 ← fzf preview command: renders session conversation with ANSI colors
  open.sh                    ← Receives fzf selection, opens/switches to a tmux window running `copilot --resume=<id>`
  toggle.sh                  ← Toggles a directory's collapsed state in the state file
```

**Data flow:** `tmux keybind → popup.sh → picker.py | fzf (preview.py) → open.sh → tmux new-window`

The plugin reads from `~/.copilot/session-store.db` (SQLite, read-only). It never writes to the database.

## Key Conventions

- **Tab-delimited protocol:** picker.py outputs `<display>\tTYPE\t<cwd>\t<session-id>`. TYPE is `DIR` (group header) or `SESSION`. fzf shows column 1 (`--with-nth=1`), passes all columns to preview.py and open.sh. Any new data must go through this protocol.
- **Collapsible groups:** Directory headers are selectable rows. Enter on a DIR row toggles its collapsed state via a temp file (`$TMPDIR/copilot-sessions-collapsed`), then re-runs fzf with the search query preserved. picker.py reads this file via `--collapsed-file` to skip sessions under collapsed dirs.
- **Read-only DB access:** All SQLite connections use `?mode=ro` URI. Do not add write operations.
- **ANSI colors:** Both Python scripts use 256-color ANSI escapes (e.g., `\033[38;5;45m`). fzf is invoked with `--ansi`. Keep color constants consistent between picker.py and preview.py.
- **Shell scripts use `set -euo pipefail`.**
- **Python scripts use no external dependencies** — only stdlib (`sqlite3`, `textwrap`, `pathlib`, `os`, `sys`).

## Configuration

tmux options are read in the `.tmux` entry point with fallback defaults:

| Option | Default |
|--------|---------|
| `@copilot_sessions_key` | `g` |
| `@copilot_sessions_popup_width` | `80%` |
| `@copilot_sessions_popup_height` | `75%` |
| `@copilot_sessions_db` | `~/.copilot/session-store.db` |
| `@copilot_sessions_command` | `copilot` |

## Session DB Schema (read-only)

The plugin depends on these tables from the Copilot CLI session store:

- `sessions` — `id`, `cwd`, `summary`, `repository`, `branch`, `created_at`, `updated_at`
- `turns` — `session_id`, `turn_index`, `user_message`, `assistant_response`
- `session_files` — `session_id`, `file_path`
