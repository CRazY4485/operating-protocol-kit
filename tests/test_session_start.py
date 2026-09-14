"""The SessionStart hook's state report, produced the way Claude Code runs the hook."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kit_testing import KIT, git

HOOK = KIT / ".claude" / "hooks" / "session-start.py"


def state_report(root: Path, isolated_home: Path | None = None) -> str:
    environment = dict(os.environ)
    if isolated_home is not None:
        # Only the repository's own git configuration may decide the answer.
        empty = isolated_home / "gitconfig"
        empty.write_bytes(b"")
        environment.update(GIT_CONFIG_GLOBAL=str(empty), GIT_CONFIG_NOSYSTEM="1")
    result = subprocess.run(
        [sys.executable, str(HOOK), str(root)],
        input=json.dumps({"source": "clear"}).encode("utf-8"),
        capture_output=True,
        env=environment,
        check=True,
    )
    return json.loads(result.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]


@pytest.fixture
def repository(tmp_path: Path) -> Path:
    root = tmp_path / "repository"
    root.mkdir()
    git(root, "init", "-q")
    return root


def git_line(report: str) -> str:
    return next(line for line in report.splitlines() if line.startswith("git: "))


def test_flags_an_unset_hooks_path(repository: Path, tmp_path: Path) -> None:
    line = git_line(state_report(repository, isolated_home=tmp_path))

    assert "core.hooksPath NOT SET" in line


def test_flags_a_hooks_path_other_than_githooks(repository: Path, tmp_path: Path) -> None:
    git(repository, "config", "core.hooksPath", ".husky")

    line = git_line(state_report(repository, isolated_home=tmp_path))

    assert "core.hooksPath .husky - NOT .githooks" in line


@pytest.mark.parametrize("value", [".githooks", ".githooks/"])
def test_accepts_the_kits_hooks_path(repository: Path, tmp_path: Path, value: str) -> None:
    git(repository, "config", "core.hooksPath", value)

    line = git_line(state_report(repository, isolated_home=tmp_path))

    assert line.endswith(f"core.hooksPath {value}")


def test_accepts_the_kits_hooks_path_written_absolute(repository: Path, tmp_path: Path) -> None:
    absolute = (repository / ".githooks").as_posix()
    git(repository, "config", "core.hooksPath", absolute)

    line = git_line(state_report(repository, isolated_home=tmp_path))

    assert "NOT" not in line


def test_reads_the_plan_from_a_file_made_from_the_shipped_template(tmp_path: Path) -> None:
    bank = tmp_path / "memory-bank"
    bank.mkdir()
    shutil.copyfile(KIT / "docs" / "templates" / "activeContext.md", bank / "activeContext.md")

    report = state_report(tmp_path)

    assert "open plan, verbatim from activeContext.md:" in report
    assert "**Goal:**" in report
    # The instruction above the anchor is guidance, not part of the plan.
    assert "Keep the anchor" not in report
