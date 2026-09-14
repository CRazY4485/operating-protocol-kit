"""What install.sh and install.ps1 write into a project, and what they leave alone."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from kit_testing import KIT, SETTINGS, git, python_hooks, write_json

INSTALLERS = ["install.sh", "install.ps1"]

PROJECT_SETTINGS = {
    "hooks": {
        "PostToolUse": [
            {
                "matcher": "Edit|Write",
                "hooks": [
                    {
                        "type": "command",
                        "command": "node",
                        "args": ["${CLAUDE_PROJECT_DIR}/scripts/format.js"],
                    }
                ],
            }
        ]
    }
}


def posix_shell() -> str | None:
    if sys.platform != "win32":
        return shutil.which("sh")
    # On Windows `bash` on PATH is often WSL's, which sees a different
    # filesystem; Git for Windows ships the sh that git itself uses.
    git_executable = shutil.which("git")
    if git_executable is None:
        return None
    candidate = Path(git_executable).resolve().parents[1] / "bin" / "sh.exe"
    return str(candidate) if candidate.is_file() else None


def run_installer(installer: str, target: Path) -> subprocess.CompletedProcess[str]:
    if installer == "install.sh":
        shell = posix_shell()
        if shell is None:
            pytest.skip("no POSIX sh on this machine")
        command = [shell, (KIT / installer).as_posix(), target.as_posix()]
    else:
        if sys.platform != "win32":
            pytest.skip("install.ps1 writes Windows paths")
        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell is None:
            pytest.skip("no PowerShell on this machine")
        command = [powershell, "-NoProfile", "-File", str(KIT / installer), str(target)]
    return subprocess.run(
        command, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False
    )


def proven_interpreter(result: subprocess.CompletedProcess[str]) -> str:
    match = re.search(r"^Gate interpreter: (\S+) \(", result.stdout, re.MULTILINE)
    assert match, result.stdout + result.stderr
    return match.group(1)


def commit_project_settings(project: Path) -> bytes:
    write_json(project / SETTINGS, PROJECT_SETTINGS)
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "project settings")
    return (project / SETTINGS).read_bytes()


@pytest.mark.parametrize("installer", INSTALLERS)
def test_leaves_the_projects_own_settings_untouched(installer: str, project: Path) -> None:
    original = commit_project_settings(project)

    result = run_installer(installer, project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / SETTINGS).read_bytes() == original


@pytest.mark.parametrize("installer", INSTALLERS)
def test_kit_new_settings_name_the_proven_interpreter(installer: str, project: Path) -> None:
    commit_project_settings(project)

    result = run_installer(installer, project)

    kit_new = project / ".claude" / "settings.json.kit-new"
    assert {hook["command"] for hook in python_hooks(kit_new)} == {proven_interpreter(result)}


@pytest.mark.parametrize("installer", INSTALLERS)
def test_fresh_install_names_the_proven_interpreter(installer: str, project: Path) -> None:
    result = run_installer(installer, project)

    assert result.returncode == 0, result.stdout + result.stderr
    commands = {hook["command"] for hook in python_hooks(project / SETTINGS)}
    assert commands == {proven_interpreter(result)}


KIT_ONLY = ["README.md", "CHANGELOG.md", "install.sh", "install.ps1", "tests",
            ".github/workflows/kit-tests.yml"]


@pytest.mark.parametrize("installer", INSTALLERS)
def test_copies_nothing_that_belongs_to_the_kit_alone(installer: str, project: Path) -> None:
    tracked = git(KIT, "ls-files")
    for relative in ("tests/test_install.py", ".github/workflows/kit-tests.yml"):
        assert relative in tracked, f"stage {relative} so this test means something"

    result = run_installer(installer, project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert [relative for relative in KIT_ONLY if (project / relative).exists()] == []


@pytest.mark.parametrize("installer", INSTALLERS)
def test_copies_the_document_gate_workflow(installer: str, project: Path) -> None:
    result = run_installer(installer, project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / ".github" / "workflows" / "document-gate.yml").is_file()


def test_both_installers_prove_the_same_interpreter(tmp_path: Path) -> None:
    proven = []
    for installer in INSTALLERS:
        target = tmp_path / installer.replace(".", "-")
        target.mkdir()
        git(target, "init", "-q")
        git(target, "config", "user.email", "test@example.invalid")
        git(target, "config", "user.name", "Test")
        git(target, "commit", "-q", "--allow-empty", "-m", "init")
        proven.append(proven_interpreter(run_installer(installer, target)))

    # The name lands in a settings file the whole team shares, so the
    # operating system's installer must not be what decides it.
    assert proven[0] == proven[1]
