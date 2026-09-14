#!/usr/bin/env python3
"""The one gate command: the document gate, then the project's own gates, with evidence.

Runs .claude/tools/check-docs.py, then every gate in .claude/gates.json that
applies to this operating system, in the order listed, each from the
repository root. Everything they print goes to the screen and, byte for byte,
to logs/gate-<UTC timestamp>.log. On exit it prints the log's path and its
SHA-256, so a report can cite a file the owner can open and a hash showing the
file is the one this run wrote. See CLAUDE.md, *Quality gates*.

.claude/gates.json belongs to the project; BOOTSTRAP.md step 6 creates it from
docs/templates/gates.json. Each gate names its command as an argument list and
runs with no shell, so a gate made of several steps runs a script the project
keeps:

    {"gates": [
        {"name": "tests", "command": ["python", "-m", "pytest", "-q"]},
        {"name": "build", "command": ["dotnet", "build", "--nologo"],
         "os": ["win32"], "timeout_seconds": 900}
    ]}

`os` limits a gate to some of linux, darwin and win32. `timeout_seconds` stops
a gate that runs longer, and fails it.

Exit code 0 means every gate that ran passed. Every other outcome fails the
run: a gate that exits non-zero, times out or cannot start; a gates file that
cannot be used, in which case none of it runs; and a project past bootstrap
(memory-bank/ exists) with no gates file at all, because a runtime with no
recorded gate is a blocker. A project with nothing of its own to gate says so
with {"gates": []}. Every gate runs even after one fails, so one run reports
everything that is wrong.

Usage:
    python .claude/tools/run-gates.py            # from the repository root
    python .claude/tools/run-gates.py --root DIR
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO

from kit_config import GATES_FILE, Gate, load_gates

LOGS = "logs"
DOCUMENT_GATE = Path(".claude") / "tools" / "check-docs.py"
PASSING = ("PASS", "SKIPPED")


class Tee:
    """Every byte to the screen and to the log, in the order it arrived."""

    def __init__(self, log: BinaryIO) -> None:
        self._log = log
        self._screen = sys.stdout.buffer

    def write(self, data: bytes) -> None:
        self._screen.write(data)
        self._screen.flush()
        self._log.write(data)

    def line(self, text: str = "") -> None:
        self.write((text + "\n").encode("utf-8"))


def new_log(root: Path, now: datetime) -> Path:
    folder = root / LOGS
    folder.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    path = folder / f"gate-{stamp}.log"
    counter = 2
    while path.exists():  # two runs in one second must not share a log
        path = folder / f"gate-{stamp}-{counter}.log"
        counter += 1
    return path


def run_one(gate: Gate, root: Path, out: Tee) -> str:
    """Run one gate with its output streamed through `out`; return its result."""
    out.line(f"== {gate.name}: {subprocess.list2cmdline(list(gate.command))}")
    started = time.monotonic()
    try:
        process = subprocess.Popen(
            list(gate.command), cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
        )
    except OSError as err:
        out.line(f"-- {gate.name}: NOT STARTED - {err}")
        out.line()
        return "NOT STARTED"

    timed_out = threading.Event()
    timer = None
    if gate.timeout_seconds is not None:
        def stop() -> None:
            timed_out.set()
            process.kill()

        timer = threading.Timer(gate.timeout_seconds, stop)
        timer.start()
    try:
        assert process.stdout is not None
        for chunk in iter(lambda: process.stdout.read1(65536), b""):  # type: ignore[union-attr]
            out.write(chunk)
        code = process.wait()
    finally:
        if timer is not None:
            timer.cancel()

    if timed_out.is_set():
        result = f"TIMEOUT after {gate.timeout_seconds:g}s"
    elif code == 0:
        result = "PASS"
    else:
        result = f"FAIL (exit {code})"
    out.line(f"-- {gate.name}: {result} in {time.monotonic() - started:.1f}s")
    out.line()
    return result


def run_all(root: Path, out: Tee) -> list[tuple[str, str]]:
    document_gate = Gate(
        "document gate", (sys.executable, str(root / DOCUMENT_GATE), "--root", str(root))
    )
    results = [(document_gate.name, run_one(document_gate, root, out))]

    gates, problems = load_gates(root)
    if problems:
        for problem in problems:
            out.line(f"!! {GATES_FILE}: {problem}")
        out.line(f"!! none of {GATES_FILE} runs until it can be used as a whole")
        return results + [(GATES_FILE, "UNREADABLE")]
    if gates is None:
        if (root / "memory-bank").exists():
            # Not a pointer to BOOTSTRAP.md: a bootstrapped project never reads it again.
            out.line(f"!! {GATES_FILE} is missing while memory-bank/ exists: a runtime with no "
                     "recorded gate is a blocker; create it from docs/templates/gates.json "
                     "(CLAUDE.md, Quality gates)")
            return results + [(GATES_FILE, "MISSING")]
        out.line(f"-- {GATES_FILE} is absent before bootstrap: the document gate is the only gate")
        return results
    if not gates:
        out.line(f"-- {GATES_FILE} lists no gates: the document gate is the only gate")
    for gate in gates:
        if gate.runs_on(sys.platform):
            results.append((gate.name, run_one(gate, root, out)))
        else:
            out.line(f"-- {gate.name}: SKIPPED - it runs on {', '.join(gate.platforms)}, "
                     f"and this is {sys.platform}")
            results.append((gate.name, "SKIPPED"))
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run every gate and keep the evidence.")
    parser.add_argument("--root", default=".", help="repository root (default: current directory)")
    root = Path(parser.parse_args().root).resolve()

    now = datetime.now(timezone.utc)
    log_path = new_log(root, now)
    with log_path.open("wb") as log:
        out = Tee(log)
        out.line(f"run-gates: {now:%Y-%m-%dT%H:%M:%SZ} on {sys.platform}, root {root}")
        out.line()
        results = run_all(root, out)
        failed = [name for name, result in results if result not in PASSING]
        out.line("== summary")
        for name, result in results:
            out.line(f"   {result:<24} {name}")
        out.line(f"run-gates: {'FAILED' if failed else 'PASSED'}")

    digest = hashlib.sha256(log_path.read_bytes()).hexdigest()
    print(f"gate log: {log_path.relative_to(root).as_posix()}")
    print(f"sha256:   {digest}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
