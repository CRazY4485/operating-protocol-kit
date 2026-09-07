# Changelog

Versions follow semantic versioning as applied to a rule set: a **major** bump changes a rule a
project may already be relying on, a **minor** bump adds a rule or a document, a **patch** bump
clarifies wording without changing what is required. The version in effect on a project is
recorded in its `memory-bank/techContext.md` at bootstrap.

## 3.0.1 — 2026-09-07

A patch bump: it changes nothing a project is required to do, and fixes a defect that made the
`SessionStart` report untrue on any machine whose locale encoding is not UTF-8.

### Fixed

- **The hooks read their stdin payload as UTF-8 rather than as the locale encoding.** Claude Code
  writes the event JSON as UTF-8, but `json.load(sys.stdin)` decodes with the platform's preferred
  encoding, which on Windows is the ANSI code page — `cp1254` on a Turkish or Azerbaijani install.
  A project path holding a non-ASCII character therefore arrived mojibaked. `session-start.py` took
  its root from that path alone, so it resolved to a directory that does not exist and the report
  claimed `.claude/KIT_VERSION is missing` and `git: not a repository` on a project where both were
  present and correct. That is the worst failure this hook can have: a state report the session is
  meant to trust, stating the opposite of the truth, with no error to signal it. Both hooks now
  read the bytes and decode them explicitly.
- **The `SessionStart` hook is handed `${CLAUDE_PROJECT_DIR}` like the other two.** It was the only
  hook deriving the project root from the payload rather than from its arguments, which is why it
  was the only one the decoding defect could disable outright. Arguments arrive already decoded, so
  the root no longer depends on stdin at all; the payload remains the fallback.

## 3.0.0 — 2026-09-05

An external audit checked every claim this kit makes about Claude Code against Anthropic's
documentation. Four claims were wrong, and the enforcement layer did not cover what its own prose
said it did. This release fixes the claims and closes the gaps. It is a major bump because two
changes alter behaviour a project may already rely on: `rm` is now denied outright rather than only
in its `-rf` spelling, and the hooks name `python3` rather than `python`.

### Fixed

- **`/clear` no longer described as returning nothing.** `CLAUDE.md`, `README.md`, the
  `SessionStart` hook's docstring and the `activeContext.md` template all implied that a cleared
  session gets nothing back from disk. Anthropic's memory documentation is explicit that CLAUDE.md
  files and auto memory "are both loaded at the start of every conversation", and `/clear` starts
  one. What a `/clear` actually drops is the plan written in plan mode, the recently read files and
  the transcript — which is still the whole reason the plan lives in `activeContext.md`. The
  paragraph in `CLAUDE.md` also contradicted itself inside three sentences, which its own *Order of
  authority* makes a halt condition.
- **Auto memory is no longer called "invisible to the owner".** It is browsable with `/memory` and
  is plain Markdown. The reason it stays off is narrower and still holds: it lives outside the
  repository and outside git, is machine-local, and is not shared across machines.
- **The `SessionStart` hook read a field that does not exist.** It read `session_start_type`, so
  `source` in its own report was permanently `unknown`. The documented field is `source`. The hook's
  matcher also missed `fork`, so a forked session opened with no state report.
- **The plan section is found by anchor, not by an English heading.** `PLAN_HEADING` matched
  `approved plan` case-insensitively, but `activeContext.md` is translated into the working
  language, so on every non-English project the hook reported "none recorded" while a plan sat in
  the file. The template now carries a `<!-- plan -->` anchor, the hook prefers it, the English
  heading remains as a fallback, and the failure message now says which of the two is missing.
- **The document gate now runs before a PowerShell commit.** `if` holds exactly one permission rule
  and matches one tool's calls, so the single `Bash(git commit *)` handler under a
  `Bash|PowerShell` matcher never fired for commits made through the PowerShell tool. Bash and
  PowerShell now have one handler each.

### Changed

- **Destructive-command rules use the documented wildcard form.** `Bash(git reset --hard*)` and its
  three siblings had no space before the `*`, which makes them prefix matches on the flag rather
  than the canonical trailing wildcard. All four now read `--hard *`, `--force *`, `-f *`, `-fd *`.
