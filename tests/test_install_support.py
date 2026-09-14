"""The installers' shared helper: the upgrade notes it writes, and what it leaves out."""

from __future__ import annotations

from pathlib import Path

from kit_testing import load_script

SUPPORT = load_script(Path("install_support.py"), "install_support")

CHANGELOG = """# Changelog

Intro.

## 4.0.0 — 2026-09-14

Summary.

### Fixed

- Something.

### Upgrading

Replace `a`.

- Merge `b`.

## 3.1.0 — 2026-09-10

### Upgrading

Copy `c`.

## 3.0.1 — 2026-09-07

### Fixed

- A fix.

## 3.0.0 — 2026-09-05

Big.
"""


def test_collects_the_upgrading_sections_of_newer_releases_oldest_first() -> None:
    notes = SUPPORT.upgrade_notes(CHANGELOG, "3.0.1", "4.0.0")

    assert notes is not None
    assert notes.index("## 3.1.0") < notes.index("## 4.0.0")
    assert "Copy `c`." in notes
    assert "Replace `a`.\n\n- Merge `b`." in notes


def test_leaves_out_what_is_not_an_upgrading_section() -> None:
    notes = SUPPORT.upgrade_notes(CHANGELOG, "3.0.1", "4.0.0")

    assert "Something." not in notes
    assert "Summary." not in notes


def test_leaves_out_releases_the_project_already_has() -> None:
    notes = SUPPORT.upgrade_notes(CHANGELOG, "3.1.0", "4.0.0")

    assert "## 3.1.0" not in notes
    assert "## 4.0.0" in notes


def test_names_a_release_that_has_no_upgrading_section() -> None:
    notes = SUPPORT.upgrade_notes(CHANGELOG, "3.0.0", "4.0.0")

    assert "## 3.0.1" in notes
    assert "no Upgrading section" in notes


def test_heads_the_notes_with_both_versions() -> None:
    notes = SUPPORT.upgrade_notes(CHANGELOG, "3.0.1", "4.0.0")

    assert notes.startswith("# Kit upgrade 3.0.1 -> 4.0.0\n")


def test_writes_nothing_when_the_project_is_current_or_newer() -> None:
    assert SUPPORT.upgrade_notes(CHANGELOG, "4.0.0", "4.0.0") is None
    assert SUPPORT.upgrade_notes(CHANGELOG, "4.1.0", "4.0.0") is None


def test_compares_versions_as_numbers_not_text() -> None:
    changelog = "## 3.10.0 — x\n\n### Upgrading\n\nTen.\n\n## 3.9.0 — x\n\n### Upgrading\n\nNine.\n"

    notes = SUPPORT.upgrade_notes(changelog, "3.9.0", "3.10.0")

    assert "Ten." in notes
    assert "Nine." not in notes
