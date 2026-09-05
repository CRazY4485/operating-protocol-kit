# Operating Protocol Kit

A copy-in document set that governs how an AI coding assistant works on a project: how work is
planned, verified, recorded, and stopped. It contains no project facts, so it is copied into a new
repository unchanged and configured per project through `memory-bank/techContext.md`.

Version: see `.claude/KIT_VERSION`. Changes: see `CHANGELOG.md`.

`README.md`, `CHANGELOG.md`, `install.sh` and `install.ps1` describe the kit itself and stay
with it. Everything else is copied into the project.

## What each file is, and when it is read

| Path | Read when | Holds |
|---|---|---|
| `CLAUDE.md` | Every session, in full | The process: session start, task cycle, evidence discipline, gates, halt conditions |
| `docs/ARCHITECTURAL_CONSTITUTION.md` | Every code task | Code and architecture standards that hold on any stack |
| `.claude/rules/<language>.md` | When a matching file is touched | Language mechanics, conventions, build and verification procedure |
| `.claude/rules/markdown.md` | When a Markdown file is touched | Authored-document voice and Markdown mechanics |
| `docs/BOOTSTRAP.md` | Once, when implementation begins | One-time project setup, step by step |
| `docs/decision-format.md` | When a decision record is written | What earns a record, and its structure |
| `docs/templates/` | At bootstrap, and per delegation | Starting files for the decision index and sub-agent briefs |
| `.claude/tools/check-docs.py` | Every gate run, and before every commit | The gate for these documents |
| `.claude/settings.json` | Enforced by the client, not read | Denied commands and paths, and the hooks |
| `.claude/KIT_VERSION` | At bootstrap, and at session start | The version of the document set in force |
| `.githooks/pre-commit` | Enforced by git on every commit | The document gate, as the layer that fails closed |
| `memory-bank/` | Tiered, per task | Project state — created at bootstrap, not shipped with the kit |

`memory-bank/` is deliberately absent from the kit. Its absence is what tells the assistant the
project is still pre-implementation; see `CLAUDE.md`, *Session start*.

## Installing it in a project

The script does all six steps below, refuses to touch a dirty working tree so the install is
undoable with `git checkout . && git clean -fd`, and never overwrites a file you already have — it
writes the kit's version beside it as `<name>.kit-new` for you to merge:

```text
./install.sh /path/to/project
.\install.ps1 C:\path\to\project       # the same thing, from PowerShell
```

To do it by hand instead:

1. Copy `CLAUDE.md`, `docs/`, `.claude/`, `.githooks/`, `.gitignore`, `.gitattributes` and
   `.editorconfig` into the repository root — or run `install.sh` / `install.ps1`, which copies
   exactly this set and performs step 3 for you. `README.md` and `CHANGELOG.md`
   describe the kit itself and stay with it; they are not copied. Do not copy `memory-bank/`
   either — bootstrap creates it, and its absence is what marks a project as pre-implementation.
2. Delete the language rule files the project does not use. A language in use with no rule file is
   a blocker, not a gap to fill later.

3. Point git at the committed hooks directory. Git never runs hooks from a directory it has not
   been told about, so this is one command per clone and it is what makes the gate binding:

   ```text
   git config core.hooksPath .githooks
   ```
4. Start a session and run `/context`. The rule files must appear under **Memory files**. The
   `InstructionsLoaded` hook also writes every load to `logs/instructions-loaded.log`, so the
   answer survives the session.
5. Run the document gate. It must pass before any project work begins:

   ```text
   python .claude/tools/check-docs.py
   ```

6. Follow `docs/BOOTSTRAP.md` from step 1. It ends with a stated exit condition and is never read
   again afterwards.

## The two ideas the rest follows from

**Evidence outlives the report.** The owner is assumed not to read code, so a claim is worth
nothing unless it points at something the owner can open unaided: a gate log, a build output, a
running window. The gate writes its own log; the assistant quotes it and gives its path. See
`CLAUDE.md`, *Quality gates*.

**What a tool can enforce does not belong in prose.** Anthropic's documentation is explicit that
instruction files "shape Claude's behavior but are not a hard enforcement layer", while settings
rules "are enforced by the client regardless of what Claude decides to do". Destructive commands
and secret-file reads are therefore configuration in `.claude/settings.json`, not promises in
`CLAUDE.md`.

That configuration has one limit worth stating plainly, because it decides where the gate lives.
Claude Code treats a hook it cannot start — a missing interpreter, a bad path — and a hook that
reaches its timeout as a **non-blocking** error, and the tool call proceeds. A `PreToolUse` hook
therefore fails open and cannot be the last line of defence. Git behaves the other way: any
non-zero exit from `.githooks/pre-commit` refuses the commit. So the document gate runs in both
places — in Claude Code for fast feedback, and in git as the check that actually holds, including
when Python is absent, and including for commits nobody asked Claude to make.

## Requirements

- Git.
- Python 3.9 or later, for `.claude/tools/check-docs.py` and the hook scripts. Standard library only; no
  packages to install. `.githooks/pre-commit` finds it as `python3`, `python`, or the Windows `py`
  launcher, and probes the version rather than trusting the name — on Windows, `python.exe` on
  `PATH` is often the Microsoft Store app-execution alias, which is not an interpreter. If none of
  the three is a real Python 3.9+, the hook refuses the commit instead of skipping the check.
- Git 2.9 or later, for `core.hooksPath`.
- Claude Code recent enough to support `.claude/rules/` with `paths:` frontmatter and the
  `InstructionsLoaded` hook. Step 3 above is the check; if rules do not load, move their content
  into directory-scoped `CLAUDE.md` files beside the code they govern and record which mechanism
  is in use in `techContext.md`.
