# Changelog

Versions follow semantic versioning as applied to a rule set: a **major** bump changes a rule a
project may already be relying on, a **minor** bump adds a rule or a document, a **patch** bump
clarifies wording without changing what is required. The version in effect on a project is
recorded in its `memory-bank/techContext.md` at bootstrap.

Each release from 4.0.0 on ends with an *Upgrading* section: the installed files it changes, and
anything a project must do beyond merging them. Re-running an installer on a project writes each
changed file beside the project's copy as `<name>.kit-new`, and copies the *Upgrading* section of
every release newer than the project's into `.claude/KIT_UPGRADE.md`, since this file stays with
the kit.

## 4.0.0 — 2026-09-14

Fixes from the enforcement audit in issue #3, and the defects found while checking it. It is a
major bump because four changes alter what a project may already rely on: `git clean` is denied
outright and force flags are denied in any position; the one gate command is now
`.claude/tools/run-gates.py`, reading the project's `.claude/gates.json`, and a bootstrapped
project without that file fails the gate run; Tier 1 budgets are tuned in
`memory-bank/budgets.json` rather than `techContext.md`; and the gate no longer claims to check
the voice of deliverables, which it never did.

### Fixed

- **The installers no longer rewrite a project's own hooks.** Both installers set the hook
  interpreter by rewriting `command` in every hook that had `args`, and they did it in the
  project's existing `.claude/settings.json` as well as in the `.kit-new` beside it. A project
  hook such as `node format.js` became `python3 format.js`, which Claude Code cannot run and so
  skips without a word. That contradicted the installers' own promise that nothing existing is
  destroyed. They now write the interpreter only into a file the same run wrote: a
  `settings.json` copied into a project that had none, or the `.kit-new`.
- **Both installers try `python3` first.** `install.ps1` tried `py` first, so a Windows install
  wrote `py` into a settings file that is committed and shared, and a teammate on macOS or Linux
  then had no working hooks. `python3` is the only candidate name that exists on all three
  systems. Both installers now probe `python3`, `python`, `py` in the order `.githooks/pre-commit`
  always has, and print a note whenever they write a name other than `python3`.
- **`git clean` is denied outright, and force flags are matched in any position.** 3.0.0 turned
  `git clean -f*` into `git clean -f *`. Under Claude Code's documented wildcard rules the space
  is part of the rule, so `git clean -fdx` — the most common destructive spelling — stopped
  matching, and `-df` and `-xdf` never had. Enumerating flags cannot be complete, which is the
  reason 3.0.0 gave for denying `rm` outright, so `git clean` now gets the same treatment. The
  push rules matched only a force flag written straight after `push`: `git push origin main
  --force`, `git push origin main -f` and a `+main` refspec all passed. They are now
  `git push *--force*`, `git push -f*`, `git push * -f*` and `git push *+*`, and
  `git reset --hard *` is `git reset *--hard*`. Every git rule keeps its `PowerShell` twin.
- **`find … -delete`, `truncate` and `shred` are denied** for `Bash`, beside `rm`.
- **Commands that discard uncommitted work ask first.** `git restore`, `git checkout -- <path>`,
  `git checkout .`, `git checkout -f`, `git switch -f` and `--discard-changes`, `git stash drop`
  and `clear`, and `git branch -D` were neither denied nor asked about, though each can destroy
  work git never saw. They have everyday uses too, so they are `ask` rules rather than `deny`:
  Claude Code stops for the owner before each. A path checked out without `--` cannot be told
  from a branch switch by a pattern and stays uncovered.
- **The first-person check is removed, because it never ran.** It skipped every rule document and
  every path under `.claude/rules/`, and those were the only documents the gate loaded, so it
  returned before its first comparison on every run while `.claude/rules/markdown.md` said the
  gate "greps for these phrases". It is removed rather than aimed at the deliverables: they are
  written in the working language, and an English phrase list would pass nearly all of them. Its
  place in `memory-bank/` is taken by a phrase list the project keeps in its own working language;
  see *Added*. Elsewhere the rule is held by review against the checkable test in `markdown.md`,
  and neither that file nor `CLAUDE.md` claims otherwise.
