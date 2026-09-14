"""The document gate, run the way git and Claude Code run it: as a program on a tree."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from kit_testing import SETTINGS, point_hooks_at, run_gate, write_json


def test_a_clean_copy_of_the_kit_passes(kit_tree: Path) -> None:
    run = run_gate(kit_tree)

    assert run.code == 0, run.output
    assert "0 errors, 0 warnings" in run.output


# --- the hooks' interpreter --------------------------------------------------


def test_warns_when_the_hook_interpreter_does_not_start(kit_tree: Path) -> None:
    point_hooks_at(kit_tree, "no-such-python-3f9c")

    run = run_gate(kit_tree)

    assert run.code == 0, run.output
    assert "WARN  .claude/settings.json: hook interpreter `no-such-python-3f9c`" in run.output


def test_does_not_probe_hooks_that_run_no_python(kit_tree: Path) -> None:
    settings = kit_tree / SETTINGS
    config = json.loads(settings.read_text(encoding="utf-8"))
    config["hooks"]["PostToolUse"] = [
        {
            "matcher": "Edit",
            "hooks": [{"type": "command", "command": "node", "args": ["format.js"]}],
        }
    ]
    write_json(settings, config)

    run = run_gate(kit_tree)

    assert "`node`" not in run.output
    assert "0 errors, 0 warnings" in run.output


def test_settings_that_are_not_json_fail_the_gate(kit_tree: Path) -> None:
    (kit_tree / SETTINGS).write_bytes(b'{ "hooks": ')

    run = run_gate(kit_tree)

    assert run.code == 1, run.output
    assert "ERROR .claude/settings.json: not valid JSON" in run.output


def test_the_interpreter_running_the_tests_is_accepted(kit_tree: Path) -> None:
    point_hooks_at(kit_tree, sys.executable)

    run = run_gate(kit_tree)

    assert "settings.json" not in run.output
