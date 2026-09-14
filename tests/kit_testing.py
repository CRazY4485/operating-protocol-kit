"""Helpers shared by the kit's tests: copying the kit, running the gate, reading hooks."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
GATE = Path(".claude") / "tools" / "check-docs.py"
SETTINGS = Path(".claude") / "settings.json"

# The kit's own development files. They are never part of what the gate checks
# or what an installer copies, so a copy of the kit leaves them out.
DEVELOPMENT_ONLY = ("tests/", ".github/")


def git(cwd: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=cwd, check=True, capture_output=True, text=True
    )
    return result.stdout


def kit_files() -> list[str]:
    """Every file the kit consists of right now, committed or not, minus ignored ones."""
    listed = git(KIT, "ls-files", "--cached", "--others", "--exclude-standard")
    return [
        relative
        for relative in listed.splitlines()
        if relative
        and not relative.startswith(DEVELOPMENT_ONLY)
        and (KIT / relative).is_file()
    ]


def copy_kit(destination: Path) -> Path:
    for relative in kit_files():
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KIT / relative, target)
    return destination


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(value, indent=2) + "\n").encode("utf-8"))


def python_hooks(settings: Path) -> list[dict]:
    """The hook entries that run one of the kit's Python scripts."""
    config = json.loads(settings.read_text(encoding="utf-8"))
    return [
        hook
        for groups in config.get("hooks", {}).values()
        for group in groups
        for hook in group.get("hooks", [])
        if hook.get("args") and str(hook["args"][0]).endswith(".py")
    ]


def point_hooks_at(root: Path, interpreter: str) -> None:
    settings = root / SETTINGS
    config = json.loads(settings.read_text(encoding="utf-8"))
    for groups in config.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("args") and str(hook["args"][0]).endswith(".py"):
                    hook["command"] = interpreter
    write_json(settings, config)


@dataclass(frozen=True)
class GateRun:
    code: int
    stdout: str
    stderr: str

    @property
    def output(self) -> str:
        return self.stdout + self.stderr


def run_gate(root: Path, *arguments: str) -> GateRun:
    result = subprocess.run(
        [sys.executable, str(root / GATE), "--root", str(root), *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    return GateRun(result.returncode, result.stdout, result.stderr)