- **A commit the `PreToolUse` hook blocks now tells Claude why.** On exit 2 Claude Code gives
  Claude the hook's stderr as the reason, and the gate printed its findings to stdout, so Claude
  saw a refused commit and nothing else. With `--hook` the findings now go to stderr.
- **A Markdown link resolves against the directory of the document it is in**, as GitHub and
  every editor resolve it. The gate resolved every link from the repository root, so a correct
  link from `docs/` to a sibling was reported as incomplete, and the path the report suggested
  would have been a broken link. A link that leaves the repository is now an error of its own.
- **`docs/templates/activeContext.md` fits the budget of the file it becomes.** At 433 words it
  was over the 400-word Tier 1 budget of `memory-bank/activeContext.md`, so every project started
  over budget the moment step 5 of `BOOTSTRAP.md` copied it. It is 239 words now: the rationale it
  repeated from `CLAUDE.md` is referenced instead, and the instructions `CLAUDE.md` does not carry
  — keep both anchors through translation, and put nothing but the plan beneath the plan anchor —
  sit in two short comments.
- **A reference in `docs/templates/superseded.md` resolved to nothing.** It named the
  "Alternatives rejected" section, a heading that exists only inside the example record in a
  code block; it now points at *Structure of a record*. The gate found it the first time it read
  the templates.

- **A project can set its Tier 1 budgets, as `CLAUDE.md` always said it could.** `CLAUDE.md`
  said the budgets were "tuned per project in `techContext.md`", but nothing read that file: the
  figures were constants in `check-docs.py`, repeated a second time in `session-start.py`. A
  project that raised a budget and recorded it was still warned against the old figure. The
  figures now live once, in `.claude/tools/kit_config.py`, which both scripts read, and a project
  sets its own in `memory-bank/budgets.json` — a JSON object from Tier 1 file to words. A file
  that is not JSON, names a file that is not Tier 1, or gives anything but a positive whole number
  is an error, and the starting figure stays in force for that file, so a typo can never lift a
  budget silently.

### Changed

- **`.claude/rules/markdown.md` holds writing rules and nothing else.** It carried a `## Gate`
  section — the document gate's checks, and its two enforcement layers — plus clauses naming the
  tool behind individual rules, and an opening sentence on how rule files load. The layers
  repeated `CLAUDE.md`, *Quality gates*, and the loading sentence repeated *Session hygiene*; the
  list of checks belongs beside the checks, at the top of `check-docs.py`, where `CLAUDE.md` now
  points. The file loads whenever a Markdown file is read, in practice every task, so each of the
  261 words it lost was context paid on every one. It is 655 words now, and a test keeps the kit's
  machinery out of it.
- **The language rule files and their skeleton drop the kit's machinery too.** Each opened with
  how rule files load and how step 3 of `BOOTSTRAP.md` proves it — the first half is in *Session
  hygiene*, the second in step 3 itself — and `python.md` and `mql5.md` named `.claude/gates.json`
  as the place their gate is listed. They now state what the language's gate must contain and
  leave where it is listed to the gate runner. The same test covers every rule file and the
  skeleton.

### Added

- **`.claude/tools/run-gates.py`, the one gate command.** `CLAUDE.md` said one command runs every
  gate and appends its output to `logs/gate-<UTC timestamp>.log`, but the kit shipped no such
  command, so the mechanism every claim of evidence rests on was rebuilt by hand in each project.
  The runner runs the document gate, then each gate in `.claude/gates.json` that applies to this
  operating system, from the repository root and with no shell. It streams everything to the
  screen and to one log, and prints the log's path and SHA-256, so a report can cite a hash that
  shows the log is the one the run wrote. It fails on any gate that fails, times out or cannot
  start; on a gate list it cannot use, running none of it; and on a bootstrapped project with no
  gate list, since a runtime with no recorded gate is a blocker. `.claude/gates.json` belongs to
  the project: step 6 of `BOOTSTRAP.md` creates it from `docs/templates/gates.json`, and the
  document gate refuses a malformed one at commit rather than at the next run.
