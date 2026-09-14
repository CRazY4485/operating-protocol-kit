"""Helpers shared by the kit's tests: copying the kit, running the gate, reading hooks."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

KIT = Path(__file__).resolve().parents[1]
GATE = Path(".claude") / "tools" / "check-docs.py"
SETTINGS = Path(".claude") / "settings.json"

# The kit's own development files. They are never part of what the gate checks
# or what an installer copies, so a copy of the kit leaves them out.
DEVELOPMENT_ONLY = ("tests/", ".github/")


def load_script(relative: Path, name: str) -> ModuleType:
    """A kit script as a module, for reading its declared figures rather than copying them."""
    path = KIT / relative
    # Run as a program, a script finds its sibling modules on sys.path[0].
    if str(path.parent) not in sys.path:
        sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolves annotations through it
    spec.loader.exec_module(module)
    return module


def load_gate() -> ModuleType:
    return load_script(GATE, "check_docs")


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


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def filler(count: int) -> str:
    """`count` words, ten to a line, so no line breaks the wrap limit."""
    lines = [" ".join(["word"] * min(10, count - start)) for start in range(0, count, 10)]
    return "".join(line + "\n" for line in lines)


TIER1 = (
    "memory-bank/activeContext.md",
    "memory-bank/progress.md",
    "memory-bank/decisions/decisions.md",
)
INDEX = "memory-bank/decisions/decisions.md"


ACTIVE_CONTEXT = "memory-bank/activeContext.md"
VOICE_FILE = "memory-bank/voice.json"
# A gate log no test machine holds, so its citation is taken as written.
CITED_ELSEWHERE = "logs/gate-20260101T000000Z.log, sha256 " + "0" * 64


def active_context(verified: str) -> str:
    """An activeContext.md whose last verified change says `verified`."""
    return ("# Active context\n\n## Last verified change\n<!-- verified -->\n"
            f"{verified}\n\n## Approved plan\n<!-- plan -->\n\n- [ ] Step one\n")


def bootstrap(root: Path) -> None:
    """A minimal Memory Bank that passes every check."""
    for relative in TIER1:
        write(root, relative, "# State\n\nOne fact.\n")
    write(root, ACTIVE_CONTEXT, active_context(f"Bootstrap finished; {CITED_ELSEWHERE}."))
    write(root, VOICE_FILE, '{"phrases": ["I think", "məncə"]}\n')
    write(root, INDEX, "# Decisions\n\n| Number | Summary | Status |\n|---|---|---|\n"
                       "| 0001 | First decision | Active |\n")
    write(root, "memory-bank/decisions/0001-first-decision.md", "# 0001 First decision\n")


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

    def _summary(self) -> tuple[int, int]:
        match = re.search(r"checked, (\d+) errors, (\d+) warnings", self.output)
        assert match, f"no summary line in gate output:\n{self.output}"
        return int(match.group(1)), int(match.group(2))

    @property
    def errors(self) -> int:
        return self._summary()[0]

    @property
    def warnings(self) -> int:
        return self._summary()[1]


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
