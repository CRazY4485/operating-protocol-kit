from __future__ import annotations

import sys
from pathlib import Path

import pytest

from kit_testing import copy_kit, git, point_hooks_at


@pytest.fixture
def kit_tree(tmp_path: Path) -> Path:
    """A copy of the kit as the gate sees the kit repository itself.

    The hooks are pointed at the interpreter running the tests, so what the
    machine happens to have on PATH cannot change a result.
    """
    root = copy_kit(tmp_path / "kit")
    point_hooks_at(root, sys.executable)
    return root


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """An empty project repository with one commit and a clean working tree."""
    root = tmp_path / "project"
    root.mkdir()
    git(root, "init", "-q")
    git(root, "config", "user.email", "test@example.invalid")
    git(root, "config", "user.name", "Test")
    git(root, "config", "core.autocrlf", "false")
    git(root, "commit", "-q", "--allow-empty", "-m", "init")
    return root