- **The Memory Bank is checked for opinion and narration, in the working language.**
  `memory-bank/` records facts, and an opinion written there as one ("I think…", "məncə…") is
  read by every later session as settled. The project lists the phrases that mark one in
  `memory-bank/voice.json`, copied at bootstrap from `docs/templates/voice.json`, which starts
  with English and Azerbaijani phrases. The gate warns on each it finds, with file and line, outside
  code blocks and only as whole words. Only explicit markers are listed: Azerbaijani marks the
  first person mostly with a verb suffix, and matching suffixes would flag possessives too. It is a
  warning, not an error, because a phrase list cannot tell a quotation from a claim. A missing
  list is a warning of its own; `{"phrases": []}` declares that none are wanted.
- **The last verified change must cite its evidence.** `CLAUDE.md` has the Record step name the
  gate log behind a change, but nothing checked that it did, and a claim with no log is the kind
  that corrupts a project's record fastest. `activeContext.md` now carries a `<!-- verified -->`
  anchor under that heading, found through translation like the plan anchor. The gate warns when
  the section cites no `logs/gate-…log` with a SHA-256, and fails when the cited log is on this
  machine and its hash is not the one cited: the record then claims evidence the log does not
  hold. Logs are git-ignored, so on another clone or in CI the citation is taken as written.
- **The document gate checks `.claude/settings.json`.** A file that is not valid JSON is an
  error: Claude Code ignores it, which drops every deny rule and hook at once. An interpreter
  named by the Python hooks that does not start Python 3.9+ on the machine the gate runs on is a
  warning — a warning rather than an error, because the file is shared and a name that is right
  on one operating system can be missing on another. The gate runs in `.githooks/pre-commit`, so
  the mismatch shows up on the first commit made on such a machine.
- **The templates are gated.** Every `docs/templates/*.md` is checked for shape, references and
  paths like the documents that name them; the four templates bootstrap and delegation copy must
  exist; a Tier 1 template must fit the budget of the file bootstrap makes of it; and the
  `activeContext.md` template must keep the `<!-- plan -->` anchor, with a test holding the gate's
  pattern for it equal to the `SessionStart` hook's.
- **Upgrade steps reach the project.** A project upgrading saw `KIT_VERSION MISMATCH` in its
  state report and had nothing inside it that said what to do: the steps lived only in this file,
  which stays with the kit. Run on a project with an older kit, the installers now copy the
  *Upgrading* section of every newer release, oldest first, into `.claude/KIT_UPGRADE.md`; a
  release before this convention is named with a pointer here instead. The document gate warns and
  the `SessionStart` report says `UPGRADE PENDING` until the file is deleted, and notes already
  pending are never overwritten. The work both installers share — this, and naming the hook
  interpreter — now lives once, in the kit-only `install_support.py`, rather than as the same
  Python embedded in two shells. A project upgrading from 3.x to 4.0.0 gets its notes this way.
- **Unmerged kit files are reported.** A `*.kit-new` an installer left beside a file is a warning
  naming the file to merge it into. It was an untracked file that `git add -A` would commit.
- **`.github/workflows/document-gate.yml` runs the document gate on every push and pull request.**
  `.githooks/pre-commit` binds only in a clone that ran `git config core.hooksPath .githooks`, and
  nothing reported a clone that had not. The workflow is copied into projects; made a required
  status check, which `BOOTSTRAP.md` step 10 now asks the owner for, it holds the gate for every
  clone. `.github/workflows/kit-tests.yml` runs the kit's own suite on Linux with Python 3.9 and
  the newest release, and on Windows, and stays with the kit.
