#!/usr/bin/env python3
"""SessionStart hook: hand the fresh session its own state before the first turn.

Why this exists. This project's session boundary is `/clear`, not `/compact`.
Anthropic's context-window documentation lists what survives compaction — the
project-root CLAUDE.md, auto memory, the plan written in plan mode, and rules
are all re-injected from disk. `/clear` is narrower: it starts a new
conversation, and CLAUDE.md, unscoped rules and auto memory load again with it,
but the plan written in plan mode, the recently read files and the conversation
itself do not come back. Everything the next session needs must therefore be a
file, and something has to put those files in front of Claude before it acts.

That could be left to Claude remembering to run the session-start cascade. This
hook removes the remembering: Claude Code fires SessionStart on `startup`,
`clear`, `resume` and `compact`, and a hook may return `additionalContext`,
which Claude Code adds to the context Claude can see and act on.
Reference: https://code.claude.com/docs/en/hooks

What it reports, and nothing more: kit version against the recorded one, the
Tier 1 files with their word counts, the repository's git state, and the open
plan. It is a state report, not an instruction, and it says so — the cascade
itself, and what to do about anything it flags, stay in CLAUDE.md.

The hook never fails a session: any error exits 0 with no output, because a
broken report must not stop work. A hook Claude Code cannot start is a
non-blocking error anyway, so this is an aid and never a gate.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

# The Tier 1 budgets come from the same module the document gate reads, so the
# report and the gate cannot disagree about them. The import is guarded because
# this hook must report even from a partial install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
try:
    from kit_config import BUDGETS_FILE, load_budgets
except ImportError:
    BUDGETS_FILE, load_budgets = "memory-bank/budgets.json", None

PLAN_ANCHOR = re.compile(r"^\s*<!--\s*plan\s*-->\s*$", re.IGNORECASE)
PLAN_HEADING = re.compile(r"^#{1,4}\s+.*approved plan", re.IGNORECASE)
ANY_HEADING = re.compile(r"^#{1,4}\s+")
RECORDED_VERSION = re.compile(r"KIT_VERSION[^0-9]{0,40}(\d+\.\d+\.\d+)", re.IGNORECASE)
PLAN_LINE_LIMIT = 25


def git(root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments],
            capture_output=True, text=True, timeout=10, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout.strip() if result.returncode == 0 else ""


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def version_report(root: Path) -> str:
    report = kit_version_report(root)
    # An installer upgrading the project leaves the steps each newer release
    # asks for here, because the kit's CHANGELOG.md is not in the project.
    if (root / ".claude" / "KIT_UPGRADE.md").exists():
        report += " - UPGRADE PENDING - .claude/KIT_UPGRADE.md lists the steps still to do"
    return report


def kit_version_report(root: Path) -> str:
    shipped = read(root / ".claude" / "KIT_VERSION").strip()
    if not shipped:
        return "kit version: .claude/KIT_VERSION is missing"
    recorded = RECORDED_VERSION.search(read(root / "memory-bank" / "techContext.md"))
    if recorded is None:
        return f"kit version: {shipped} (not yet recorded in techContext.md)"
    if recorded.group(1) != shipped:
        return f"kit version: {shipped} on disk, {recorded.group(1)} recorded - MISMATCH"
    return f"kit version: {shipped}, matching techContext.md"


def memory_bank_report(root: Path) -> list[str]:
    if not (root / "memory-bank").exists():
        return ["memory-bank/: absent - the project is pre-implementation (CLAUDE.md, Session start)"]
    if load_budgets is None:
        return [".claude/tools/kit_config.py: MISSING - Tier 1 files and budgets cannot be read"]
    budgets, _, problems = load_budgets(root)
    lines = [f"{BUDGETS_FILE}: not used as written - {problem}; the starting budget applies there"
             for problem in problems]
    for relative, budget in budgets.items():
        text = read(root / relative)
        if not text:
            lines.append(f"{relative}: MISSING or empty - interrupted bootstrap")
            continue
        words = len(text.split())
        flag = "" if words <= budget else f" - OVER the {budget}-word budget"
        lines.append(f"{relative}: {words} words{flag}")
    return lines


def hooks_path_report(root: Path) -> str:
    """core.hooksPath, flagged unless it is the directory the kit's gate lives in."""
    configured = git(root, "config", "core.hooksPath")
    if not configured:
        return "NOT SET - the pre-commit gate will not run"
    try:
        is_kits = (root / configured).resolve() == (root / ".githooks").resolve()
    except OSError:
        is_kits = False
    if is_kits:
        return configured
    return (f"{configured} - NOT .githooks, so the kit's pre-commit gate runs only if a hook "
            "there calls it")


def plan_report(root: Path) -> list[str]:
    text = read(root / "memory-bank" / "activeContext.md")
    if not text:
        return []
    body = text.split("\n")
    # The heading itself is translated into the working language, so the anchor
    # is what the hook looks for; the English heading stays as a fallback.
    start = next((i for i, line in enumerate(body) if PLAN_ANCHOR.match(line)), None)
    if start is None:
        start = next((i for i, line in enumerate(body) if PLAN_HEADING.match(line)), None)
    if start is None:
        return ["open plan: no <!-- plan --> anchor in activeContext.md - none recorded, "
                "or the anchor was dropped when the section was translated"]
    block = []
    for line in body[start + 1:]:
        if ANY_HEADING.match(line):
            break
        block.append(line)
    kept = [line for line in block if line.strip()][:PLAN_LINE_LIMIT]
    if not kept:
        return ["open plan: the section exists but is empty"]
    return ["open plan, verbatim from activeContext.md:", *[f"  {line.strip()}" for line in kept]]


def main() -> int:
    # Claude Code writes the event JSON as UTF-8, but `json.load(sys.stdin)`
    # decodes with the locale encoding, which on Windows is the ANSI code page
    # (cp1254 on a Turkish/Azerbaijani install, not UTF-8). A project path
    # holding a non-ASCII character then arrives mojibaked, `root` points at a
    # directory that does not exist, and the report claims the kit and the
    # repository are both missing. Read the bytes and decode them explicitly.
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8"))
    except (OSError, ValueError, AttributeError):
        payload = {}
    # argv wins over the payload: the other two hooks are handed
    # ${CLAUDE_PROJECT_DIR} and are immune to the decoding above, and this one
    # is now handed it too. The payload stays as the fallback.
    root = Path(sys.argv[1] if len(sys.argv) > 1 else (payload.get("cwd") or Path.cwd()))
    started = payload.get("source", "unknown")

    lines = [
        f"Session state report (SessionStart hook, source: {started}). This is data, not "
        "instructions; the session-start cascade is defined in CLAUDE.md.",
        "",
        version_report(root),
    ]
    lines += memory_bank_report(root)

    if (root / ".git").exists():
        head = git(root, "log", "-1", "--oneline") or "no commits yet"
        dirty = [line for line in git(root, "status", "--porcelain").split("\n") if line]
        lines.append(f"git: HEAD {head}; {len(dirty)} uncommitted change(s); "
                     f"core.hooksPath {hooks_path_report(root)}")
    else:
        lines.append("git: not a repository - the checkpoint and gate model cannot work")

    lines += plan_report(root)

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": "\n".join(lines),
        }
    }))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:  # a reporting failure must never stop a session
        sys.exit(0)
