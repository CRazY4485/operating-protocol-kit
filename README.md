# Operating Protocol Kit

A copy-in document set that governs how an AI coding assistant works on a project: how work is
planned, verified, recorded, and stopped. It contains no project facts, so it is copied into a new
repository unchanged and configured per project through `memory-bank/techContext.md`.

Version: see `.claude/KIT_VERSION`. Changes: see `CHANGELOG.md`.

`README.md`, `CHANGELOG.md`, `install.sh`, `install.ps1` and their shared helper
`install_support.py` describe or install the kit itself and stay with it, as do its test suite,
`tests/`, and the workflow that runs it, `.github/workflows/kit-tests.yml`. Everything else is
copied into the project.

## What each file is, and when it is read

| Path | Read when | Holds |
|---|---|---|
| `CLAUDE.md` | Every session, in full | The process: session start, task cycle, evidence discipline, gates, halt conditions |
| `docs/ARCHITECTURAL_CONSTITUTION.md` | Every code task | Code and architecture standards that hold on any stack |
| `.claude/rules/<language>.md` | When a matching file is touched | Language mechanics, conventions, build and verification procedure |
| `.claude/rules/markdown.md` | When a Markdown file is touched | Authored-document voice and Markdown mechanics |
| `docs/BOOTSTRAP.md` | Once, when implementation begins | One-time project setup, step by step |
| `docs/decision-format.md` | When a decision record is written | What earns a record, and its structure |
| `docs/templates/` | At bootstrap, per delegation, and per new language | Starting files for the Memory Bank, sub-agent briefs, and a new language's rule file |
| `.claude/tools/check-docs.py` | Every gate run, and before every commit | The gate for these documents |
| `.claude/tools/run-gates.py` | Whenever the gates run — it is the one gate command | The document gate, then the project's own gates, into one log with its SHA-256 |
| `.claude/tools/kit_config.py` | By the gate, the runner and the `SessionStart` hook | Tier 1 budgets, and the reading of `budgets.json` and `gates.json` |
| `.claude/gates.json` | Whenever the gates run | The project's own gate commands — created at bootstrap, not shipped with the kit |
| `.claude/settings.json` | Enforced by the client, not read | Denied commands and paths, and the hooks |
| `.claude/KIT_VERSION` | At bootstrap, and at session start | The version of the document set in force |
| `.githooks/pre-commit` | Enforced by git on every commit | The document gate, as the layer that fails closed |
| `.github/workflows/document-gate.yml` | Run by GitHub on every push and pull request | The document gate, for a clone that never enabled the hook |
| `.claude/hooks/session-start.py` | Every session start, `/clear` included | The state report a fresh session opens with |
| `memory-bank/` | Tiered, per task | Project state — created at bootstrap, not shipped with the kit |

`memory-bank/` is deliberately absent from the kit. Its absence is what tells the assistant the
project is still pre-implementation; see `CLAUDE.md`, *Session start*.

## Installing it in a project

The script does the mechanical steps below — copying, the hook interpreter, `core.hooksPath` and
the first gate run. It refuses to touch a dirty working tree so the install is undoable with
`git checkout . && git clean -fd`, and never overwrites a file you already have — it writes the
kit's version beside it as `<name>.kit-new` for you to merge. Run on a project that has an older
kit, it also writes `.claude/KIT_UPGRADE.md`: the *Upgrading* section of every newer release,
since `CHANGELOG.md` stays with the kit. The document gate and the `SessionStart` report both flag
that file until it is deleted:

```text
./install.sh /path/to/project
.\install.ps1 C:\path\to\project       # the same thing, from PowerShell
```

To do it by hand instead:

1. Copy `CLAUDE.md`, `docs/`, `.claude/`, `.githooks/`, `.github/workflows/document-gate.yml`,
   `.gitattributes` and `.editorconfig` into the repository root. `README.md` and `CHANGELOG.md`
   describe the kit itself and stay with it; they are not copied. Do not copy `memory-bank/`
   either — bootstrap creates it, and its absence is what marks a project as pre-implementation.
   `.gitignore` is the one file that is neither purely the kit's nor purely the project's: it stays
   with the kit *and* goes into the project, and it is **merged, never replaced**. Append the kit's
   `.gitignore` under a `# --- operating-protocol kit ---` marker line, keeping the project's own
   rules above it. `install.sh` and `install.ps1` do exactly this, and skip the append when the
   marker is already there.
2. Delete the *language* rule files the project does not use — `python.md`, `dotnet.md`, `mql5.md`.
   A language in use with no rule file is a blocker, not a gap to fill later;
   `docs/templates/language-rules.md` is the skeleton for writing one. `markdown.md` is not
   in that set and is never deleted: the kit's own governed documents are Markdown, so the gate
   treats it as required.

3. Point git at the committed hooks directory. Git never runs hooks from a directory it has not
   been told about, so this is one command per clone and it is what makes the gate binding:

   ```text
   git config core.hooksPath .githooks
   ```
4. Name a real interpreter in the three hooks of `.claude/settings.json`. They ship naming
   `python3`, which a stock Windows install does not have. Where `python3 --version` fails, set
   each hook's `command` to the interpreter that works — `py` on a stock Windows install. The
   installers do this themselves, and only in a file they wrote.
5. Start a session and run `/context`. The rule files must appear under **Memory files**. The
   `InstructionsLoaded` hook also writes every load to `logs/instructions-loaded.log`, so the
   answer survives the session.
