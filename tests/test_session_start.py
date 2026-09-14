"""The SessionStart hook's state report, produced the way Claude Code runs the hook."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

from kit_testing import KIT

HOOK = KIT / ".claude" / "hooks" / "session-start.py"


def state_report(root: Path) -> str:
    result = subprocess.run(
        [sys.executable, str(HOOK), str(root)],
        input=json.dumps({"source": "clear"}).encode("utf-8"),
        capture_output=True,
        check=True,
    )
    return json.loads(result.stdout.decode("utf-8"))["hookSpecificOutput"]["additionalContext"]


def test_reads_the_plan_from_a_file_made_from_the_shipped_template(tmp_path: Path) -> None:
    bank = tmp_path / "memory-bank"
    bank.mkdir()
    shutil.copyfile(KIT / "docs" / "templates" / "activeContext.md", bank / "activeContext.md")

    report = state_report(tmp_path)

    assert "open plan, verbatim from activeContext.md:" in report
    assert "**Goal:**" in report
    # The instruction above the anchor is guidance, not part of the plan.
    assert "Keep the anchor" not in report
