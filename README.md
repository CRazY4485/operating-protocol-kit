# Operating Protocol Kit

A copy-in document set that governs how an AI coding assistant works on a project: how work is
planned, verified, recorded, and stopped. It contains no project facts, so it is copied into a new
repository unchanged and configured per project through `memory-bank/techContext.md`.

Version: see `KIT_VERSION`. Changes: see `CHANGELOG.md`.

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
| `tools/check-docs.py` | Every gate run, and before every commit | The gate for these documents |
| `.claude/settings.json` | Enforced by the client, not read | Denied commands and paths, and the hooks |
| `memory-bank/` | Tiered, per task | Project state — created at bootstrap, not shipped with the kit |

`memory-bank/` is deliberately absent from the kit. Its absence is what tells the assistant the
project is still pre-implementation; see `CLAUDE.md`, *Session start*.

## Installing it in a project

1. Copy `CLAUDE.md`, `docs/`, `.claude/`, `tools/`, `KIT_VERSION`, `.gitignore`, `.gitattributes`
   and `.editorconfig` into the repository root. Do not copy `memory-bank/`; bootstrap creates it.
2. Delete the language rule files the project does not use. A language in use with no rule file is
   a blocker, not a gap to fill later.
3. Start a session and run `/context`. The rule files must appear under **Memory files**. The
   `InstructionsLoaded` hook also writes every load to `logs/instructions-loaded.log`, so the
   answer survives the session.
4. Run the document gate. It must pass before any project work begins:

   ```text
   python tools/check-docs.py
   ```

5. Follow `docs/BOOTSTRAP.md` from step 1. It ends with a stated exit condition and is never read
   again afterwards.

## The two ideas the rest follows from

**Evidence outlives the report.** The owner is assumed not to read code, so a claim is worth
nothing unless it points at something the owner can open unaided: a gate log, a build output, a
running window. The gate writes its own log; the assistant quotes it and gives its path. See
`CLAUDE.md`, *Quality gates*.

**What a tool can enforce does not belong in prose.** Anthropic's documentation is explicit that
instruction files "shape Claude's behavior but are not a hard enforcement layer", while settings
rules "are enforced by the client regardless of what Claude decides to do". Destructive commands,
secret-file reads, and the document gate are therefore configuration in `.claude/settings.json`,
not promises in `CLAUDE.md`.

## Requirements

- Git.
- Python 3.10 or later, for `tools/check-docs.py` and the hook scripts. Standard library only; no
  packages to install.
- Claude Code recent enough to support `.claude/rules/` with `paths:` frontmatter and the
  `InstructionsLoaded` hook. Step 3 above is the check; if rules do not load, move their content
  into directory-scoped `CLAUDE.md` files beside the code they govern and record which mechanism
  is in use in `techContext.md`.