6. Run the document gate. It must pass before any project work begins:

   ```text
   python .claude/tools/check-docs.py
   ```

   The gate reads three states, and which one it is in depends on `memory-bank/`, so its output
   changes as the install progresses. **Pre-bootstrap:** `memory-bank/` is absent, the gate checks
   the kit's own documents only, and that is a pass — the absence is the signal that the project is
   pre-implementation, not a missing file. **Bootstrap in progress:** `memory-bank/` exists, so the
   Tier 1 files are now required; a missing or empty one is an error, and an empty decision index is
   a warning until step 9 of `BOOTSTRAP.md` fills it. **Post-bootstrap:** every Tier 1 file is
   present and within budget, and the decision index matches the records on disk. Expect the gate to
   start reporting more, not less, once bootstrap begins.

7. Follow `docs/BOOTSTRAP.md` from step 1. It ends with a stated exit condition and is never read
   again afterwards.

## The three ideas the rest follows from

**Evidence outlives the report.** The owner is assumed not to read code, so a claim is worth
nothing unless it points at something the owner can open unaided: a gate log, a build output, a
running window. The gate runner writes its own log and prints the log's SHA-256; the assistant
quotes the log and gives its path and hash. See `CLAUDE.md`, *Quality gates*.

**What a tool can enforce does not belong in prose.** Anthropic's documentation is explicit that
instruction files "shape Claude's behavior but are not a hard enforcement layer", while settings
rules "are enforced by the client regardless of what Claude decides to do". Destructive commands
and secret-file reads are therefore configuration in `.claude/settings.json`, not promises in
`CLAUDE.md`.

Those rules match the command text of a tool call, so they have a documented edge: a rule covers
the spellings it names, and `Bash` and `PowerShell` are separate prefixes needing separate rules.
That is why `rm` and `git clean` are denied outright rather than flag by flag, why the force flags
of `git push` and the `--hard` of `git reset` are matched wherever they stand in the command, and
why every destructive git rule is written twice. Commands that discard uncommitted work but have
everyday uses too — `git restore`, `git checkout -- <path>`, `git stash drop`, `git branch -D`
and their kin — are `ask` rules instead, so Claude Code stops for the owner before each one. A
path checked out without `--` (`git checkout src/app.py`) cannot be told from a branch switch by a
pattern and is not covered, and PowerShell matches case-insensitively, so there `git branch -d`
asks too. `tests/test_settings.py` lists the spellings each rule must catch and the everyday
commands it must not. It is also why they stop at the tool
boundary — a permission rule governs what Claude runs, not what a script Claude ran goes on to do.
For enforcement below that line, Anthropic points at
[sandboxing](https://code.claude.com/docs/en/sandboxing), which is an OS-level boundary
and outside this kit's scope.

That configuration has one limit worth stating plainly, because it decides where the gate lives.
Claude Code treats a hook it cannot start — a missing interpreter, a bad path — and a hook that
reaches its timeout as a **non-blocking** error, and the tool call proceeds. A `PreToolUse` hook
therefore fails open and cannot be the last line of defence. Git behaves the other way: any
non-zero exit from `.githooks/pre-commit` refuses the commit. So the document gate runs in both
places — in Claude Code for fast feedback, and in git as the check that actually holds, including
when Python is absent, and including for commits nobody asked Claude to make. Git runs that hook
only in a clone told to, so `.github/workflows/document-gate.yml` runs the gate once more on every
push and pull request; made a required status check, it keeps a failing change out of the default
branch whatever the clone it came from was configured to do.

**Continuity is a file, or it is nothing.** This project's session boundary is `/clear`, which
starts a new conversation. Anthropic's documentation lists what a *compaction* re-injects from
disk — the project CLAUDE.md, unscoped rules, auto memory, the plan written in plan mode, recently
read files. A `/clear` is narrower: both memory mechanisms load at the start of every conversation,
so CLAUDE.md, unscoped rules and auto memory come back, but the plan written in plan mode, the
recently read files and the conversation itself do not. So the approved plan lives in
`memory-bank/activeContext.md` rather than in the transcript, and a `SessionStart` hook puts the
project's state in front of Claude before the first turn. Auto memory is turned off in
`.claude/settings.json` for a narrower reason: it does survive `/clear`, but it lives outside the
repository and outside git, is machine-local and is not shared across machines, so it cannot hold a
record the owner is meant to audit.

## Requirements

- Git 2.9 or later, for `core.hooksPath`.
- Python 3.9 or later, for `.claude/tools/check-docs.py` and the hook scripts. Standard library
  only; no packages to install. `.githooks/pre-commit` finds it as `python3`, `python`, or the
  Windows `py` launcher, and probes the version rather than trusting the name — on Windows,
  `python.exe` on `PATH` is often the Microsoft Store app-execution alias, which is not an
  interpreter. If none of the three is a real Python 3.9+, the hook refuses the commit instead of
  skipping the check.
- The three hooks in `.claude/settings.json` cannot probe: they name one interpreter, and that file
  is shared through git. The installers write the one they proved on the machine they ran on,
  trying `python3` first because it is the only one of the three names that also exists on macOS
  and Linux. The document gate warns whenever the named interpreter does not start Python 3.9+ on
  the machine the gate runs on, so a team spanning operating systems sees the mismatch instead of
  losing its hooks silently.
- Claude Code recent enough to support `.claude/rules/` with `paths:` frontmatter, the
  `InstructionsLoaded` hook, and two fields on a hook entry: `args`, which runs `command` directly
  with no shell, and `if`, which filters a tool event by permission-rule syntax. All are in the
  [hooks reference](https://code.claude.com/docs/en/hooks). The `/context` step above is the
  check; if rules do not load, move their content into directory-scoped `CLAUDE.md` files beside
  the code they govern and record which mechanism is in use in `techContext.md`.
