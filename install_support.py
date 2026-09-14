#!/usr/bin/env python3
"""Work install.sh and install.ps1 share, written once rather than in two shells.

It belongs to the kit and is never copied into a project. The installers run
it with the interpreter they have just proved:

    install_support.py set-hook-interpreter INTERPRETER SETTINGS_FILE
    install_support.py write-upgrade-notes KIT_DIR PROJECT_DIR

set-hook-interpreter names INTERPRETER in every hook of SETTINGS_FILE that
runs with arguments. The installers pass only a file the same run wrote, so a
project's own settings, and any hook of its own, are never rewritten.

write-upgrade-notes compares the kit version a project has with this kit's.
When the project's is older, it copies the Upgrading section of every release
in between, oldest first, from CHANGELOG.md into the project's
.claude/KIT_UPGRADE.md, which the document gate reports until it is deleted.
Notes already pending are never overwritten: the new ones go beside them as
KIT_UPGRADE.md.kit-new, the way every other file the kit would overwrite does.

Standard library only, like every script in the kit.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

RELEASE = re.compile(r"^## (\d+\.\d+\.\d+)\b.*$", re.MULTILINE)
UPGRADING = re.compile(r"^### Upgrading[ \t]*$", re.MULTILINE)
UPGRADE_NOTES = Path(".claude") / "KIT_UPGRADE.md"
VERSION_FILE = Path(".claude") / "KIT_VERSION"


def version_key(version: str) -> tuple[int, ...]:
    return tuple(int(part) for part in version.split("."))


def set_hook_interpreter(interpreter: str, settings: Path) -> str:
    try:
        config = json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        return f"WARNING: could not read {settings}: {err}"
    changed = 0
    for groups in config.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("args") and hook.get("command") != interpreter:
                    hook["command"] = interpreter
                    changed += 1
    if not changed:
        return f"the hooks in {settings.name} already name {interpreter}"
    try:
        with settings.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError as err:
        return f"WARNING: could not set the hook interpreter in {settings}: {err}"
    return f"set the hook interpreter to {interpreter} in {settings.name} ({changed} hooks)"


def releases(changelog: str) -> list[tuple[str, str]]:
    """Each release heading's version, with the text of its section."""
    headings = list(RELEASE.finditer(changelog))
    sections = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(changelog)
        sections.append((heading.group(1), changelog[heading.end():end]))
    return sections


def upgrade_notes(changelog: str, project: str, kit: str) -> str | None:
    """The notes a project on version `project` needs to reach `kit`; None if it needs none."""
    if version_key(project) >= version_key(kit):
        return None
    wanted = [(version, body) for version, body in releases(changelog)
              if version_key(project) < version_key(version) <= version_key(kit)]
    parts = [
        f"# Kit upgrade {project} -> {kit}\n",
        "Written by the installer from the kit's CHANGELOG.md: what each release below changes in "
        "an\ninstalled project, oldest first. Merge the `.kit-new` files as it says, do the steps "
        "that\nfollow, then delete this file; the document gate warns until it is gone.\n",
    ]
    for version, body in sorted(wanted, key=lambda release: version_key(release[0])):
        upgrading = UPGRADING.search(body)
        if upgrading is None:
            text = ("This release has no Upgrading section; read its entry in the kit's "
                    "CHANGELOG.md.")
        else:
            text = body[upgrading.end():].strip()
        parts.append(f"## {version}\n\n{text}\n")
    return "\n".join(parts)


def write_upgrade_notes(kit: Path, project: Path) -> str | None:
    try:
        project_version = (project / VERSION_FILE).read_text(encoding="utf-8").strip()
        kit_version = (kit / VERSION_FILE).read_text(encoding="utf-8").strip()
        changelog = (kit / "CHANGELOG.md").read_text(encoding="utf-8")
    except OSError:
        return None  # a first install: the project had no kit version to upgrade from
    try:
        notes = upgrade_notes(changelog, project_version, kit_version)
    except ValueError:
        return (f"WARNING: the project's kit version {project_version!r} is not a semantic "
                "version; read the kit's CHANGELOG.md for what changed since it")
    if notes is None:
        return None
    target = project / UPGRADE_NOTES
    if target.exists():
        target = target.with_name(target.name + ".kit-new")
    target.write_bytes(notes.encode("utf-8"))
    relative = target.relative_to(project).as_posix()
    return f"wrote {relative}: what to do to go from {project_version} to {kit_version}"


def main(arguments: list[str]) -> int:
    if len(arguments) == 3 and arguments[0] == "set-hook-interpreter":
        print(set_hook_interpreter(arguments[1], Path(arguments[2])))
        return 0
    if len(arguments) == 3 and arguments[0] == "write-upgrade-notes":
        message = write_upgrade_notes(Path(arguments[1]), Path(arguments[2]))
        if message:
            print(message)
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
