"""The gate runner: every gate in order, one log, and a hash that pins the log down."""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

from kit_testing import KIT, bootstrap, write, write_json

RUNNER = Path(".claude") / "tools" / "run-gates.py"
GATES = ".claude/gates.json"
OTHER_PLATFORM = "darwin" if sys.platform != "darwin" else "linux"


@dataclass(frozen=True)
class Run:
    code: int
    stdout: str
    log: Path
    digest: str

    @property
    def text(self) -> str:
        return self.log.read_text(encoding="utf-8", errors="replace")


def run_runner(root: Path) -> Run:
    result = subprocess.run(
        [sys.executable, str(root / RUNNER), "--root", str(root)],
        capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    # print() ends a line with CRLF on Windows.
    stdout = result.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
    log = re.search(r"^gate log: (\S+)$", stdout, re.MULTILINE)
    digest = re.search(r"^sha256: +([0-9a-f]{64})$", stdout, re.MULTILINE)
    assert log and digest, stdout + result.stderr.decode("utf-8", errors="replace")
    return Run(result.returncode, stdout, root / log.group(1), digest.group(1))


def python_gate(name: str, code: str, **extra: object) -> dict:
    return {"name": name, "command": [sys.executable, "-c", code], **extra}


def set_gates(root: Path, *gates: dict) -> None:
    write_json(root / GATES, {"gates": list(gates)})


def test_before_bootstrap_the_document_gate_is_the_only_gate(kit_tree: Path) -> None:
    run = run_runner(kit_tree)

    assert run.code == 0, run.text
    assert "PASS" in run.text and "document gate" in run.text


def test_logs_under_logs_with_a_utc_timestamp(kit_tree: Path) -> None:
    run = run_runner(kit_tree)

    assert re.fullmatch(r"gate-\d{8}T\d{6}Z(-\d+)?\.log", run.log.name)
    assert run.log.parent == kit_tree / "logs"


def test_prints_the_sha256_of_the_log_it_wrote(kit_tree: Path) -> None:
    run = run_runner(kit_tree)

    assert run.digest == hashlib.sha256(run.log.read_bytes()).hexdigest()


def test_two_runs_never_share_a_log(kit_tree: Path) -> None:
    first = run_runner(kit_tree)
    second = run_runner(kit_tree)

    assert first.log != second.log
    assert first.log.exists() and second.log.exists()


def test_writes_every_gates_full_output_to_the_log(kit_tree: Path) -> None:
    set_gates(kit_tree, python_gate("echo", "print('marker-7f3a'); import sys; "
                                            "print('to-stderr-7f3a', file=sys.stderr)"))

    run = run_runner(kit_tree)

    assert run.code == 0, run.text
    assert "marker-7f3a" in run.text
    assert "to-stderr-7f3a" in run.text
    assert "check-docs:" in run.text  # the document gate's own output


def test_fails_when_a_gate_fails(kit_tree: Path) -> None:
    set_gates(kit_tree, python_gate("broken", "import sys; sys.exit(3)"))

    run = run_runner(kit_tree)

    assert run.code == 1
    assert "FAIL (exit 3)" in run.text


def test_fails_when_the_document_gate_fails(kit_tree: Path) -> None:
    write(kit_tree, ".claude/KIT_VERSION", "one\n")

    run = run_runner(kit_tree)

    assert run.code == 1
    assert "is not a semantic version" in run.text


def test_runs_every_gate_even_after_one_fails(kit_tree: Path) -> None:
    set_gates(kit_tree, python_gate("first", "import sys; sys.exit(1)"),
              python_gate("second", "print('second-ran-7f3a')"))

    run = run_runner(kit_tree)

    assert run.code == 1
    assert "second-ran-7f3a" in run.text


def test_fails_a_gate_that_cannot_start(kit_tree: Path) -> None:
    set_gates(kit_tree, {"name": "missing", "command": ["no-such-program-7f3a"]})

    run = run_runner(kit_tree)

    assert run.code == 1
    assert "NOT STARTED" in run.text


def test_fails_a_gate_that_outruns_its_timeout(kit_tree: Path) -> None:
    set_gates(kit_tree, python_gate("slow", "import time; time.sleep(60)", timeout_seconds=1))

    run = run_runner(kit_tree)

    assert run.code == 1
    assert "TIMEOUT" in run.text


def test_skips_a_gate_meant_for_another_operating_system(kit_tree: Path) -> None:
    set_gates(kit_tree, python_gate("elsewhere", "print('ran-7f3a')", os=[OTHER_PLATFORM]))

    run = run_runner(kit_tree)

    assert run.code == 0, run.text
    assert "SKIPPED" in run.text
    assert "ran-7f3a" not in run.text


def test_runs_a_gate_from_the_repository_root(kit_tree: Path) -> None:
    set_gates(kit_tree, python_gate("where", "import os; print('cwd=' + os.getcwd())"))

    run = run_runner(kit_tree)

    assert f"cwd={kit_tree}" in run.text


def test_after_bootstrap_a_missing_gates_file_fails(kit_tree: Path) -> None:
    # A runtime with no recorded gate is a blocker; see CLAUDE.md, Quality gates.
    bootstrap(kit_tree)

    run = run_runner(kit_tree)

    assert run.code == 1
    assert "MISSING" in run.text


def test_an_empty_gate_list_is_a_declared_choice(kit_tree: Path) -> None:
    bootstrap(kit_tree)
    set_gates(kit_tree)

    run = run_runner(kit_tree)

    assert run.code == 0, run.text


def test_a_gates_file_it_cannot_use_fails_and_runs_none_of_it(kit_tree: Path) -> None:
    write_json(kit_tree / GATES, {"gates": [python_gate("echo", "print('ran-7f3a')"),
                                            {"name": "no command"}]})

    run = run_runner(kit_tree)

    assert run.code == 1
    assert "UNREADABLE" in run.text
    assert "ran-7f3a" not in run.text


def test_the_shipped_gates_template_is_a_valid_start(kit_tree: Path) -> None:
    shutil.copyfile(kit_tree / "docs/templates/gates.json", kit_tree / GATES)
    config = json.loads((kit_tree / GATES).read_text(encoding="utf-8"))
    # Its gates name tools a machine may lack; only its shape is at issue here.
    for gate in config["gates"]:
        gate["command"] = [sys.executable, "-c", "pass"]
    write_json(kit_tree / GATES, config)

    run = run_runner(kit_tree)

    assert run.code == 0, run.text


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ("[]", "a JSON object with a `gates` list"),
        ('{"gates": {}}', "a JSON object with a `gates` list"),
        ('{"gates": [], "extra": 1}', "unknown key `extra`"),
        ('{"gates": ["tests"]}', "gate 1 must be an object"),
        ('{"gates": [{"command": ["x"]}]}', "gate 1 needs a `name`"),
        ('{"gates": [{"name": "t", "command": "pytest -q"}]}', "`command` as a list"),
        ('{"gates": [{"name": "t", "command": []}]}', "`command` as a list"),
        ('{"gates": [{"name": "t", "command": ["x"], "os": ["windows"]}]}', "`os`"),
        ('{"gates": [{"name": "t", "command": ["x"], "timeout_seconds": 0}]}', "`timeout_seconds`"),
        ('{"gates": [{"name": "t", "command": ["x"], "shell": true}]}', "unknown key `shell`"),
        ('{"gates": [{"name": "t", "command": ["x"]}, {"name": "t", "command": ["y"]}]}',
         "more than one gate is named `t`"),
    ],
)
def test_the_document_gate_rejects_a_gates_file_it_cannot_use(
    kit_tree: Path, config: str, message: str
) -> None:
    from kit_testing import run_gate

    write(kit_tree, GATES, config + "\n")

    run = run_gate(kit_tree)

    assert run.code == 1, run.output
    assert f"ERROR {GATES}: " in run.output
    assert message in run.output
