#!/usr/bin/env python3
"""
preview.py — renders a Copilot CLI session conversation for fzf preview.

Usage: preview.py <session-id>
"""

import os
import sqlite3
import sys
import textwrap
from pathlib import Path

DB_PATH = os.environ.get("COPILOT_SESSIONS_DB", str(Path.home() / ".copilot" / "session-store.db"))

# ── ANSI colors ───────────────────────────────────────────────────────────────

CYAN    = "\033[38;5;45m"
GREEN   = "\033[38;5;114m"
YELLOW  = "\033[38;5;226m"
MAGENTA = "\033[38;5;201m"
GRAY    = "\033[38;5;242m"
WHITE   = "\033[38;5;252m"
BOLD    = "\033[1m"
DIM     = "\033[2m"
RESET   = "\033[0m"

# ── main ──────────────────────────────────────────────────────────────────────

def get_preview_width() -> int:
    """Get available width from fzf preview columns."""
    return int(os.environ.get("FZF_PREVIEW_COLUMNS", 80))


def show_dir_preview(cwd_path: str) -> None:
    """Show a summary of all sessions in a directory."""
    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    home = str(Path.home())
    short = cwd_path.replace(home, "~") if cwd_path != "(no directory)" else cwd_path

    if cwd_path == "(no directory)":
        cur.execute("""
            SELECT id, summary, created_at, updated_at
            FROM sessions WHERE cwd IS NULL OR cwd = ''
            ORDER BY COALESCE(updated_at, created_at) DESC
        """)
    else:
        cur.execute("""
            SELECT id, summary, created_at, updated_at
            FROM sessions WHERE cwd = ?
            ORDER BY COALESCE(updated_at, created_at) DESC
        """, (cwd_path,))

    rows = cur.fetchall()
    conn.close()

    width = get_preview_width()
    n = len(rows)
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{WHITE}{short}{RESET}")
    print(f"{GRAY}{n} session{'s' if n != 1 else ''}{RESET}")
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")

    for row in rows:
        summary = row["summary"] or "(no summary)"
        ts = (row["updated_at"] or row["created_at"] or "")[:19].replace("T", " ")
        print(f"\n  {GREEN}{ts}{RESET}  {WHITE}{summary}{RESET}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: preview.py <type> <cwd> [session-id]")
        sys.exit(1)

    # Dispatch: DIR shows directory summary, SESSION shows conversation
    if len(sys.argv) >= 3 and sys.argv[1].strip() == "DIR":
        show_dir_preview(sys.argv[2].strip())
        return

    # SESSION mode (or backward-compat single arg)
    session_id = sys.argv[-1].strip()
    if not session_id:
        sys.exit(0)

    if not os.path.exists(DB_PATH):
        print(f"DB not found: {DB_PATH}")
        sys.exit(1)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Session metadata
    cur.execute("SELECT id, cwd, summary, repository, branch, created_at, updated_at FROM sessions WHERE id = ?", (session_id,))
    session = cur.fetchone()
    if not session:
        print(f"Session not found: {session_id}")
        conn.close()
        sys.exit(0)

    home = str(Path.home())
    cwd = (session["cwd"] or "").replace(home, "~")
    summary = session["summary"] or ""
    created = (session["created_at"] or "")[:19].replace("T", " ")
    updated = (session["updated_at"] or "")[:19].replace("T", " ")
    repo = session["repository"] or ""
    branch = session["branch"] or ""

    # Header
    width = get_preview_width()
    print(f"{BOLD}{CYAN}{'─' * width}{RESET}")
    if summary:
        print(f"{BOLD}{WHITE}{summary}{RESET}")
    print(f"{GRAY}Session:  {RESET}{session_id[:12]}…")
    if cwd:
        print(f"{GRAY}Dir:      {RESET}{cwd}")
    if repo:
        print(f"{GRAY}Repo:     {RESET}{repo}")
    if branch:
        print(f"{GRAY}Branch:   {RESET}{branch}")
    print(f"{GRAY}Created:  {RESET}{created}")
    if updated and updated != created:
        print(f"{GRAY}Updated:  {RESET}{updated}")

    # Files touched
    cur.execute(
        "SELECT DISTINCT file_path FROM session_files WHERE session_id = ? LIMIT 10",
        (session_id,),
    )
    files = [r["file_path"].replace(home, "~") for r in cur.fetchall()]
    if files:
        print(f"\n{YELLOW}Files touched:{RESET}")
        for f in files:
            print(f"  {DIM}{f}{RESET}")

    print(f"\n{BOLD}{CYAN}{'─' * width}{RESET}")

    # Conversation turns
    cur.execute(
        "SELECT turn_index, user_message, assistant_response FROM turns WHERE session_id = ? ORDER BY turn_index",
        (session_id,),
    )
    turns = cur.fetchall()
    conn.close()

    cols = width - 4

    for turn in turns:
        idx = turn["turn_index"]
        user_msg = (turn["user_message"] or "").strip()
        assistant_msg = (turn["assistant_response"] or "").strip()

        if user_msg:
            # Skip XML-heavy system messages
            if user_msg.startswith("<") and len(user_msg) > 500:
                user_msg = "(system context)"
            elif len(user_msg) > 300:
                user_msg = user_msg[:297] + "…"
            print(f"\n{GREEN}{BOLD}  You [{idx}]:{RESET}")
            for line in user_msg.split("\n")[:6]:
                wrapped = textwrap.fill(line, width=cols) if len(line) > cols else line
                print(f"  {WHITE}{wrapped}{RESET}")

        if assistant_msg:
            if len(assistant_msg) > 500:
                assistant_msg = assistant_msg[:497] + "…"
            print(f"\n{MAGENTA}{BOLD}  🤖 Copilot [{idx}]:{RESET}")
            for line in assistant_msg.split("\n")[:10]:
                wrapped = textwrap.fill(line, width=cols) if len(line) > cols else line
                print(f"  {GRAY}{wrapped}{RESET}")


if __name__ == "__main__":
    main()
