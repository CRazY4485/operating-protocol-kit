# Bootstrap Protocol — first run only

**Trigger.** Read this when implementation is about to begin and the Memory Bank is not yet
complete — either `memory-bank/` does not exist, or it exists with a Tier 1 file missing because an
earlier bootstrap was interrupted. The second case is a resumption, not a defect report; see
`CLAUDE.md`, *Session start*. An incomplete Memory Bank alone does not mean bootstrap should start:
before implementation a project is legitimately in specification work, and creating a Memory Bank
there is exactly the busywork `CLAUDE.md` forbids (see *Memory Bank*).

It runs once, then never again; `CLAUDE.md` governs everything afterwards. Each step is proposed in
plan mode and approved before execution, per the *Task protocol*, and each finished step is
committed — so an interrupted bootstrap resumes from git state, never from my memory of what I
think I did. Resuming means reading `git log` first and restarting at the earliest step whose
commit is absent.

Nothing here invents project facts. Every value recorded comes from the owner or from verified tool
output; an unknown is asked, never assumed.

1. **Git first, before anything else exists.** `git init`, `.gitignore` (build output, caches,
   compiled artifacts, `logs/`, secrets file), `.gitattributes` (UTF-8, LF), `.editorconfig`,
   `git config core.hooksPath .githooks`, first commit. Every later step is then reversible; a
   bootstrap that sets up the repository last has done its riskiest work unprotected.
2. **Establish the ground facts with the owner.** The specification document; which runtimes and
   languages the project uses; which operating systems it must run on and which the owner works
   from; the working language for conversation and the Memory Bank; deadlines; and any external
   platform, service, or toolchain the project depends on. These answers shape every later step, so
   they are asked in order where one shapes another (see `CLAUDE.md`, *Asking questions*).
3. **Install the documents, then prove they load.** Place the Constitution, this file, and
   `decision-format.md` in `docs/`; install a rule file in `.claude/rules/` for each language in
   use, plus `markdown.md`. Then verify loading with evidence, not assumption:
   - Run `/context` and confirm each file appears under **Memory files**.
   - Read `logs/instructions-loaded.log`, written by the `InstructionsLoaded` hook, and confirm the
     rule files appear there with their load reason. A path-scoped rule loads when a matching file
     is read, so the check is: touch a file of that type, then look again.
   - A rule file that does not appear is not a rule. If path-scoped rules are unsupported in the
     installed version, move their content to a directory-scoped `CLAUDE.md` beside the code they
     govern.
   - Record which mechanism is in use, and the version of Claude Code that was checked, in
     `techContext.md` and as a decision record. This is a platform fact the whole process depends
     on, and an unverified platform fact is the thing a decision record exists to prevent.
4. **Create the layout** defined in the Constitution's *Modular Structure*, one tree per runtime,
   with `tests/` mirroring the source structure from the first commit rather than added later.
5. **Create the memory-bank files in the working language**, in this order because each inherits
   from the last: `projectbrief.md` distilled from the specification first, then
   `productContext.md`, `systemPatterns.md`, `techContext.md`, then `progress.md` and an empty
   `backlog.md`, and finally — copied from `docs/templates/` and translated — `activeContext.md`,
   `decisions/decisions.md` and `decisions/superseded.md`. Confirm each with the owner: everything
   downstream inherits errors made here, so accuracy beats speed. Record the value of
   `.claude/KIT_VERSION` in `techContext.md`, so a later session can see whether the project is
   running an outdated document set. `techContext.md` is filled progressively through steps 6 to
   8 and confirmed complete at the end.
6. **Build the verification command before building features.** One command per runtime runs that
   language's full gate set — as its rule file defines it — plus the document gate
   `python .claude/tools/check-docs.py`, and prints a clear pass or fail. It appends its full
   output to `logs/gate-<UTC timestamp>.log`, so every later claim of mine points at a file the
   owner can open rather than at a message they must trust. Record it in `techContext.md` for
   every operating system in use, and confirm the owner can run it themselves and read the result
   without help. This command comes before the first feature, not after it.
7. **Measure the encodings, do not assume them.** For each source type in use, check what the
   toolchain actually writes on disk — some editors emit UTF-16 — and record the result in
   `techContext.md`. Where it is not UTF-8, declare it per pattern in `.gitattributes` with
   `working-tree-encoding`, then verify by committing one file and reopening it in that toolchain.
   See the Constitution, *Portability*.
8. **Establish each toolchain as a task of its own, not an afterthought.** For any runtime with a
   build, compile, or deploy step, determine whether I can run it directly from my environment. If
   I can, record the exact commands and, where useful, a one-command script that writes a readable
   log to a fixed path. If I cannot, record why, note plainly that the owner-assisted mode is
   temporary, and leave the diagnosis in `backlog.md`. Every session in an assisted mode spends the
   owner's attention, which is the project's scarcest resource, so this is worth real effort now.
   The per-language procedure lives in that language's rule file.
9. **Record the first decisions while the reasoning is still fresh:** repository layout, the
   contract at each boundary between runtimes or services, the toolchain and verification mode, the
   rule-loading mechanism verified in step 3, and the pre-authorised zone the owner grants. A
   decision made before the log exists is a decision that will be forgotten. What earns a record is
   listed in `docs/decision-format.md`.
10. **Install the enforced configuration, and prove the gate refuses.** Two layers ship with the
    document set. `.claude/settings.json` holds the denied destructive commands and secret-file
    reads, `autoMemoryEnabled: false`, and three hooks: `InstructionsLoaded` from step 3, a
    `PreToolUse` run of the document gate, and `SessionStart`, which reports the project's state
    into a fresh session. Claude Code lets a hook it cannot start fail open, so this layer is a
    fast signal, not the gate. `.githooks/pre-commit` is the gate, and git refuses the commit on
    any non-zero exit. Confirm `core.hooksPath` is set, extend the deny list with anything this
    project must never run, then demonstrate two refusals in front of the owner: a deny rule
    firing, and a commit refused by the document gate. A protection the owner has not watched work
    does not count as installed.
11. **Prove the session survives `/clear`.** With a plan recorded in `activeContext.md`, clear the
    session and confirm the state report names the kit version, the Tier 1 files, the git state and
    the open plan. This is the project's continuity model, and an untested continuity model is an
    assumption. See `CLAUDE.md`, *Continuity across `/clear`*.

**Exit condition.** Bootstrap is finished only when all of these are true, and I state each with
its evidence: the verification command runs clean, writes its log, and the owner has run it
themselves at least once; the rule files are confirmed loaded, with the log line to show it; every
Tier 1 memory-bank file exists and the owner has confirmed its content; the interpreter behind the
gate, the kit version and the encodings are recorded in `techContext.md`; the first decisions are
recorded; `core.hooksPath` is set, both a deny rule and a gate refusal have been seen to fire, and
a cleared session has been seen to receive its state report;
and the repository is committed with the `last-good` tag on that commit. Then the first real task
goes through the *Task protocol*, and this file is never read again.
