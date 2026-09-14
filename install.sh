#!/bin/sh
# Install the operating-protocol kit into a project.
#
#   ./install.sh [target-directory]      # defaults to the current directory
#
# What it guarantees, in order of importance:
#
#   1. `git config core.hooksPath .githooks` is set. Without it git never runs
#      the pre-commit hook, and the document gate silently stops failing closed
#      while still looking installed. This one command is the main reason this
#      script exists.
#   2. Exactly the right files are copied. README.md, CHANGELOG.md and the two
#      install scripts describe the kit itself and stay with it.
#   3. Nothing existing is destroyed. A file already present in the target is
#      left untouched and the kit's version is written beside it as
#      `<name>.kit-new`, for you to merge. `.gitignore` is appended to, never
#      replaced.
#   4. The install is reversible. The script refuses to run on a dirty working
#      tree, so `git checkout . && git clean -fd` undoes everything it did.
#
# It rewrites no paths: every reference in the kit is relative to the project
# root, and the hooks resolve it themselves at run time.

set -u

KIT=$(cd "$(dirname "$0")" && pwd)
TARGET=${1:-.}

if [ ! -d "$TARGET" ]; then
    printf 'install: target directory does not exist: %s\n' "$TARGET" >&2
    exit 1
fi
TARGET=$(cd "$TARGET" && pwd)

if [ "$KIT" = "$TARGET" ]; then
    printf 'install: target is the kit itself; pass the project directory.\n' >&2
    exit 1
fi

# --- preconditions ---------------------------------------------------------

if ! git -C "$TARGET" rev-parse --git-dir >/dev/null 2>&1; then
    printf 'install: %s is not a git repository.\n' "$TARGET" >&2
    printf 'install: run `git init` there first — the kit requires git for its\n' >&2
    printf 'install: checkpoints, its pre-commit gate, and its recovery model.\n' >&2
    exit 1
fi

if [ -n "$(git -C "$TARGET" status --porcelain)" ]; then
    printf 'install: %s has uncommitted changes.\n' "$TARGET" >&2
    printf 'install: commit or stash them first, so this install can be undone\n' >&2
    printf 'install: with `git checkout . && git clean -fd`.\n' >&2
    exit 1
fi

REPORT=$(mktemp)
trap 'rm -f "$REPORT"' EXIT

# --- copying ---------------------------------------------------------------

copy_one() {
    relative=$1
    source="$KIT/$relative"
    destination="$TARGET/$relative"
    mkdir -p "$(dirname "$destination")"
    if [ ! -e "$destination" ]; then
        cp "$source" "$destination"
        printf 'copied %s\n' "$relative" >>"$REPORT"
        return
    fi
    if cmp -s "$source" "$destination"; then
        printf 'same %s\n' "$relative" >>"$REPORT"
        return
    fi
    cp "$source" "$destination.kit-new"
    printf 'kept %s (kit version written as %s.kit-new)\n' "$relative" "$relative" >>"$REPORT"
}

