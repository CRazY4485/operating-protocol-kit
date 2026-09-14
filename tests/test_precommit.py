""".githooks/pre-commit, run by git itself: the gate must judge the commit being made.

The document gate reads the working tree, and git commits the index. Where the
two differ for a file the gate reads, the gate would pass or fail a different
commit from the one being made, so the hook refuses until they agree.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from kit_testing import bootstrap, git, write

GOVERNED = "docs/BOOTSTRAP.md"
BROKEN_REFERENCE = "See *Nonexistent Section Name*.\n"


def commit(root: Path, message: str = "change") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "commit", "-q", "-m", message], cwd=root, capture_output=True, text=True,
        encoding="utf-8", errors="replace", check=False,
    )


@pytest.fixture
def repository(kit_tree: Path) -> Path:
    """The kit as a repository whose commits go through .githooks/pre-commit."""
    os.chmod(kit_tree / ".githooks" / "pre-commit", 0o755)
    git(kit_tree, "init", "-q")
    git(kit_tree, "config", "user.email", "test@example.invalid")
    git(kit_tree, "config", "user.name", "Test")
    git(kit_tree, "config", "core.autocrlf", "false")
    git(kit_tree, "config", "core.hooksPath", ".githooks")
    git(kit_tree, "add", "-A")
    first = commit(kit_tree, "kit")
    assert first.returncode == 0, first.stdout + first.stderr
    return kit_tree


def test_refuses_a_defect_that_is_staged_while_the_working_tree_is_clean(
    repository: Path,
) -> None:
    clean = (repository / GOVERNED).read_bytes()
    write(repository, GOVERNED, clean.decode("utf-8") + BROKEN_REFERENCE)
    git(repository, "add", GOVERNED)
    (repository / GOVERNED).write_bytes(clean)

    result = commit(repository)

    assert result.returncode != 0, "the defect reached the history"
    assert f"{GOVERNED}" in result.stderr


def test_refuses_while_a_file_the_gate_reads_has_unstaged_changes(repository: Path) -> None:
    write(repository, "src/app.py", "print('staged')\n")
    git(repository, "add", "src/app.py")
    (repository / GOVERNED).write_bytes((repository / GOVERNED).read_bytes() + b"More.\n")

    result = commit(repository)

    assert result.returncode != 0
    assert "not staged" in result.stderr
    assert "git stash push --keep-index --include-untracked" in result.stderr


def test_refuses_while_a_file_the_gate_reads_is_untracked(repository: Path) -> None:
    # The index row is staged and the record is not: the working tree agrees
    # with itself, so the gate passes, and the commit indexes a missing file.
    bootstrap(repository)
    git(repository, "add", "-A")
    assert commit(repository, "bootstrap").returncode == 0
    index = repository / "memory-bank/decisions/decisions.md"
    index.write_bytes(index.read_bytes() + b"| 0002 | Second decision | Active |\n")
    git(repository, "add", "memory-bank/decisions/decisions.md")
    write(repository, "memory-bank/decisions/0002-second-decision.md", "# 0002\n")

    result = commit(repository)

    assert result.returncode != 0, "a commit indexing a file it does not contain went through"
    assert "memory-bank/decisions/0002-second-decision.md" in result.stderr


def test_allows_unstaged_changes_the_gate_does_not_read(repository: Path) -> None:
    write(repository, "src/app.py", "print('one')\n")
    git(repository, "add", "src/app.py")
    write(repository, "src/app.py", "print('two')\n")

    result = commit(repository)

    assert result.returncode == 0, result.stdout + result.stderr


def test_an_unmerged_kit_file_does_not_hold_up_a_commit(repository: Path) -> None:
    write(repository, ".claude/settings.json.kit-new", "{}\n")
    write(repository, "src/app.py", "print('staged')\n")
    git(repository, "add", "src/app.py")

    result = commit(repository)

    assert result.returncode == 0, result.stdout + result.stderr


def test_a_fully_staged_defect_is_refused_by_the_gate(repository: Path) -> None:
    write(repository, GOVERNED, (repository / GOVERNED).read_text(encoding="utf-8")
          + BROKEN_REFERENCE)
    git(repository, "add", GOVERNED)

    result = commit(repository)

    assert result.returncode != 0
    assert "resolves to no section or label" in result.stdout + result.stderr
