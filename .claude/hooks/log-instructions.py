#!/usr/bin/env python3
"""InstructionsLoaded hook: record which instruction files actually loaded.

A rule file that does not load is not a rule, and its absence is silent: no
error, no warning, just guidance that never applies. This hook turns that
invisible failure into a file the owner can open.

Claude Code fires InstructionsLoaded for every CLAUDE.md and .claude/rules/*.md
it loads, at session start and whenever a path-scoped rule matches a file being
read. The event JSON arrives on stdin with `load_reason` and `file_path`.
Reference: https://code.claude.com/docs/en/hooks

Written to: logs/instructions-loaded.log (git-ignored, UTF-8, one line per load)

The hook never blocks: any failure here exits 0 so a logging problem cannot
stop the session.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

LOG_RELATIVE = Path("logs") / "instructions-loaded.log"


def main() -> int:
    try:
        root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
        payload = json.load(sys.stdin)
    except (OSError, ValueError, IndexError):
        return 0

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    session = str(payload.get("session_id", "unknown"))[:8]
    reason = payload.get("load_reason", "unknown")
    loaded = payload.get("file_path", "unknown")
    try:
        loaded = str(Path(loaded).resolve().relative_to(Path(root).resolve()))
    except (ValueError, TypeError, OSError):
        loaded = str(loaded)  # outside the project root, or an unresolvable path

    line = f"{stamp} session={session} reason={reason} file={loaded}\n"
    try:
        log = root / LOG_RELATIVE
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(line)
    except OSError:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
