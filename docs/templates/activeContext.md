# Active context

<!-- Copied to memory-bank/activeContext.md at bootstrap and translated into the working language.
What it holds and when it changes: CLAUDE.md, *Memory Bank*. Why the plan lives here: CLAUDE.md,
*Continuity across `/clear`*. -->

## Last verified change

What was accepted, and the gate log that proves it. One or two lines.

## Approved plan
<!-- Keep the anchor below when this heading is translated: the SessionStart hook finds the plan by
the anchor, not by the heading, and reads everything from it to the next heading verbatim. -->
<!-- plan -->

- **Goal:** one sentence — what is true when this is finished.
- **Files in scope:** the exact paths. Nothing outside this list is touched; see `CLAUDE.md`,
  *Scope lock*.
- **Owner check:** how the owner confirms the change personally, without reading code.
- **Undo:** the checkpoint commit or tag to return to.
- **Decisions that govern this work:** by number, or `none`.

Steps, each marked `[ ]` open, `[x]` done, or `[!]` blocked the moment that is verifiably true.

- [ ] Step one
- [ ] Step two

## Next step

The single next action, stated so a fresh session can start on it without reconstructing anything.

## Open escalation

What is blocked, the exact answer needed, and what can still be finished without it. Delete the
section when nothing is blocked; see `CLAUDE.md`, *Halt and escalate*.