- **The `SessionStart` report flags a `core.hooksPath` that is not `.githooks`.** It flagged the
  setting only when it was unset, so a clone pointed at another hooks directory — where the kit's
  gate runs only if a hook there calls it — reported as healthy.
- **`docs/templates/language-rules.md`**, the skeleton for a language the kit ships no rule file
  for: naming table, structure, errors, security, gate and pass condition, and testing, including
  the reachable equivalent where the language has no test runner. It lives in `docs/templates/`
  rather than `.claude/rules/`, because Claude Code loads every Markdown file there as a rule.
  `CLAUDE.md` names it in the sentence that makes a language without a rule file a blocker: a new
  language usually arrives after bootstrap, when `BOOTSTRAP.md` is no longer read. A
  rule file written from it is gated like the shipped ones, under a default budget of 2 000 words;
  before, the gate read only the rule files it named, so an added language's file was never
  checked at all.
- **A test suite**, under `tests/`, run with `python -m pytest`. Every check the document gate
  makes has a test that plants the defect in a copy of the kit and asserts the finding it must
  produce, so each check is seen to fire rather than assumed to; the installers and the deny rules
  are covered too. The suite belongs to the kit's own repository and is never copied into a
  project.

### Upgrading

Replace outright — a project has no reason to have edited them: `.claude/tools/check-docs.py`,
`.claude/hooks/session-start.py`, `.claude/rules/markdown.md`, `.claude/rules/python.md`,
`.claude/rules/dotnet.md`, `.claude/rules/mql5.md`, `docs/templates/activeContext.md` and
`docs/templates/superseded.md`.
New files, copied as they are: `.claude/tools/kit_config.py`, which `check-docs.py` now needs,
`.claude/tools/run-gates.py`, `docs/templates/gates.json`, `docs/templates/voice.json`,
`docs/templates/language-rules.md` and `.github/workflows/document-gate.yml`.

Merge:

- `.claude/settings.json` — take the kit's `permissions.deny` and `permissions.ask` lists whole,
  and keep the project's own hooks. Keep the hook `command` the installer wrote into the
  `.kit-new`, which is the interpreter it proved on this machine.
- `CLAUDE.md` — *Quality gates*: the one gate command is `run-gates.py`, its log comes with a
  hash, what the document gate checks is listed at the top of `check-docs.py`, and a language
  without a rule file points at `docs/templates/language-rules.md`. *Memory Bank*: Tier 1 budgets
  are tuned in `budgets.json`, not `techContext.md`.
- `docs/BOOTSTRAP.md` — steps 3, 5, 6 and 10.

Then, beyond the merge:

- A `memory-bank/activeContext.md` made from the 3.x template still carries that template's
  preamble, about half of its 400-word budget. Replace the preamble with the two comments of the
  new template, and keep the `<!-- plan -->` anchor where it is. Put `<!-- verified -->` on the
  line after the last-verified-change heading, and cite there the gate log of the last accepted
  change with the SHA-256 `run-gates.py` printed for it; the gate warns until both are there.
- Copy `docs/templates/voice.json` to `memory-bank/voice.json`, and extend it to the working
  language if the list lacks it. Until it exists the gate warns that no phrases are checked.
- The gate command a project recorded in `techContext.md` becomes an entry in
  `.claude/gates.json`, started from `docs/templates/gates.json`; `techContext.md` then records
  `python .claude/tools/run-gates.py` as the one gate command.
- A Tier 1 budget the project raised in `techContext.md` moves to `memory-bank/budgets.json`,
  for example `{"memory-bank/progress.md": 900}`; the gate never read the old place.
- On GitHub, make the job in `.github/workflows/document-gate.yml` a required status check.
- Delete each `.kit-new` once merged; the gate warns about every one still present.

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
