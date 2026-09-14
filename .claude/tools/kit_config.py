"""Figures and project settings the kit's scripts share, each with one home.

check-docs.py and the SessionStart hook both judge Tier 1 files against their
budgets; they read the figures from here, so the two can never disagree.
Standard library only, like every script in the kit.
"""

from __future__ import annotations

import json
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
