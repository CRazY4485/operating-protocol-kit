#!/usr/bin/env python3
"""Governance-document gate for the operating-protocol kit.

Runs the checks that a tool can make on the rule documents themselves, so those
rules do not depend on anyone's attention. See CLAUDE.md, *Quality gates*.

Checks performed:
  1. Encoding and shape  - UTF-8 decodable, LF-only, no trailing whitespace,
     wrap limit per file class. Covers every template in docs/templates/.
  2. Document budgets    - words and (for CLAUDE.md) lines, per the table below;
     a rule file the kit does not ship gets DEFAULT_RULE_BUDGET; and no Tier 1
     template is over the budget of the file bootstrap makes of it.
  3. Cross-references    - every *Section Name* reference resolves to a real
     heading or bold label somewhere in the document set.
  4. Referenced paths    - a Markdown link target, resolved against the linking
     document's directory, and a backticked path under a governed prefix exist.
  5. Memory Bank state   - if memory-bank/ exists, every Tier 1 file exists, is
     non-empty and is within its budget (a warning), and memory-bank/budgets.json,
     if present, is usable; if it does not, nothing is required (pre-bootstrap).
  6. Decision index      - every number in the index table has a matching
     decisions/NNNN-*.md file, and every such file appears in the index.
  7. Templates           - every template bootstrap copies exists, and the
     activeContext.md template keeps its <!-- plan --> and <!-- verified --> anchors.
  8. Evidence            - the last verified change in activeContext.md cites a
     gate log with its SHA-256 (a warning when it does not), and when that log
     is on this machine, the hash matches it.
  9. Kit version         - .claude/KIT_VERSION exists and is a semantic version.
 10. Client settings     - .claude/settings.json parses, and the interpreter its
     Python hooks name starts on this machine (a warning when it does not).
 11. Gate list          - .claude/gates.json, if present, is one run-gates.py can
     use, so a broken list is refused at commit rather than found at the next run.
 12. Unmerged kit files  - a *.kit-new an installer left beside a file of the
     same name (a warning).

The ban on first-person commentary in project deliverables is not checked here:
deliverables are written in the working language, and a phrase list covers one
language. It is held by review; see .claude/rules/markdown.md.

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
import hashlib
import json
import os
import posixpath
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from kit_config import BUDGETS_FILE, GATES_FILE, TIER1_BUDGETS, load_budgets, load_gates

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

# A rule file for a language the kit does not ship - written from
# docs/templates/language-rules.md - is gated like the shipped ones, under this
# budget: with CLAUDE.md's 4 400 words it keeps the pair under 6 500.
RULES = ".claude/rules"
DEFAULT_RULE_BUDGET: dict[str, int | None] = {"words": 2000, "lines": None, "wrap": WRAP_LIMIT}

# Language rule files are installed per project: a project that uses no MQL5
# deletes mql5.md, and that is a correct install rather than a missing document.
# Everything else in BUDGETS is required, and its absence is an error.
OPTIONAL_DOCUMENTS = {
    ".claude/rules/python.md",
    ".claude/rules/dotnet.md",
    ".claude/rules/mql5.md",
}

# Tier 1 files and their budgets live in kit_config.py beside this file, which
# the SessionStart hook reads too; a project sets its own in memory-bank/budgets.json.

# Templates are copied into every project and, at bootstrap, into memory-bank/,
# so they are held to the same shape as the documents that name them.
TEMPLATES = "docs/templates"
REQUIRED_TEMPLATES = (
    "docs/templates/activeContext.md",
    "docs/templates/decisions.md",
    "docs/templates/subagent-brief.md",
    "docs/templates/superseded.md",
)
# The Tier 1 file each template becomes at bootstrap (BOOTSTRAP.md step 5). A
# template over that file's budget starts every bootstrapped project over it,
# before a single fact has been written.
TEMPLATE_TARGETS = {
    "docs/templates/activeContext.md": "memory-bank/activeContext.md",
    "docs/templates/decisions.md": "memory-bank/decisions/decisions.md",
}
# The SessionStart hook finds the open plan by this anchor. It must match
# PLAN_ANCHOR in .claude/hooks/session-start.py exactly; a test holds them equal.
PLAN_TEMPLATE = "docs/templates/activeContext.md"
PLAN_ANCHOR = re.compile(r"^\s*<!--\s*plan\s*-->\s*$", re.IGNORECASE)

# The section a Record fills with the change it accepted, found by this anchor
# because its heading is translated. It cites the gate log that proved the
# change and the log's SHA-256, both as run-gates.py prints them.
ACTIVE_CONTEXT = "memory-bank/activeContext.md"
VERIFIED_ANCHOR = re.compile(r"^\s*<!--\s*verified\s*-->\s*$", re.IGNORECASE)
GATE_LOG = re.compile(r"logs/gate-\d{8}T\d{6}Z(?:-\d+)?\.log")
SHA256 = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{64}(?![0-9A-Fa-f])")
UNMERGED_SUFFIX = ".kit-new"

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
# Files the project creates rather than the kit ships, so a reference to one is
# valid before it exists. BOOTSTRAP.md step 6 creates the gate list.
PROJECT_FILES = {GATES_FILE}

# Directories kept out of the "did you mean" corpus below. memory-bank/ is the
# one that matters: the house style names its files by shorthand, so
# `decisions/decisions.md` in CLAUDE.md is a path-suffix of the real
# memory-bank/decisions/decisions.md the moment a project bootstraps. With that
# tree in the corpus the gate would turn red on kit text nobody had touched,
# and only after an install had already gone green.
CORPUS_EXCLUDED = {".git", "memory-bank", "logs", "__pycache__", "node_modules"}
DECISION_FILE = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")

SETTINGS = ".claude/settings.json"
# Run with `-c`, so the answer is the interpreter's own rather than its name's:
# a Microsoft Store alias for python3 exists on PATH and still fails this.
PYTHON_PROBE = "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
PROBE_TIMEOUT_SECONDS = 15


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


def check_shape(relative: str, raw: bytes, limit: int | None) -> list[str] | None:
    """Encoding, line endings, trailing whitespace, and a wrap limit unless it is None."""
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


def collect_repository_files(root: Path) -> list[str]:
    """Every file an incomplete reference could actually have meant."""
    found: list[str] = []
    for folder, folders, names in os.walk(root):
        folders[:] = [name for name in folders if name not in CORPUS_EXCLUDED]
        base = Path(folder).relative_to(root)
        found.extend((base / name).as_posix() for name in names)
    return sorted(found)  # sorted so the reported suggestion is deterministic


def check_paths(root: Path, relative: str, lines: list[str], corpus: list[str]) -> None:
    """Referenced files exist. A reference to a file that moved is silent rot:
    the sentence still reads correctly and points nowhere."""
    for number, text in strip_code_blocks(lines):
        backticked = BACKTICKED.findall(text)
        # `required` targets must resolve. The rest are checked only for the
        # incomplete form — a real file written without its directory prefix —
        # and stay silent otherwise, which is what keeps bare shorthand and
        # example identifiers out of the findings.
        targets = [(target, "link target", True) for target in MARKDOWN_LINK.findall(text)]
        targets += [(target, "reference", True) for target in backticked
                    if target.startswith(GOVERNED_PREFIXES)]
        targets += [(target, "reference", False) for target in backticked
                    if "/" in target and not target.startswith(GOVERNED_PREFIXES)]
        for target, kind, required in targets:
            if target.startswith(("http://", "https://", "mailto:", "#", "/")):
                continue
            if PLACEHOLDER.search(target):
                continue
            candidate = target.split("#")[0].rstrip("/")
            if not candidate:
                continue
            # A Markdown link resolves against the linking document's directory,
            # as GitHub and every editor resolve it; a backticked path is written
            # from the project root by house style.
            base = posixpath.dirname(relative) if kind == "link target" else ""
            resolved = posixpath.normpath(posixpath.join(base, candidate))
            if resolved == ".." or resolved.startswith("../"):
                error(relative, number, f"{kind} `{target}` points outside the repository")
                continue
            if resolved in OPTIONAL_DOCUMENTS or resolved in PROJECT_FILES:
                continue
            head = resolved.split("/")[0]
            if head in CONDITIONAL_ROOTS and not (root / head).exists():
                continue
            if (root / resolved).exists():
                continue
            complete = [f for f in corpus if f.endswith("/" + candidate)]
            if complete:
                real = posixpath.relpath(complete[0], base) if base else complete[0]
                also = f" (and {len(complete) - 1} more)" if len(complete) > 1 else ""
                error(relative, number,
                      f"{kind} `{target}` is incomplete; the file is at `{real}`{also}")
            elif required:
                where = f", resolved from `{base}/`" if base else ""
                error(relative, number,
                      f"{kind} `{target}` points at no file in the repository{where}")


def check_templates(root: Path, documents: dict[str, list[str]]) -> None:
    for template in REQUIRED_TEMPLATES:
        if not (root / template).exists():
            error(template, 0, "template is missing; bootstrap and delegation copy it")
    for template, target in TEMPLATE_TARGETS.items():
        lines = documents.get(template)
        if lines is None:
            continue
        words = sum(len(line.split()) for line in lines)
        budget = TIER1_BUDGETS[target]
        if words > budget:
            error(template, 0,
                  f"{words} words is over the {budget}-word budget of {target}, "
                  "which bootstrap copies it into")
    lines = documents.get(PLAN_TEMPLATE)
    if lines is not None and not any(PLAN_ANCHOR.match(line) for line in lines):
        error(PLAN_TEMPLATE, 0,
              "no `<!-- plan -->` anchor; the SessionStart hook finds the open plan by it")
    if lines is not None and not any(VERIFIED_ANCHOR.match(line) for line in lines):
        error(PLAN_TEMPLATE, 0,
              "no `<!-- verified -->` anchor; the gate finds the last verified change by it")


def check_last_verified_change(root: Path) -> None:
    """The accepted change cites the gate log that proved it, and that log still says so."""
    path = root / ACTIVE_CONTEXT
    if not path.exists():
        return  # check_memory_bank reports a missing Tier 1 file
    lines = path.read_text(encoding="utf-8", errors="replace").split("\n")
    start = next((i for i, line in enumerate(lines) if VERIFIED_ANCHOR.match(line)), None)
    if start is None:
        warn(ACTIVE_CONTEXT, 0, "no `<!-- verified -->` anchor, so the last verified change "
             f"cannot be checked against its gate log; {PLAN_TEMPLATE} carries it")
        return
    section = []
    for line in lines[start + 1:]:
        if HEADING.match(line):
            break
        section.append(line)
    text = "\n".join(section)
    log, digest = GATE_LOG.search(text), SHA256.search(text)
    if log is None or digest is None:
        warn(ACTIVE_CONTEXT, start + 1, "the last verified change cites no gate log with its "
             "SHA-256, as run-gates.py prints them; see CLAUDE.md, Quality gates")
        return
    # Logs are git-ignored and machine-local. On another clone, or in CI, the
    # file is absent and the citation is taken as written.
    log_path = root / log.group(0)
    if not log_path.is_file():
        return
    actual = hashlib.sha256(log_path.read_bytes()).hexdigest()
    if actual != digest.group(0).lower():
        error(ACTIVE_CONTEXT, start + 1,
              f"sha256 {digest.group(0)} does not match {log.group(0)}, whose sha256 is "
              f"{actual}; the record cites evidence the log does not hold")


def check_gate_list(root: Path) -> None:
    for problem in load_gates(root)[1]:
        error(GATES_FILE, 0, problem)


def check_unmerged(corpus: list[str]) -> None:
    """An installer never overwrites a file; it leaves the kit's version beside it."""
    for relative in corpus:
        if relative.endswith(UNMERGED_SUFFIX):
            original = relative[: -len(UNMERGED_SUFFIX)]
            warn(relative, 0, f"unmerged kit file; merge it into {original}, then delete it")


