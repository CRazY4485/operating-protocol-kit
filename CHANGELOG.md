# Changelog

Versions follow semantic versioning as applied to a rule set: a **major** bump changes a rule a
project may already be relying on, a **minor** bump adds a rule or a document, a **patch** bump
clarifies wording without changing what is required. The version in effect on a project is
recorded in its `memory-bank/techContext.md` at bootstrap.

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

- `README.md`, `KIT_VERSION`, `CHANGELOG.md`: entry point, version, and change history.
- `tools/check-docs.py`: the gate for the governed documents — encoding and line shape, word and
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
