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


def test_install_ps1_does_not_depend_on_get_filehash() -> None:
    # Windows PowerShell 5.1 started from PowerShell 7 - every step on a GitHub
    # Windows runner, or `powershell -File` typed in a PowerShell 7 terminal -
    # inherits a module path it cannot load Get-FileHash from, and the install
    # failed there. That environment cannot be built without PowerShell 7, so
    # the kit-tests workflow's Windows job is where the behaviour is proven;
    # this keeps the dependency from coming back.
    code = [line for line in (KIT / "install.ps1").read_text(encoding="utf-8").splitlines()
            if not line.lstrip().startswith("#")]

    assert [line for line in code if "Get-FileHash" in line] == []


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


KIT_ONLY = ["README.md", "CHANGELOG.md", "install.sh", "install.ps1", "install_support.py",
            "tests", ".github/workflows/kit-tests.yml"]
UPGRADE_NOTES = Path(".claude") / "KIT_UPGRADE.md"


def kit_version() -> str:
    return (KIT / ".claude" / "KIT_VERSION").read_text(encoding="utf-8").strip()


def commit_old_kit_version(project: Path, version: str = "3.0.1") -> None:
    target = project / ".claude" / "KIT_VERSION"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(f"{version}\n".encode("utf-8"))
    git(project, "add", "-A")
    git(project, "commit", "-q", "-m", "an older kit")


@pytest.mark.parametrize("installer", INSTALLERS)
def test_writes_the_upgrade_notes_for_an_older_project(installer: str, project: Path) -> None:
    commit_old_kit_version(project)

    result = run_installer(installer, project)

    assert result.returncode == 0, result.stdout + result.stderr
    notes = (project / UPGRADE_NOTES).read_text(encoding="utf-8")
    assert notes.startswith(f"# Kit upgrade 3.0.1 -> {kit_version()}\n")
    assert "Replace outright" in notes


@pytest.mark.parametrize("installer", INSTALLERS)
def test_writes_no_upgrade_notes_on_a_first_install(installer: str, project: Path) -> None:
    result = run_installer(installer, project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert not (project / UPGRADE_NOTES).exists()


@pytest.mark.parametrize("installer", INSTALLERS)
def test_keeps_upgrade_notes_already_pending(installer: str, project: Path) -> None:
    (project / ".claude").mkdir()
    (project / UPGRADE_NOTES).write_bytes(b"# Steps still to do\n")
    commit_old_kit_version(project)

    result = run_installer(installer, project)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / UPGRADE_NOTES).read_bytes() == b"# Steps still to do\n"
    assert (project / ".claude" / "KIT_UPGRADE.md.kit-new").is_file()


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