# The copy set is whatever git tracks in the kit, minus the files that describe
# the kit itself. Deriving it from git means .gitignore is the single source of
# truth: build output, caches and logs can never be copied into a project.
git -C "$KIT" ls-files | while IFS= read -r tracked; do
    case "$tracked" in
        README.md|CHANGELOG.md|install.sh|install.ps1|LICENSE) continue ;;
        tests/*) continue ;;  # the kit's own test suite
        .gitignore) continue ;;  # merged below, never replaced
    esac
    copy_one "$tracked"
done

# .gitignore is merged rather than replaced: a project's own ignores matter.
MARKER='# --- operating-protocol kit ---'
if [ ! -e "$TARGET/.gitignore" ]; then
    { printf '%s\n' "$MARKER"; cat "$KIT/.gitignore"; } >"$TARGET/.gitignore"
    printf 'copied .gitignore\n' >>"$REPORT"
elif grep -qF "$MARKER" "$TARGET/.gitignore"; then
    printf 'same .gitignore (kit block already present)\n' >>"$REPORT"
else
    { printf '\n%s\n' "$MARKER"; cat "$KIT/.gitignore"; } >>"$TARGET/.gitignore"
    printf 'appended .gitignore (kit block added, existing rules kept)\n' >>"$REPORT"
fi

chmod +x "$TARGET/.githooks/pre-commit" 2>/dev/null || true

# --- the step that makes the gate binding ----------------------------------

git -C "$TARGET" config core.hooksPath .githooks
printf 'set core.hooksPath = .githooks\n' >>"$REPORT"

# --- report ----------------------------------------------------------------

printf '\nInstalled into %s\n\n' "$TARGET"
sort "$REPORT" | sed 's/^/  /'

kept=$(grep -c '^kept ' "$REPORT" || true)
if [ "${kept:-0}" -gt 0 ]; then
    printf '\n%s file(s) already existed and were left untouched.\n' "$kept"
    printf 'Their kit versions are beside them as *.kit-new — merge, then delete.\n'
fi

# --- prerequisites the gate needs at commit time ---------------------------

interpreter=""
for candidate in python3 python py; do
    command -v "$candidate" >/dev/null 2>&1 || continue
    if "$candidate" -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" >/dev/null 2>&1; then
        interpreter=$candidate
        break
    fi
done

printf '\n'
if [ -z "$interpreter" ]; then
    printf 'WARNING: no Python 3.9+ interpreter found on PATH.\n'
    printf 'The document gate cannot run, so .githooks/pre-commit will refuse every\n'
    printf 'commit until Python is installed. That is deliberate: the gate fails\n'
    printf 'closed rather than passing unchecked work.\n'
    exit 1
fi

printf 'Gate interpreter: %s (%s)\n' "$interpreter" "$("$interpreter" --version 2>&1)"

# The hooks in .claude/settings.json are exec form: `command` must name a real
# interpreter. The shipped default is `python3`, which a stock Windows install
# does not have, and `python` there is often the Microsoft Store app-execution
# alias rather than an interpreter. Claude Code treats a hook it cannot start as
# a NON-BLOCKING error and proceeds, so a wrong name here disables the hooks
# silently. Write the interpreter this machine just proved instead of guessing.
#
# Only into a file this run wrote: the settings.json it copied into a project
# that had none, or the .kit-new beside the project's own. A settings.json the
# project already had is the project's file - it can hold hooks of its own,
# which a rewrite would point at Python - and it stays byte-for-byte as it was.
settings=""
if grep -qxF 'copied .claude/settings.json' "$REPORT"; then
    settings="$TARGET/.claude/settings.json"
elif grep -qF 'kept .claude/settings.json (' "$REPORT"; then
    settings="$TARGET/.claude/settings.json.kit-new"
fi

if [ -n "$settings" ]; then
KIT_INTERPRETER="$interpreter" "$interpreter" - "$settings" <<'PY'
import json, os, sys

interpreter = os.environ["KIT_INTERPRETER"]
for path in sys.argv[1:]:
    try:
        with open(path, encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, ValueError):
        continue  # absent, or not ours to rewrite
    changed = 0
    for groups in config.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("args") and hook.get("command") != interpreter:
                    hook["command"] = interpreter
                    changed += 1
    if not changed:
        continue
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError:
        print(f"WARNING: could not set the hook interpreter in {path}")
        continue
    print(f"set the hook interpreter to {interpreter} in {os.path.basename(path)} ({changed} hooks)")
PY
    # .claude/settings.json is committed and shared. `python3` is the one name
    # that also exists on macOS and Linux; any other is this machine's alone.
    if [ "$interpreter" != python3 ]; then
        printf 'NOTE: the hooks name `%s`, which may not exist on another operating system.\n' "$interpreter"
        printf 'Where it does not, the hooks fail open there; the document gate warns about it.\n'
    fi
fi

printf 'Running the document gate once, so the install is proven rather than assumed:\n\n'
"$interpreter" "$TARGET/.claude/tools/check-docs.py" --root "$TARGET" || {
    printf '\nThe gate did not pass. Fix the findings above before starting work.\n'
    exit 1
}

printf '\nNext: follow docs/BOOTSTRAP.md from step 1.\n'
