"""The document gate, run the way git and Claude Code run it: as a program on a tree.

Each test changes one thing in a clean copy of the kit and asserts the finding
it must produce, so every check is seen to fire rather than assumed to.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

from kit_testing import SETTINGS, load_gate, load_script, point_hooks_at, run_gate, write_json

GATE = load_gate()
SESSION_START = load_script(Path(".claude/hooks/session-start.py"), "session_start")

# A governed document with a word budget and a wrap limit.
BOOTSTRAP = "docs/BOOTSTRAP.md"
TIER1 = sorted(GATE.TIER1_BUDGETS)
INDEX = "memory-bank/decisions/decisions.md"


def write(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def append(root: Path, relative: str, text: str) -> None:
    path = root / relative
    path.write_bytes(path.read_bytes() + text.encode("utf-8"))


def word_count(root: Path, relative: str) -> int:
    return len((root / relative).read_text(encoding="utf-8").split())


def filler(count: int) -> str:
    """`count` words, ten to a line, so no line breaks the wrap limit."""
    lines = [" ".join(["word"] * min(10, count - start)) for start in range(0, count, 10)]
    return "".join(line + "\n" for line in lines)


def bootstrap(root: Path) -> None:
    """A minimal Memory Bank that passes every check."""
    for relative in TIER1:
        write(root, relative, "# State\n\nOne fact.\n")
    write(root, INDEX, "# Decisions\n\n| Number | Summary | Status |\n|---|---|---|\n"
                       "| 0001 | First decision | Active |\n")
    write(root, "memory-bank/decisions/0001-first-decision.md", "# 0001 First decision\n")


def test_a_clean_copy_of_the_kit_passes(kit_tree: Path) -> None:
    run = run_gate(kit_tree)

    assert run.code == 0, run.output
    assert (run.errors, run.warnings) == (0, 0), run.output


# --- exit codes --------------------------------------------------------------


def test_an_error_exits_1(kit_tree: Path) -> None:
    write(kit_tree, ".claude/KIT_VERSION", "one\n")

    assert run_gate(kit_tree).code == 1


def test_an_error_exits_2_when_run_as_a_hook(kit_tree: Path) -> None:
    # Claude Code blocks a PreToolUse call only on exit 2.
    write(kit_tree, ".claude/KIT_VERSION", "one\n")

    assert run_gate(kit_tree, "--hook").code == 2


def test_findings_go_to_stderr_when_run_as_a_hook(kit_tree: Path) -> None:
    # On exit 2 Claude Code shows Claude the hook's stderr as the reason for
    # the block; stdout would leave Claude knowing only that it was blocked.
    write(kit_tree, ".claude/KIT_VERSION", "one\n")

    run = run_gate(kit_tree, "--hook")

    assert "'one' is not a semantic version" in run.stderr
    assert run.stdout == ""


def test_findings_go_to_stdout_otherwise(kit_tree: Path) -> None:
    write(kit_tree, ".claude/KIT_VERSION", "one\n")

    run = run_gate(kit_tree)

    assert "'one' is not a semantic version" in run.stdout


def test_warnings_alone_pass(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "Trailing space. \n")

    run = run_gate(kit_tree)

    assert run.code == 0, run.output
    assert (run.errors, run.warnings) == (0, 1), run.output


# --- encoding and shape --------------------------------------------------------


def test_rejects_a_document_that_is_not_utf8(kit_tree: Path) -> None:
    (kit_tree / BOOTSTRAP).write_bytes((kit_tree / BOOTSTRAP).read_bytes() + b"\xff\xfe\n")

    assert f"ERROR {BOOTSTRAP}: not valid UTF-8" in run_gate(kit_tree).output


def test_rejects_crlf_line_endings(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "A line.\r\n")

    assert f"ERROR {BOOTSTRAP}: contains CRLF line endings" in run_gate(kit_tree).output


def test_warns_on_trailing_whitespace(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "A line.   \n")

    assert re.search(rf"WARN  {BOOTSTRAP}:\d+: trailing whitespace", run_gate(kit_tree).output)


def test_warns_on_a_missing_final_newline(kit_tree: Path) -> None:
    path = kit_tree / BOOTSTRAP
    path.write_bytes(path.read_bytes().rstrip(b"\n"))

    assert "no trailing newline at end of file" in run_gate(kit_tree).output


def test_rejects_a_line_over_the_wrap_limit(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "x" * (GATE.WRAP_LIMIT + 1) + "\n")

    run = run_gate(kit_tree)

    assert f"line is {GATE.WRAP_LIMIT + 1} columns; limit is {GATE.WRAP_LIMIT}" in run.output


@pytest.mark.parametrize(
    "long_line",
    [
        "| " + "x" * 120 + " |\n",
        "See https://example.com/" + "a" * 100 + "\n",
        "```text\n" + "x" * 120 + "\n```\n",
    ],
    ids=["table row", "bare url", "fenced block"],
)
def test_allows_a_long_line_that_cannot_be_wrapped(kit_tree: Path, long_line: str) -> None:
    append(kit_tree, BOOTSTRAP, long_line)

    assert "columns; limit is" not in run_gate(kit_tree).output


def test_does_not_wrap_claude_md(kit_tree: Path) -> None:
    append(kit_tree, "CLAUDE.md", "x" * 150 + "\n")

    assert "columns; limit is" not in run_gate(kit_tree).output


# --- budgets -------------------------------------------------------------------


def test_rejects_a_document_over_its_word_budget(kit_tree: Path) -> None:
    budget = GATE.BUDGETS[BOOTSTRAP]["words"]
    append(kit_tree, BOOTSTRAP, filler(budget - word_count(kit_tree, BOOTSTRAP) + 1))

    run = run_gate(kit_tree)

    assert f"ERROR {BOOTSTRAP}: {budget + 1} words exceeds the budget of {budget}" in run.output


def test_warns_within_five_percent_of_a_word_budget(kit_tree: Path) -> None:
    budget = GATE.BUDGETS[BOOTSTRAP]["words"]
    append(kit_tree, BOOTSTRAP, filler(budget - word_count(kit_tree, BOOTSTRAP)))

    run = run_gate(kit_tree)

    assert f"WARN  {BOOTSTRAP}: {budget} words is within 5% of the {budget}-word budget" in run.output


def test_rejects_claude_md_over_its_line_budget(kit_tree: Path) -> None:
    budget = GATE.BUDGETS["CLAUDE.md"]["lines"]
    current = len((kit_tree / "CLAUDE.md").read_text(encoding="utf-8").splitlines())
    append(kit_tree, "CLAUDE.md", "x\n" * (budget - current + 1))

    assert f"lines exceeds the budget of {budget}" in run_gate(kit_tree).output


# --- cross-references ------------------------------------------------------------


def test_accepts_a_reference_to_a_bold_label(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "See *Order of authority*.\n")

    assert run_gate(kit_tree).errors == 0


def test_rejects_a_reference_that_resolves_to_nothing(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "See *Nonexistent Section Name*.\n")

    run = run_gate(kit_tree)

    assert "reference *Nonexistent Section Name* resolves to no section or label" in run.output


def test_ignores_italics_that_are_emphasis(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "This is *only emphasis* here.\n")

    assert run_gate(kit_tree).errors == 0


# --- referenced paths --------------------------------------------------------------


def test_rejects_a_link_to_a_missing_file(kit_tree: Path) -> None:
    append(kit_tree, "README.md", "[gone](docs/gone.md)\n")

    run = run_gate(kit_tree)

    assert "link target `docs/gone.md` points at no file in the repository" in run.output


def test_rejects_a_governed_path_that_does_not_exist(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "Run `.claude/tools/gone.py`.\n")

    run = run_gate(kit_tree)

    assert "reference `.claude/tools/gone.py` points at no file in the repository" in run.output


def test_reports_an_incomplete_path_with_the_real_one(kit_tree: Path) -> None:
    append(kit_tree, BOOTSTRAP, "Run `tools/check-docs.py`.\n")

    run = run_gate(kit_tree)

    assert (
        "reference `tools/check-docs.py` is incomplete; the file is at `.claude/tools/check-docs.py`"
        in run.output
    )


@pytest.mark.parametrize("token", ["`src/example`", "`docs/<name>.md`", "`decisions/NNNN-x.md`"])
def test_ignores_a_path_like_token_that_names_no_file(kit_tree: Path, token: str) -> None:
    append(kit_tree, BOOTSTRAP, f"An example: {token}.\n")

    assert run_gate(kit_tree).errors == 0


def test_changelog_may_name_a_path_that_has_moved(kit_tree: Path) -> None:
    append(kit_tree, "CHANGELOG.md", "- Moved `.claude/tools/gone.py`.\n")

    assert run_gate(kit_tree).errors == 0


@pytest.mark.parametrize("link", ["[format](decision-format.md)", "[readme](../README.md)"])
def test_resolves_a_link_against_the_linking_documents_directory(
    kit_tree: Path, link: str
) -> None:
    # Markdown, GitHub and every editor resolve a relative link this way.
    append(kit_tree, BOOTSTRAP, f"See {link}.\n")

    run = run_gate(kit_tree)

    assert run.errors == 0, run.output


def test_rejects_a_root_relative_link_written_in_a_subdirectory(kit_tree: Path) -> None:
    # From docs/ this link opens docs/docs/decision-format.md, which does not exist.
    append(kit_tree, BOOTSTRAP, "See [format](docs/decision-format.md).\n")

    run = run_gate(kit_tree)

    assert "link target `docs/decision-format.md` points at no file" in run.output


def test_rejects_a_link_that_leaves_the_repository(kit_tree: Path) -> None:
    append(kit_tree, "README.md", "[outside](../outside.md)\n")

    assert "link target `../outside.md` points outside the repository" in run_gate(kit_tree).output


# --- templates -----------------------------------------------------------------------

TEMPLATE = "docs/templates/subagent-brief.md"
PLAN_TEMPLATE = "docs/templates/activeContext.md"


def test_rejects_crlf_in_a_template(kit_tree: Path) -> None:
    append(kit_tree, TEMPLATE, "A line.\r\n")

    assert f"ERROR {TEMPLATE}: contains CRLF line endings" in run_gate(kit_tree).output


def test_rejects_a_template_line_over_the_wrap_limit(kit_tree: Path) -> None:
    append(kit_tree, TEMPLATE, "x" * (GATE.WRAP_LIMIT + 1) + "\n")

    assert f"ERROR {TEMPLATE}:" in run_gate(kit_tree).output


def test_rejects_a_reference_to_nothing_in_a_template(kit_tree: Path) -> None:
    append(kit_tree, TEMPLATE, "See *Nonexistent Section Name*.\n")

    assert "reference *Nonexistent Section Name*" in run_gate(kit_tree).output


def test_gates_a_template_added_later(kit_tree: Path) -> None:
    write(kit_tree, "docs/templates/backlog.md", "# Backlog\r\n")

    assert "ERROR docs/templates/backlog.md: contains CRLF" in run_gate(kit_tree).output


@pytest.mark.parametrize("template", ["activeContext.md", "decisions.md", "superseded.md",
                                      "subagent-brief.md"])
def test_rejects_a_missing_template(kit_tree: Path, template: str) -> None:
    (kit_tree / "docs/templates" / template).unlink()

    assert f"ERROR docs/templates/{template}: template is missing" in run_gate(kit_tree).output


def test_requires_the_plan_anchor_in_the_active_context_template(kit_tree: Path) -> None:
    path = kit_tree / PLAN_TEMPLATE
    path.write_bytes(path.read_bytes().replace(b"<!-- plan -->\n", b""))

    run = run_gate(kit_tree)

    assert f"ERROR {PLAN_TEMPLATE}: no `<!-- plan -->` anchor" in run.output


def test_gate_and_session_start_hook_read_the_same_plan_anchor() -> None:
    assert GATE.PLAN_ANCHOR.pattern == SESSION_START.PLAN_ANCHOR.pattern
    assert GATE.PLAN_ANCHOR.flags == SESSION_START.PLAN_ANCHOR.flags


@pytest.mark.parametrize("template", sorted(GATE.TEMPLATE_TARGETS))
def test_rejects_a_template_over_the_budget_of_the_file_it_becomes(
    kit_tree: Path, template: str
) -> None:
    target = GATE.TEMPLATE_TARGETS[template]
    budget = GATE.TIER1_BUDGETS[target]
    append(kit_tree, template, filler(budget - word_count(kit_tree, template) + 1))

    run = run_gate(kit_tree)

    assert f"ERROR {template}: {budget + 1} words is over the {budget}-word budget of {target}" in (
        run.output
    )


def test_the_shipped_tier1_templates_leave_room_under_their_budgets(kit_tree: Path) -> None:
    # A template near its budget makes every bootstrapped project start there.
    for template, target in GATE.TEMPLATE_TARGETS.items():
        assert word_count(kit_tree, template) <= GATE.TIER1_BUDGETS[target] * 0.6, template


# --- unmerged kit files ----------------------------------------------------------------


def test_warns_on_an_unmerged_kit_file(kit_tree: Path) -> None:
    write(kit_tree, ".claude/settings.json.kit-new", "{}\n")

    run = run_gate(kit_tree)

    assert run.code == 0, run.output
    assert "WARN  .claude/settings.json.kit-new: unmerged kit file" in run.output


# --- Memory Bank -------------------------------------------------------------------


def test_a_bootstrapped_memory_bank_passes(kit_tree: Path) -> None:
    bootstrap(kit_tree)

    run = run_gate(kit_tree)

    assert (run.errors, run.warnings) == (0, 0), run.output


@pytest.mark.parametrize("relative", TIER1)
def test_requires_every_tier1_file_once_the_memory_bank_exists(
    kit_tree: Path, relative: str
) -> None:
    bootstrap(kit_tree)
    (kit_tree / relative).unlink()

    run = run_gate(kit_tree)

    assert f"ERROR {relative}: Tier 1 file is missing while memory-bank/ exists" in run.output


def test_rejects_an_empty_tier1_file(kit_tree: Path) -> None:
    bootstrap(kit_tree)
    write(kit_tree, "memory-bank/progress.md", " \n")

    assert "ERROR memory-bank/progress.md: Tier 1 file is empty" in run_gate(kit_tree).output


def test_warns_on_a_tier1_file_over_its_starting_budget(kit_tree: Path) -> None:
    bootstrap(kit_tree)
    budget = GATE.TIER1_BUDGETS["memory-bank/progress.md"]
    write(kit_tree, "memory-bank/progress.md", filler(budget + 1))

    run = run_gate(kit_tree)

    assert f"{budget + 1} words exceeds the starting budget of {budget}" in run.output


# --- decision index ----------------------------------------------------------------


def test_rejects_an_indexed_decision_with_no_file(kit_tree: Path) -> None:
    bootstrap(kit_tree)
    (kit_tree / "memory-bank/decisions/0001-first-decision.md").unlink()

    assert "decision 0001 has no NNNN-*.md file" in run_gate(kit_tree).output


def test_rejects_a_decision_file_missing_from_the_index(kit_tree: Path) -> None:
    bootstrap(kit_tree)
    write(kit_tree, "memory-bank/decisions/0002-second-decision.md", "# 0002\n")

    run = run_gate(kit_tree)

    assert "memory-bank/decisions/0002-*.md: decision file is not listed in the index" in run.output


def test_warns_on_an_empty_decision_index(kit_tree: Path) -> None:
    bootstrap(kit_tree)
    write(kit_tree, INDEX, "# Decisions\n")
    (kit_tree / "memory-bank/decisions/0001-first-decision.md").unlink()

    run = run_gate(kit_tree)

    assert run.code == 0, run.output
    assert "the decision index is empty" in run.output


# --- kit version -------------------------------------------------------------------


def test_rejects_a_missing_kit_version(kit_tree: Path) -> None:
    (kit_tree / ".claude/KIT_VERSION").unlink()

    assert "file is missing; the document set carries no version" in run_gate(kit_tree).output


@pytest.mark.parametrize("value", ["1.0", "v1.0.0", "one"])
def test_rejects_a_kit_version_that_is_not_semantic(kit_tree: Path, value: str) -> None:
    write(kit_tree, ".claude/KIT_VERSION", value + "\n")

    assert f"'{value}' is not a semantic version" in run_gate(kit_tree).output


# --- governed documents ------------------------------------------------------------


def test_rejects_a_missing_required_document(kit_tree: Path) -> None:
    (kit_tree / "docs/decision-format.md").unlink()

    run = run_gate(kit_tree)

    assert "ERROR docs/decision-format.md: governed document is missing" in run.output


def test_a_language_rule_file_is_optional(kit_tree: Path) -> None:
    (kit_tree / ".claude/rules/mql5.md").unlink()

    run = run_gate(kit_tree)

    assert run.code == 0, run.output


# --- client settings ---------------------------------------------------------------


def test_warns_when_the_hook_interpreter_does_not_start(kit_tree: Path) -> None:
    point_hooks_at(kit_tree, "no-such-python-3f9c")

    run = run_gate(kit_tree)

    assert run.code == 0, run.output
    assert "WARN  .claude/settings.json: hook interpreter `no-such-python-3f9c`" in run.output


def test_does_not_probe_hooks_that_run_no_python(kit_tree: Path) -> None:
    settings = kit_tree / SETTINGS
    config = json.loads(settings.read_text(encoding="utf-8"))
    config["hooks"]["PostToolUse"] = [
        {
            "matcher": "Edit",
            "hooks": [{"type": "command", "command": "node", "args": ["format.js"]}],
        }
    ]
    write_json(settings, config)

    run = run_gate(kit_tree)

    assert "`node`" not in run.output
    assert (run.errors, run.warnings) == (0, 0), run.output


def test_settings_that_are_not_json_fail_the_gate(kit_tree: Path) -> None:
    (kit_tree / SETTINGS).write_bytes(b'{ "hooks": ')

    run = run_gate(kit_tree)

    assert run.code == 1, run.output
    assert "ERROR .claude/settings.json: not valid JSON" in run.output


def test_settings_whose_hooks_are_misshapen_fail_the_gate(kit_tree: Path) -> None:
    write_json(kit_tree / SETTINGS, {"hooks": ["not", "a", "mapping"]})

    run = run_gate(kit_tree)

    assert run.code == 1, run.output
    assert "`hooks` is not in the shape Claude Code reads" in run.output


def test_the_interpreter_running_the_tests_is_accepted(kit_tree: Path) -> None:
    point_hooks_at(kit_tree, sys.executable)

    assert "settings.json" not in run_gate(kit_tree).output