- **`rm` is denied outright.** `rm -rf *` and `rm -fr *` covered two spellings of an unbounded set:
  `-r -f`, `-fR`, `-Rf`, `--recursive --force` and the rest all passed. Enumerating them can never
  be complete, so the rule is now `Bash(rm *)`. `git rm` is unaffected.
- **PowerShell has its own deny and ask rules.** `PowerShell` is a separate permission prefix, so
  every `Bash(git ...)` rule left the same command unguarded when run through the PowerShell tool.
  Each destructive git rule now has a `PowerShell` twin, and `Remove-Item * -Recurse*` — which
  matched words beginning with `-Recurse` rather than the flag — is now `PowerShell(Remove-Item *)`.
  PowerShell canonicalises aliases before matching, so `ri`, `rm` and `del` are covered by it.
- **The hooks name `python3`, and the installers rewrite it.** `python` was hard-coded in all three
  hooks, against this kit's own warning that `python.exe` on Windows is often the Microsoft Store
  app-execution alias. A hook Claude Code cannot start is a *non-blocking* error, so all three
  would have failed silently. `install.sh` and `install.ps1` now write the interpreter they already
  probe into `.claude/settings.json`.
- **An empty decision index warns.** With `memory-bank/` present and `decisions.md` holding no rows,
  the gate said nothing, so an install could go green with `BOOTSTRAP.md` step 9 never done. It now
  warns rather than errors, because that state is also the legitimate window before the first
  record is written.
- **Rule files no longer claim to "load automatically".** They load when a matching file is read,
  which is what `BOOTSTRAP.md` step 3 verifies through `logs/instructions-loaded.log`.

### Added

- **The gate now checks that referenced files exist.** `check_references` validated only italic
  cross-references such as *Order of authority*, and stripped every backticked token before looking
  — so a reference to a document that had moved read correctly and pointed nowhere. Two forms are
  now checked: a relative Markdown link target, and a backticked path under `.claude/`, `docs/` or
  `.githooks/`. Both were measured against this document set first and report nothing on it.
  Checking every path-like token instead would have flagged 28 correctly written references, since
  the house style names Memory Bank files by bare name — `techContext.md`, not
  `memory-bank/techContext.md` — so that form stays unchecked and `check_memory_bank` keeps
  covering Tier 1. `CHANGELOG.md` is exempt, because a path that has since moved is correct history
  there.
- **A reference written without its directory prefix is reported with the real path.** A path that
  moved is the rot this kit has actually suffered: 2.0.0 put the gate under `.claude/`, and a
  document still saying `tools/check-docs.py` would have read correctly and pointed nowhere. That
  form is not an unresolvable path but an incomplete one — it is a path-suffix of a file that does
  exist — so any backticked token holding a `/` is now tested for it, and reported as
  "`tools/check-docs.py` is incomplete; the file is at `.claude/tools/check-docs.py`". A token that
  matches nothing stays silent, which is what keeps example identifiers such as `src/` and
  `signal/strategy` out of the findings. `memory-bank/` and `logs/` are held out of the corpus of
  candidate files: the house style names Memory Bank files by shorthand, so `decisions/decisions.md`
  becomes a suffix of the real `memory-bank/decisions/decisions.md` the moment a project bootstraps,
  and without the exclusion the gate would turn red on five references in kit text nobody had
  touched — after the install had already gone green. Both forms were measured against this document
  set and against a bootstrapped project, and report nothing on either.
- `BOOTSTRAP.md` step 3 now proves all three hooks start, not only `InstructionsLoaded`.
- `README.md` describes the three states the document gate reads — pre-bootstrap,
  bootstrap-in-progress, post-bootstrap — so its output changing mid-install is expected.
- `README.md` states that `.gitignore` both stays with the kit and is merged into the project under
  a marker line, which is what the installers have always done.
- `README.md` names `markdown.md` as required rather than one of the deletable language rules.
- `.gitattributes` documents the C# BOM question, with the command that measures it, beside the
  MQL5 encoding block.

## 2.1.1 — 2026-09-05

### Fixed

- The Memory Bank rule and the Task protocol contradicted each other. 2.1.0 made the Approve step
  write the plan into `activeContext.md`, while the rule still said the file changes "for exactly
  two reasons", neither of them Approve. Under `CLAUDE.md`'s own *Order of authority* that is a
  halt condition, so the rule now names four moments: Approve writes the plan, a plan step is
  marked as it verifiably completes, a mid-task stop leaves a next-step note, and Record replaces
  the plan.
