"""Figures and project settings the kit's scripts share, each with one home.

check-docs.py and the SessionStart hook both judge Tier 1 files against their
budgets, and check-docs.py and run-gates.py both read the project's gate list;
they read them from here, so no two scripts can disagree about either.
Standard library only, like every script in the kit.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

# Tier 1 files, read at the start of every task, and their starting budgets in
# words. A project changes a figure in memory-bank/budgets.json, never here: this
# file is the kit's, and an upgrade replaces it. See CLAUDE.md, *Memory Bank*.
TIER1_BUDGETS: dict[str, int] = {
    "memory-bank/activeContext.md": 400,
    "memory-bank/progress.md": 650,
    "memory-bank/decisions/decisions.md": 400,
}
BUDGETS_FILE = "memory-bank/budgets.json"


def load_budgets(root: Path) -> tuple[dict[str, int], set[str], list[str]]:
    """The Tier 1 budgets in force, the files the project set, and what was wrong.

    An absent memory-bank/budgets.json is not a problem: the starting figures
    apply. An entry that cannot be used is reported and the starting figure
    stays in force for that file, so a typo never silently lifts a budget.
    """
    budgets = dict(TIER1_BUDGETS)
    path = root / BUDGETS_FILE
    if not path.exists():
        return budgets, set(), []
    try:
        overrides = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as err:
        return budgets, set(), [f"not valid JSON: {err}"]
    if not isinstance(overrides, dict):
        return budgets, set(), ["must be a JSON object mapping a Tier 1 file to its budget in words"]

    project_set: set[str] = set()
    problems: list[str] = []
    for name, words in overrides.items():
        if name not in TIER1_BUDGETS:
            problems.append(f"`{name}` is not a Tier 1 file; those are {', '.join(TIER1_BUDGETS)}")
        elif isinstance(words, bool) or not isinstance(words, int) or words <= 0:
            problems.append(
                f"the budget for `{name}` must be a positive whole number of words, not {words!r}"
            )
        else:
            budgets[name] = words
            project_set.add(name)
    return budgets, project_set, problems


# The project's own gates, run by run-gates.py after the document gate. The
# file belongs to the project: BOOTSTRAP.md step 6 creates it from
# docs/templates/gates.json, and the kit never ships or overwrites it.
GATES_FILE = ".claude/gates.json"
PLATFORMS = ("linux", "darwin", "win32")  # the sys.platform values `os` accepts
GATE_KEYS = {"name", "command", "os", "timeout_seconds"}


@dataclass(frozen=True)
class Gate:
    name: str
    command: tuple[str, ...]  # an argument list, run with no shell
    platforms: tuple[str, ...] = ()  # empty: every operating system
    timeout_seconds: float | None = None

    def runs_on(self, platform: str) -> bool:
        return not self.platforms or platform in self.platforms


def _gate_problems(where: str, entry: dict) -> list[str]:
    problems = [f"{where} has unknown key `{key}`" for key in sorted(set(entry) - GATE_KEYS)]
    name = entry.get("name")
    if not isinstance(name, str) or not name.strip():
        problems.append(f"{where} needs a `name`")
    command = entry.get("command")
    if not (isinstance(command, list) and command
            and all(isinstance(part, str) and part for part in command)):
        problems.append(f"{where} needs `command` as a list of arguments, run with no shell; "
                        "a pipeline belongs in a script the project keeps")
    if "os" in entry:
        platforms = entry["os"]
        if not (isinstance(platforms, list) and platforms
                and all(platform in PLATFORMS for platform in platforms)):
            problems.append(f"{where}: `os` lists one or more of {', '.join(PLATFORMS)}")
    timeout = entry.get("timeout_seconds")
    if timeout is not None and (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
                                or timeout <= 0):
        problems.append(f"{where}: `timeout_seconds` must be a positive number")
    return problems


def load_gates(root: Path) -> tuple[list[Gate] | None, list[str]]:
    """The project's gates and what was wrong with them; None when there is no file.

    Any problem makes the whole list unusable: a runner that ran half of a
    malformed list would report a pass the project never defined.
    """
    path = root / GATES_FILE
    if not path.exists():
        return None, []
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as err:
        return [], [f"not valid JSON: {err}"]
    if not isinstance(config, dict) or not isinstance(config.get("gates"), list):
        return [], ["must be a JSON object with a `gates` list"]

    problems = [f"unknown key `{key}`" for key in sorted(set(config) - {"gates"})]
    gates: list[Gate] = []
    seen: set[str] = set()
    for index, entry in enumerate(config["gates"], start=1):
        where = f"gate {index}"
        if not isinstance(entry, dict):
            problems.append(f"{where} must be an object")
            continue
        found = _gate_problems(where, entry)
        problems += found
        if found:
            continue
        if entry["name"] in seen:
            problems.append(f"more than one gate is named `{entry['name']}`")
        seen.add(entry["name"])
        gates.append(Gate(entry["name"], tuple(entry["command"]), tuple(entry.get("os", [])),
                          entry.get("timeout_seconds")))
    return (gates if not problems else []), problems
