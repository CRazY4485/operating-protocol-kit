"""The deny rules in .claude/settings.json, read the way Claude Code documents reading them.

Claude Code's matcher is not importable, so `denies` below re-states the two
documented wildcard rules and nothing else: a `*` stands in for any text, and a
trailing ` *` that is the rule's only wildcard also matches the bare command.
Source: https://code.claude.com/docs/en/permissions, "Wildcard patterns".
Compound commands and wrappers are split and stripped by Claude Code before
matching and are out of scope here; so is whether the client itself agrees,
which BOOTSTRAP.md step 10 proves by watching a rule fire.
"""

from __future__ import annotations

import json
import re

import pytest

from kit_testing import KIT, SETTINGS

RULE = re.compile(r"^(Bash|PowerShell)\((.*)\)$")


def deny_rules(tool: str) -> list[str]:
    config = json.loads((KIT / SETTINGS).read_text(encoding="utf-8"))
    bodies = []
    for rule in config["permissions"]["deny"]:
        match = RULE.match(rule)
        if match and match.group(1) == tool:
            bodies.append(match.group(2))
    return bodies


def matches(body: str, command: str) -> bool:
    pattern = ".*".join(re.escape(part) for part in body.split("*"))
    if re.fullmatch(pattern, command, flags=re.DOTALL):
        return True
    return body.endswith(" *") and body.count("*") == 1 and command == body[:-2]


def denies(command: str) -> bool:
    return any(matches(body, command) for body in deny_rules("Bash"))


@pytest.mark.parametrize(
    "command",
    [
        "git reset --hard",
        "git reset --hard HEAD~1",
        "git reset HEAD~1 --hard",
        "git push --force",
        "git push --force origin main",
        "git push origin main --force",
        "git push --force-with-lease origin main",
        "git push origin main --force-with-lease",
        "git push -f",
        "git push -f origin main",
        "git push -fu origin main",
        "git push origin main -f",
        "git push origin +main",
        "git clean -f",
        "git clean -fd",
        "git clean -fdx",
        "git clean -df",
        "git clean -xdf",
        "git clean -ffdx",
        "git clean --force -d",
        "rm notes.txt",
        "rm -rf build/",
        "find . -name '*.tmp' -delete",
        "truncate -s 0 data.db",
        "shred -u key.pem",
    ],
)
def test_destructive_command_is_denied(command: str) -> None:
    assert denies(command)


@pytest.mark.parametrize(
    "command",
    [
        "git reset HEAD~1",
        "git reset --soft HEAD~1",
        "git push",
        "git push origin main",
        "git push -u origin main",
        "git push origin feature-fix",
        "git push origin --follow-tags",
        "git rm notes.txt",
        "git status",
        "find . -name '*.py'",
    ],
)
def test_everyday_command_is_not_denied(command: str) -> None:
    assert not denies(command)


def test_every_git_rule_has_a_powershell_twin() -> None:
    # Bash and PowerShell are separate permission prefixes, so a git rule
    # written for one tool leaves the same command open through the other.
    bash = {body for body in deny_rules("Bash") if body.startswith("git ")}
    powershell = {body for body in deny_rules("PowerShell") if body.startswith("git ")}

    assert bash == powershell