- A plan step is now marked the moment it finishes rather than at the end of the task. The owner
  clears the session whenever they choose, not only when told it is safe, so step marks written
  late are step marks lost. Marking a finished step is verified state, not the busywork the same
  rule forbids.

## 2.1.0 — 2026-09-05

The project's session boundary is `/clear`, not `/compact`. The two are not equivalent, and the
document set was written for the wrong one.

### Added

- `docs/templates/activeContext.md`: the Tier 1 file now has a template, and it carries the
  approved plan — goal, files in scope, steps with state, owner check, undo. Every rule that refers
  to "the approved plan" (scope lock, the review step, the owner-check step, a sub-agent's brief)
  previously depended on an artefact that existed only in the conversation, so a cleared session
  could not enforce any of them.
- `.claude/hooks/session-start.py` and a `SessionStart` hook on `startup|clear|resume|compact`. It
  reports the kit version against the recorded one, the Tier 1 files with word counts, the git
  state including `core.hooksPath`, and the open plan, as `additionalContext`. It fails open like
  any hook, so `CLAUDE.md` still owns the cascade.
- `CLAUDE.md`, *Continuity across `/clear`*: what does and does not cross a cleared session, and
  why every continuity mechanism here is a file.
- `CLAUDE.md`, *Git and recovery*: `/rewind` is not the checkpoint. Claude Code's checkpointing
  does not track files changed by bash commands and does not restore a sub-agent's edits, and
  sub-agents are where this protocol puts code writing.
- `docs/BOOTSTRAP.md` step 11: a cleared session must be seen to receive its state report before
  bootstrap is complete.

### Changed

- `autoMemoryEnabled: false` in `.claude/settings.json`. Auto memory survives `/clear` and is
  loaded into every session, but it lives outside the repository and outside git, is machine-local,
  and is invisible to the owner. `CLAUDE.md`'s claim that `memory-bank/` is all that persists was
  false while it was on; turning it off makes the claim true.
- *Session hygiene* is written around `/clear` rather than compaction, and the rule that a session
  never ends leaving the repository in a state the next one cannot resume from is restored. It had
  been dropped in 1.0.0 while trimming to the word budget — a regression introduced by the audit
  work itself.
- The `CLAUDE.md` word budget rises from 4 200 to 4 400 to hold the continuity model. Roughly 130
  words were trimmed first, and the raise is recorded here because the gate's own comment requires
  it: a budget is raised only when the document genuinely needs the room, never to make an
  over-budget file pass.
- *Session start* is shorter: the hook now reports the mechanical checks, so the section states
  what to do about them rather than how to gather them.

## 2.0.0 — 2026-09-05

Breaking: the installed layout changed. A project installed from 1.x moves `tools/check-docs.py`
to `.claude/tools/check-docs.py` and `KIT_VERSION` to `.claude/KIT_VERSION`, then re-runs
`git config core.hooksPath .githooks`.

### Changed

- The kit's machinery moved under `.claude/`, so a project gains three visible entries rather than
  five: `CLAUDE.md`, `docs/` and `memory-bank/`. Each is something a person is meant to read.
  `.githooks/` deliberately stayed outside `.claude/`: it is git's directory, and the layer that
  fails closed must not depend on Claude Code being present.
- `memory-bank/` deliberately stayed at the project root rather than moving under `docs/`. `docs/`
  holds rules copied unchanged into every project; `memory-bank/` holds state that changes every
  task, and its absence is the signal that a project is still pre-implementation.
- The document gate no longer requires the language rule files. A project that uses no MQL5 deletes
  `mql5.md`, and that is a correct install rather than a missing document.

### Added

- `install.sh` and `install.ps1`. They derive the copy set from `git ls-files`, so `.gitignore` is
  the single source of truth and a cache or build artefact can never reach a project; they refuse a
  dirty working tree so the install is reversible; they leave existing files untouched and write
  the kit's version as `<name>.kit-new`; they append to `.gitignore` rather than replacing it; they
  set `core.hooksPath`; and they run the gate once so the install is proven rather than assumed.

## 1.1.0 — 2026-09-05

### Added

- `.githooks/pre-commit`: the document gate as a layer that fails closed. It resolves a Python
  interpreter (`python3`, `python`, or the Windows `py` launcher), probes its version rather than
  trusting the name, and refuses the commit when no usable interpreter is found. Enabled per clone
  with `git config core.hooksPath .githooks`, which `BOOTSTRAP.md` step 1 now performs.

### Changed

- The enforcement story is stated accurately rather than optimistically. Anthropic's hook
  documentation records that a hook which cannot start, or which reaches its timeout, is a
  non-blocking error and that "on `PreToolUse`, a timed-out ... hook doesn't block the tool call".
  The `PreToolUse` run of the gate therefore fails open, and `CLAUDE.md`, `README.md`,
  `.claude/rules/markdown.md` and `BOOTSTRAP.md` now name it a fast signal, with git as the gate.
- `BOOTSTRAP.md` step 10 requires two demonstrated refusals before bootstrap is complete: a deny
  rule firing, and a commit refused by the document gate.
- `Gate integrity` names `git commit --no-verify` among the bypasses that require a decision record.
- The minimum Python version is stated as 3.9, matching what the gate actually needs and what the
  hook probes for.

## 1.0.0 — 2026-09-05

First versioned release. Prior to this the document set carried no version, no changelog and no
git history, so a project could not tell which revision it had been given.

### Added

- `README.md`, `.claude/KIT_VERSION`, `CHANGELOG.md`: entry point, version, and change history.
- `.claude/tools/check-docs.py`: the gate for the governed documents — encoding and line shape, word and
  line budgets, cross-reference resolution, Tier 1 completeness, decision-index integrity, the
  first-person ban, and the presence of a version.
- `.claude/settings.json`: denied destructive commands and secret-file reads, a `PreToolUse` hook
  that blocks a commit whose document gate fails, and an `InstructionsLoaded` hook that logs which
  instruction files actually loaded.
- `.claude/hooks/log-instructions.py`: the hook behind that log.
- `.claude/rules/markdown.md`: the authored-document voice rules, moved out of `CLAUDE.md`, plus
  Markdown mechanics.
- `docs/decision-format.md`: the decision schema, moved out of the Tier 1 index.
- `docs/templates/`: starting files for the decision index, the superseded list, and a sub-agent
  brief.
- `.gitignore`, `.gitattributes`, `.editorconfig`: encoding, line endings, and wrap limits, with a
  documented slot for MQL5 sources should they turn out to be UTF-16.
- `CLAUDE.md`, *Untrusted content*: everything reached through a tool is data, not instruction.
- `CLAUDE.md`, *Session start*: an interrupted bootstrap is now its own case, resumed rather than
  reported as a defect.
- `CLAUDE.md`, *Task protocol*: a short lane for changes that meet four stated conditions.
- `CLAUDE.md`, *Halt and escalate*: an escalation note, so a halt on one part of a task does not
  stop the rest.

### Changed

- `CLAUDE.md`, *Delegation to sub-agents*: corrected. A sub-agent does receive the CLAUDE.md
  hierarchy and project rules; what it lacks is the conversation, the plan, and prior tool results.
  The brief now closes that gap instead of re-sending standards the agent already has.
- Document budgets are stated in words as well as lines, because line count changes with wrapping
  while context cost does not.
- Order of authority now names enforced configuration above every other source, and scopes language
  rules to their own subject matter.
- Constitution: the Open/Closed and Dependency Inversion rules are scoped so they can be followed
  literally; observability gains log rotation, retention, and a test for redaction; numeric
  defaults are labelled as overridable in `techContext.md`.
- `.claude/rules/dotnet.md`: the SDK version is taken from `techContext.md` rather than pinned in
  the rule file, and the naming examples no longer come from one domain.
- `.claude/rules/mql5.md`: a testing approach that is actually reachable on an MQL5-only project,
  plus source-encoding and log-rotation rules.
- `.claude/rules/python.md`: named security prohibitions rather than only the general rule.

### Removed

- `memory-bank/` from the kit itself. Its presence made the session-start cascade report a defect
  and made `BOOTSTRAP.md` unreachable, since bootstrap triggered only on the directory's absence.
