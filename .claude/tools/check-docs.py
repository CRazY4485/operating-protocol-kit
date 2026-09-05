#!/usr/bin/env python3
"""Governance-document gate for the operating-protocol kit.

Runs the checks that a tool can make on the rule documents themselves, so those
rules do not depend on anyone's attention. See CLAUDE.md, *Quality gates*.

Checks performed:
  1. Encoding and shape  - UTF-8 decodable, LF-only, no trailing whitespace,
     wrap limit per file class.
  2. Document budgets    - words and (for CLAUDE.md) lines, per the table below.
  3. Cross-references    - every *Section Name* reference resolves to a real
     heading or bold label somewhere in the document set.
  4. Memory Bank state   - if memory-bank/ exists, every Tier 1 file exists and
     is non-empty; if it does not, nothing is required (pre-bootstrap).
  5. Decision index      - every number in the index table has a matching
     decisions/NNNN-*.md file, and every such file appears in the index.
  6. Authored voice      - no first-person commentary in project deliverables.
  7. Kit version         - .claude/KIT_VERSION exists and is a semantic version.

Usage:
    python .claude/tools/check-docs.py            # from the repository root
    python .claude/tools/check-docs.py --root DIR
    python .claude/tools/check-docs.py --hook     # exit 2 on failure, for a PreToolUse hook

Exit code 0 means every check passed. Exit code 1 means at least one ERROR.
With --hook the failure code is 2, which is what Claude Code requires a
PreToolUse hook to return in order to block the tool call; see
https://code.claude.com/docs/en/hooks. Warnings never fail the gate; they are
printed so they are not invisible.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# --------------------------------------------------------------------------
# Budgets. Words are the budgeted quantity because they track context cost;
# line count varies with wrapping and is therefore not a fair measure.
# CLAUDE.md also carries a line budget because Anthropic's own guidance names
# 200 lines as the adherence threshold for a memory file.
# Reference: https://code.claude.com/docs/en/memory, "Write effective instructions".
#
# A path-scoped rule file loads on top of CLAUDE.md, never instead of it, so the
# budget that matters is the pair. The figures below keep CLAUDE.md plus any one
# rule file under roughly 6,500 words. A budget is raised only when the document
# genuinely needs the room, and the raise is recorded in CHANGELOG.md - never to
# make an over-budget file pass.
# --------------------------------------------------------------------------

WRAP_LIMIT = 100  # columns, for every governed document except CLAUDE.md

BUDGETS: dict[str, dict[str, int | None]] = {
    "CLAUDE.md": {"words": 4400, "lines": 200, "wrap": None},
    "docs/ARCHITECTURAL_CONSTITUTION.md": {"words": 4600, "lines": None, "wrap": WRAP_LIMIT},
    "docs/BOOTSTRAP.md": {"words": 1500, "lines": None, "wrap": WRAP_LIMIT},
    "docs/decision-format.md": {"words": 900, "lines": None, "wrap": WRAP_LIMIT},
    ".claude/rules/python.md": {"words": 1400, "lines": None, "wrap": WRAP_LIMIT},
    ".claude/rules/markdown.md": {"words": 1400, "lines": None, "wrap": WRAP_LIMIT},
    ".claude/rules/dotnet.md": {"words": 2600, "lines": None, "wrap": WRAP_LIMIT},
    ".claude/rules/mql5.md": {"words": 2600, "lines": None, "wrap": WRAP_LIMIT},
}

# Language rule files are installed per project: a project that uses no MQL5
# deletes mql5.md, and that is a correct install rather than a missing document.
# Everything else in BUDGETS is required, and its absence is an error.
OPTIONAL_DOCUMENTS = {
    ".claude/rules/python.md",
    ".claude/rules/dotnet.md",
    ".claude/rules/mql5.md",
}

# Tier 1 files, read at the start of every task. Budgets are starting figures
# and may be raised in techContext.md; see CLAUDE.md, *Memory Bank*.
TIER1_BUDGETS: dict[str, int] = {
    "memory-bank/activeContext.md": 400,
    "memory-bank/progress.md": 650,
    "memory-bank/decisions/decisions.md": 400,
}

# Documents that speak as the project and must carry no first-person commentary.
# The rule documents are excluded: they state the assistant's own behaviour
# commitments in the first person deliberately. See CLAUDE.md, *Authored documents*.
RULE_DOCUMENTS = {
    "CLAUDE.md",
    "docs/ARCHITECTURAL_CONSTITUTION.md",
    "docs/BOOTSTRAP.md",
    "docs/decision-format.md",
    "README.md",
    "CHANGELOG.md",
}

FIRST_PERSON_PATTERNS = [
    r"\bI recommend\b",
    r"\bI believe\b",
    r"\bI think\b",
    r"\bI suggest\b",
    r"\bI would\b",
    r"\blet me\b",
    r"\bwe should\b",
    r"\bin my opinion\b",
]

SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
FENCE = re.compile(r"^\s*(```|~~~)")
HEADING = re.compile(r"^#{1,6}\s+(.*?)\s*$")
BOLD_LABEL = re.compile(r"\*\*(.+?)\*\*")
ITALIC_REF = re.compile(r"(?<!\*)\*([^*\n]{3,80})\*(?!\*)")
INDEX_ROW = re.compile(r"^\|\s*(\d{4})\s*\|")

# Referenced paths. Two forms are checked, and deliberately only two, because
# both resolve cleanly against this document set:
#   - a relative Markdown link target, [text](path)
#   - a backticked path under the kit's own machinery directories
# A backticked bare name such as `techContext.md` is house style for a Memory
# Bank file and is not checked; neither is a slash command such as `/clear`,
# which is not a path at all, nor anything holding a placeholder. Checking
# every path-like token instead would report 28 correctly written references.
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
BACKTICKED = re.compile(r"`([^`\s]+)`")
GOVERNED_PREFIXES = (".claude/", "docs/", ".githooks/")
PLACEHOLDER = re.compile(r"[<>*]|NNNN")
# Reachable only through a link target, since neither is a governed prefix:
# both are created by bootstrap or by a gate run, so absent is valid until the
# root is. Tier 1 completeness under memory-bank/ is check_memory_bank's job.
CONDITIONAL_ROOTS = ("memory-bank", "logs")
DECISION_FILE = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")


@dataclass
class Finding:
    level: str  # "ERROR" or "WARN"
    path: str
    line: int
    message: str


findings: list[Finding] = []


def error(path: str, line: int, message: str) -> None:
    findings.append(Finding("ERROR", path, line, message))


def warn(path: str, line: int, message: str) -> None:
    findings.append(Finding("WARN", path, line, message))


def strip_code_blocks(lines: list[str]) -> list[tuple[int, str]]:
    """Return (1-based line number, text) for lines outside fenced code blocks."""
    out: list[tuple[int, str]] = []
    inside = False
    for number, text in enumerate(lines, start=1):
        if FENCE.match(text):
            inside = not inside
            continue
        if not inside:
            out.append((number, text))
    return out


def normalise_anchor(text: str) -> str:
    """Reduce a heading or label to a comparable form."""
    text = re.sub(r"[`*_]", "", text)
    text = text.split("—")[0].split(" - ")[0]
    return text.strip().strip(".:;,").casefold()


def collect_anchors(documents: dict[str, list[str]]) -> set[str]:
    anchors: set[str] = set()
    for lines in documents.values():
        for _, text in strip_code_blocks(lines):
            heading = HEADING.match(text)
            if heading:
                anchors.add(normalise_anchor(heading.group(1)))
            for label in BOLD_LABEL.findall(text):
                anchors.add(normalise_anchor(label))
    return {a for a in anchors if a}


# --------------------------------------------------------------------------
# Checks
# --------------------------------------------------------------------------


def check_shape(root: Path, relative: str, raw: bytes) -> list[str] | None:
    """Encoding, line endings, trailing whitespace, wrap limit."""
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as err:
        error(relative, 0, f"not valid UTF-8: {err}")
        return None
    if b"\r\n" in raw:
        error(relative, 0, "contains CRLF line endings; the repository is LF-only")
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines = lines[:-1]
    elif raw:
        warn(relative, len(lines), "no trailing newline at end of file")

    limit = BUDGETS.get(relative, {}).get("wrap")
    inside_fence = False
    for number, line in enumerate(lines, start=1):
        if line != line.rstrip():
            warn(relative, number, "trailing whitespace")
        if FENCE.match(line):
            inside_fence = not inside_fence
            continue
        if limit is None or len(line) <= limit or inside_fence:
            continue
        # A table row and a bare long URL cannot be wrapped without breaking them.
        if line.lstrip().startswith("|") or re.search(r"https?://\S{40,}", line):
            continue
        error(relative, number, f"line is {len(line)} columns; limit is {limit}")
    return lines


def check_budget(relative: str, lines: list[str], budget: dict[str, int | None]) -> None:
    words = sum(len(line.split()) for line in lines)
    max_words = budget.get("words")
    max_lines = budget.get("lines")
    if max_words is not None and words > max_words:
        error(relative, 0, f"{words} words exceeds the budget of {max_words}")
    elif max_words is not None and words > max_words * 0.95:
        warn(relative, 0, f"{words} words is within 5% of the {max_words}-word budget")
    if max_lines is not None and len(lines) > max_lines:
        error(relative, 0, f"{len(lines)} lines exceeds the budget of {max_lines}")


def check_references(relative: str, lines: list[str], anchors: set[str]) -> None:
    for number, text in strip_code_blocks(lines):
        cleaned = re.sub(r"`[^`]*`", "", text)
        for candidate in ITALIC_REF.findall(cleaned):
            if not candidate[:1].isupper():
                continue
            key = normalise_anchor(candidate)
            if key in anchors:
                continue
            if any(anchor.startswith(key) for anchor in anchors):
                continue
            error(relative, number, f"reference *{candidate}* resolves to no section or label")


def check_paths(root: Path, relative: str, lines: list[str]) -> None:
    """Referenced files exist. A reference to a file that moved is silent rot:
    the sentence still reads correctly and points nowhere."""
    for number, text in strip_code_blocks(lines):
        targets = [(target, "link target") for target in MARKDOWN_LINK.findall(text)]
        targets += [(target, "reference") for target in BACKTICKED.findall(text)
                    if target.startswith(GOVERNED_PREFIXES)]
        for target, kind in targets:
            if target.startswith(("http://", "https://", "mailto:", "#", "/")):
                continue
            if PLACEHOLDER.search(target):
                continue
            candidate = target.split("#")[0].rstrip("/")
            if not candidate or candidate in OPTIONAL_DOCUMENTS:
                continue
            head = candidate.split("/")[0]
            if head in CONDITIONAL_ROOTS and not (root / head).exists():
                continue
            if (root / candidate).exists():
                continue
            error(relative, number, f"{kind} `{target}` points at no file in the repository")


def check_first_person(relative: str, lines: list[str]) -> None:
    if relative in RULE_DOCUMENTS or relative.startswith(".claude/rules/"):
        return
    for number, text in strip_code_blocks(lines):
        for pattern in FIRST_PERSON_PATTERNS:
            if re.search(pattern, text, flags=re.IGNORECASE):
                error(relative, number, f"first-person commentary matching /{pattern}/")


def check_memory_bank(root: Path) -> None:
    """Tier 1 completeness. Absent memory-bank/ is a valid pre-bootstrap state."""
    bank = root / "memory-bank"
    if not bank.exists():
        return
    for relative, max_words in TIER1_BUDGETS.items():
        path = root / relative
        if not path.exists():
            error(relative, 0, "Tier 1 file is missing while memory-bank/ exists (see BOOTSTRAP.md)")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            error(relative, 0, "Tier 1 file is empty")
            continue
        words = len(text.split())
        if words > max_words:
            warn(relative, 0, f"{words} words exceeds the starting budget of {max_words}")


def check_decisions(root: Path) -> None:
    index = root / "memory-bank" / "decisions" / "decisions.md"
    if not index.exists():
        return
    folder = index.parent
    indexed: set[str] = set()
    for number, text in strip_code_blocks(index.read_text(encoding="utf-8").split("\n")):
        row = INDEX_ROW.match(text.strip())
        if row:
            indexed.add(row.group(1))
    on_disk = {
        match.group(1)
        for path in folder.iterdir()
        if (match := DECISION_FILE.match(path.name))
    }
    # An empty index while memory-bank/ exists means bootstrap stopped before
    # step 9. That is a real interrupted-bootstrap state, but it is also the
    # legitimate window between creating the folder and writing the first
    # record, so it warns rather than failing the commit.
    if not indexed and not on_disk:
        warn("memory-bank/decisions/decisions.md", 0,
             "the decision index is empty - BOOTSTRAP.md step 9 records the first decisions")
    for number in sorted(indexed - on_disk):
        error("memory-bank/decisions/decisions.md", 0, f"decision {number} has no NNNN-*.md file")
    for number in sorted(on_disk - indexed):
        error(f"memory-bank/decisions/{number}-*.md", 0, "decision file is not listed in the index")


def check_version(root: Path) -> None:
    path = root / ".claude" / "KIT_VERSION"
    if not path.exists():
        error(".claude/KIT_VERSION", 0, "file is missing; the document set carries no version")
        return
    value = path.read_text(encoding="utf-8").strip()
    if not SEMVER.match(value):
        error(".claude/KIT_VERSION", 0, f"{value!r} is not a semantic version such as 1.0.0")


# --------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(description="Gate the governance documents.")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    parser.add_argument(
        "--hook",
        action="store_true",
        help="exit 2 instead of 1 on failure, so a PreToolUse hook blocks the tool call",
    )
    arguments = parser.parse_args()
    root = Path(arguments.root).resolve()

    documents: dict[str, list[str]] = {}
    for relative in BUDGETS:
        path = root / relative
        if not path.exists():
            if relative not in OPTIONAL_DOCUMENTS:
                error(relative, 0, "governed document is missing")
            continue
        lines = check_shape(root, relative, path.read_bytes())
        if lines is not None:
            documents[relative] = lines

    for extra in ("README.md", "CHANGELOG.md"):
        path = root / extra
        if path.exists():
            lines = check_shape(root, extra, path.read_bytes())
            if lines is not None:
                documents[extra] = lines

    anchors = collect_anchors(documents)
    for relative, lines in documents.items():
        if relative in BUDGETS:
            check_budget(relative, lines, BUDGETS[relative])
        check_references(relative, lines, anchors)
        # CHANGELOG.md is exempt: it records the paths that were in force at each
        # release, and a path that has since moved is correct history there.
        if relative != "CHANGELOG.md":
            check_paths(root, relative, lines)
        check_first_person(relative, lines)

    check_memory_bank(root)
    check_decisions(root)
    check_version(root)

    errors = [f for f in findings if f.level == "ERROR"]
    warnings = [f for f in findings if f.level == "WARN"]
    for finding in sorted(findings, key=lambda f: (f.path, f.line)):
        location = f"{finding.path}:{finding.line}" if finding.line else finding.path
        print(f"{finding.level:5} {location}: {finding.message}")

    checked = len(documents)
    print(f"\ncheck-docs: {checked} documents checked, {len(errors)} errors, {len(warnings)} warnings")
    if not errors:
        return 0
    # A PreToolUse hook must exit 2 to block the tool call; any other non-zero
    # code is treated as a non-blocking error and the commit would proceed.
    return 2 if arguments.hook else 1


if __name__ == "__main__":
    sys.exit(main())