def check_memory_bank(root: Path) -> None:
    """Tier 1 completeness. Absent memory-bank/ is a valid pre-bootstrap state."""
    bank = root / "memory-bank"
    if not bank.exists():
        return
    budgets, project_set, problems = load_budgets(root)
    for problem in problems:
        error(BUDGETS_FILE, 0, problem)
    for relative, max_words in budgets.items():
        path = root / relative
        if not path.exists():
            error(relative, 0, "Tier 1 file is missing while memory-bank/ exists (see BOOTSTRAP.md)")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if not text.strip():
            error(relative, 0, "Tier 1 file is empty")
            continue
        words = len(text.split())
        if words <= max_words:
            continue
        if relative in project_set:
            warn(relative, 0, f"{words} words exceeds its budget of {max_words}, set in {BUDGETS_FILE}")
        else:
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


def python_hook_commands(config: dict) -> set[str]:
    """The `command` of every hook that runs a Python script, in exec form.

    Raises AttributeError or TypeError when `hooks` is not the documented
    mapping of event to matcher groups; the caller reports that.
    """
    commands: set[str] = set()
    for groups in config.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                arguments = hook.get("args") or []
                command = hook.get("command")
                if isinstance(command, str) and arguments and str(arguments[0]).endswith(".py"):
                    commands.add(command)
    return commands


