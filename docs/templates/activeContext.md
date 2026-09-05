# Active context

Copied to `memory-bank/activeContext.md` at bootstrap and translated into the working language
recorded in `techContext.md`. Technical tokens stay in English verbatim.

Read at the start of every task. Budget: ~400 words, checked by
`.claude/tools/check-docs.py`. It holds the state a fresh session needs and nothing else — history
belongs to git, approved work to `progress.md`, candidates to `backlog.md`.

**The plan section is written at the Approve step, before any file is touched, and replaced at the
Record step once the task is accepted.** Everything between the `<!-- plan -->` anchor and the next
heading is read back verbatim by the `SessionStart` hook, so it holds the plan itself and no
commentary. **Keep the anchor when the heading is translated:** the hook finds the section by the
anchor, not by the heading text, so a translated heading without it leaves the hook reporting no
open plan.

**Why the plan lives here.** The session boundary on this project is `/clear`, which starts a new
conversation. Claude Code re-injects the plan mode plan from disk after a *compaction*, but a
cleared session does not get that plan back. Every rule that refers to "the approved plan" — scope
lock, the review step, the owner-check step, a sub-agent's brief — therefore depends on the plan
being a file in this repository. Delete the section when no task is open; do not leave a finished
plan behind.

---

## Last verified change

What was accepted, and the gate log that proves it. One or two lines.

## Approved plan
<!-- plan -->

- **Goal:** one sentence — what is true when this is finished.
- **Files in scope:** the exact paths. Nothing outside this list is touched; see `CLAUDE.md`,
  *Scope lock*.
- **Owner check:** how the owner confirms the change personally, without reading code.
- **Undo:** the checkpoint commit or tag to return to.
- **Decisions that govern this work:** by number, or `none`.

Steps, each marked `[ ]` open, `[x]` done, or `[!]` blocked. A step is marked the moment it is
verifiably finished, not at the end of the task: the owner may clear the session at any point, and
these marks are what the next one resumes from.

- [ ] Step one
- [ ] Step two

## Next step

The single next action, stated so a fresh session can start on it without reconstructing anything.

## Open escalation

What is blocked, the exact answer needed, and what can still be finished without it. Cleared by the
answer, not by time. Delete the section when nothing is blocked. See `CLAUDE.md`,
*Halt and escalate*.
