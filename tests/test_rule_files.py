"""Rule files hold rules. The kit's machinery is described where it lives, never in them.

A rule file loads whenever a matching file is read, so whatever it says about
the kit's gate, hooks or setup is paid for in context again and again, and
restates what CLAUDE.md and the tools already say.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kit_testing import KIT

# Names and paths of the kit's machinery: its tools, hooks, configuration and
# setup procedure. Project files such as techContext.md are not machinery.
MACHINERY = [
    ".claude/tools",
    ".claude/hooks",
    ".claude/settings.json",
    "gates.json",
    "budgets.json",
    "voice.json",
    ".githooks",
    "core.hooksPath",
    "PreToolUse",
    "SessionStart",
    "InstructionsLoaded",
    "instructions-loaded.log",
    "BOOTSTRAP.md",
    "check-docs",
    "run-gates",
    "kit_config",
]

MARKDOWN_RULES = KIT / ".claude" / "rules" / "markdown.md"
# The shipped rule files, and the skeleton a new language's rule file starts from.
RULE_FILES = sorted((KIT / ".claude" / "rules").glob("*.md")) + [
    KIT / "docs" / "templates" / "language-rules.md"
]


def machinery_named_in(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [name for name in MACHINERY if name in text]


@pytest.mark.parametrize("path", RULE_FILES, ids=lambda path: path.name)
def test_a_rule_file_names_none_of_the_kits_machinery(path: Path) -> None:
    assert machinery_named_in(path) == []


def test_the_markdown_rules_are_about_writing_not_the_gate() -> None:
    # The document gate is described in CLAUDE.md and in check-docs.py itself.
    assert "gate" not in MARKDOWN_RULES.read_text(encoding="utf-8").lower()


@pytest.mark.parametrize("name", ["CLAUDE.md"])
def test_nothing_sends_the_reader_to_the_markdown_rules_for_the_gate(name: str) -> None:
    assert "*Gate*" not in (KIT / name).read_text(encoding="utf-8")