def starts_python(command: str) -> bool:
    try:
        result = subprocess.run(
            [command, "-c", PYTHON_PROBE],
            capture_output=True,
            timeout=PROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def check_settings(root: Path) -> None:
    """The client configuration parses, and its hooks can start on this machine.

    Both failures are silent in Claude Code. A settings file it cannot parse is
    ignored, which drops every deny rule and every hook at once; a hook it
    cannot start is a non-blocking error, and the call proceeds. The first is
    an error. The second is a warning, because the file is shared through git
    and a name that is right on one operating system can be absent on another.
    """
    path = root / SETTINGS
    if not path.exists():
        return
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        commands = python_hook_commands(config)
    except (UnicodeDecodeError, ValueError) as err:
        error(SETTINGS, 0, f"not valid JSON, so Claude Code ignores every rule and hook in it: {err}")
        return
    except (AttributeError, TypeError):
        error(SETTINGS, 0, "`hooks` is not in the shape Claude Code reads, so no hook in it runs")
        return
    for command in sorted(commands):
        if not starts_python(command):
            warn(SETTINGS, 0,
                 f"hook interpreter `{command}` does not start Python 3.9+ on this machine, "
                 "so Claude Code cannot run the hooks here and lets every call through; "
                 "see README.md, Requirements")


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
        lines = check_shape(relative, path.read_bytes(), BUDGETS[relative]["wrap"])
        if lines is not None:
            documents[relative] = lines

    budgets = dict(BUDGETS)
    for path in sorted((root / RULES).glob("*.md")):
        relative = path.relative_to(root).as_posix()
        if relative in budgets:
            continue
        budgets[relative] = DEFAULT_RULE_BUDGET
        lines = check_shape(relative, path.read_bytes(), WRAP_LIMIT)
        if lines is not None:
            documents[relative] = lines

    for extra in ("README.md", "CHANGELOG.md"):
        path = root / extra
        if path.exists():
            lines = check_shape(extra, path.read_bytes(), None)
            if lines is not None:
                documents[extra] = lines

    # Every template, not a list of them, so one added later is gated too.
    for path in sorted((root / TEMPLATES).glob("*.md")):
        relative = path.relative_to(root).as_posix()
        lines = check_shape(relative, path.read_bytes(), WRAP_LIMIT)
        if lines is not None:
            documents[relative] = lines

    anchors = collect_anchors(documents)
    corpus = collect_repository_files(root)
    for relative, lines in documents.items():
        if relative in budgets:
            check_budget(relative, lines, budgets[relative])
        check_references(relative, lines, anchors)
        # CHANGELOG.md is exempt: it records the paths that were in force at each
        # release, and a path that has since moved is correct history there.
        if relative != "CHANGELOG.md":
            check_paths(root, relative, lines, corpus)

    check_templates(root, documents)
    check_memory_bank(root)
    check_last_verified_change(root)
    check_decisions(root)
    check_version(root)
    check_settings(root)
    check_gate_list(root)
    check_unmerged(corpus)

    # On exit 2 Claude Code gives Claude the hook's stderr as the reason for the
    # block, so a finding printed to stdout would block the commit unexplained.
    stream = sys.stderr if arguments.hook else sys.stdout
    errors = [f for f in findings if f.level == "ERROR"]
    warnings = [f for f in findings if f.level == "WARN"]
    for finding in sorted(findings, key=lambda f: (f.path, f.line)):
        location = f"{finding.path}:{finding.line}" if finding.line else finding.path
        print(f"{finding.level:5} {location}: {finding.message}", file=stream)

    checked = len(documents)
    print(f"\ncheck-docs: {checked} documents checked, {len(errors)} errors, {len(warnings)} warnings",
          file=stream)
    if not errors:
        return 0
    # A PreToolUse hook must exit 2 to block the tool call; any other non-zero
    # code is treated as a non-blocking error and the commit would proceed.
    return 2 if arguments.hook else 1


if __name__ == "__main__":
    sys.exit(main())
