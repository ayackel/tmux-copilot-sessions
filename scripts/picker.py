#!/usr/bin/env python3
"""
picker.py — lists all Copilot CLI sessions for fzf consumption.

Reads the session-store.db and emits one tab-delimited line per session:

    <display-text>\t<cwd>\t<session-id>

fzf uses --with-nth=1 so only the display text is shown;
columns 2 and 3 are passed to preview.py and open.sh as hidden payload.
"""

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Set

DB_PATH = os.environ.get("COPILOT_SESSIONS_DB", str(Path.home() / ".copilot" / "session-store.db"))

# ── ANSI colors ───────────────────────────────────────────────────────────────

CYAN    = "\033[38;5;45m"
MAGENTA = "\033[38;5;201m"
GRAY    = "\033[38;5;242m"
WHITE   = "\033[38;5;252m"
YELLOW  = "\033[38;5;226m"
GREEN   = "\033[38;5;114m"
RESET   = "\033[0m"


def col(s: str, c: str) -> str:
    return f"{c}{s}{RESET}"


# ── human-readable age ────────────────────────────────────────────────────────

def age(iso_ts: str) -> str:
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        s = int((datetime.now(timezone.utc) - dt).total_seconds())
    except Exception:
        return "?"
    if s < 3600:
        return f"{max(1, s // 60)}m"
    if s < 86400:
        return f"{s // 3600}h"
    return f"{s // 86400}d"


# ── project root inference ────────────────────────────────────────────────────

def _find_project_root(path: str, home: str) -> Optional[str]:
    """Walk up from path looking for a .git dir to find the project root.
    Stops at $HOME. Returns None if nothing useful is found."""
    d = path
    while d and len(d) > len(home):
        if os.path.isdir(os.path.join(d, ".git")):
            return d
        d = os.path.dirname(d)
    return None


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--collapsed-file", default="")
    args = parser.parse_args()

    collapsed: Set[str] = set()
    if args.collapsed_file and os.path.exists(args.collapsed_file):
        with open(args.collapsed_file) as f:
            collapsed = {line.strip() for line in f if line.strip()}

    if not os.path.exists(DB_PATH):
        print(f"Session database not found: {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Get all sessions with their first user message, excluding tiny (0-1 turn) sessions
    cur.execute("""
        SELECT
            s.id,
            s.cwd,
            s.summary,
            s.created_at,
            s.updated_at,
            t.user_message AS first_message
        FROM sessions s
        LEFT JOIN turns t ON t.session_id = s.id AND t.turn_index = 0
        WHERE (SELECT COUNT(*) FROM turns t2 WHERE t2.session_id = s.id) >= 2
        ORDER BY COALESCE(s.updated_at, s.created_at) DESC
    """)

    rows = cur.fetchall()

    if not rows:
        conn.close()
        print("No sessions found.", file=sys.stderr)
        sys.exit(1)

    home = str(Path.home())
    session_state_prefix = str(Path.home() / ".copilot" / "session-state")

    # For sessions with no cwd, infer project root from file paths
    null_cwd_ids = [r["id"] for r in rows if not r["cwd"]]
    inferred_cwd: Dict[str, str] = {}
    if null_cwd_ids:
        placeholders = ",".join("?" for _ in null_cwd_ids)
        cur.execute(
            f"SELECT session_id, file_path FROM session_files WHERE session_id IN ({placeholders})",
            null_cwd_ids,
        )
        files_by_session: Dict[str, List[str]] = {}
        for sf in cur.fetchall():
            path = sf["file_path"]
            if path.startswith(session_state_prefix) or "/.copilot/" in path:
                continue
            files_by_session.setdefault(sf["session_id"], []).append(path)

        for sid, paths in files_by_session.items():
            try:
                common = os.path.commonpath(paths)
                if not os.path.isdir(common):
                    common = os.path.dirname(common)
                root = _find_project_root(common, home)
                if root:
                    inferred_cwd[sid] = root
            except ValueError:
                pass

    conn.close()

    # Group by cwd (using inferred cwd for sessions without one)
    groups: dict[str, list] = {}
    for row in rows:
        cwd = row["cwd"] or inferred_cwd.get(row["id"]) or "(no directory)"
        groups.setdefault(cwd, []).append(row)

    # Sort groups by most recent session
    sorted_groups = sorted(
        groups.items(),
        key=lambda g: max(r["updated_at"] or r["created_at"] or "" for r in g[1]),
        reverse=True,
    )

    # Output format: <display>\t<TYPE>\t<cwd>\t<session-id>
    # TYPE is DIR (group header) or SESSION (individual session)
    for cwd, sessions in sorted_groups:
        short = cwd.replace(home, "~") if cwd != "(no directory)" else cwd
        count = len(sessions)
        is_collapsed = cwd in collapsed
        arrow = col("▸", YELLOW) if is_collapsed else col("▾", YELLOW)

        print(f"  {arrow} {col(short, CYAN)}  {col(f'({count})', GRAY)}\tDIR\t{cwd}\t")

        if is_collapsed:
            continue

        for row in sessions:
            sid = row["id"]
            ts = row["updated_at"] or row["created_at"] or ""
            a = age(ts)
            summary = row["summary"] or ""
            first_msg = (row["first_message"] or "").strip()

            # Prefer summary, fall back to first message
            label = summary or first_msg
            # Clean up: collapse whitespace, strip leading tags
            label = " ".join(label.split())
            if label.startswith("<") and len(label) > 200:
                label = ""

            if len(label) > 65:
                label = label[:63] + "…"
            if not label:
                label = col("(empty)", GRAY)

            age_s = col(f"[{a:>3}]", MAGENTA)
            display_cwd = cwd if cwd != "(no directory)" else home

            print(f"    {age_s}  {col(label, WHITE)}\tSESSION\t{display_cwd}\t{sid}")


if __name__ == "__main__":
    main()
