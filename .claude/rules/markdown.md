---
description: Authored-document voice, Markdown mechanics, and the document gate
paths:
  - "**/*.md"
---

# Markdown and Authored Documents

These load when a Markdown file is touched. They supplement `CLAUDE.md` and the Constitution;
nothing here relaxes either. `CLAUDE.md`, *Authored documents*, holds the two process rules —
approval before drafting, and the sub-agent brief. Everything about the prose itself lives here.

## Authored documents — the project's voice, never mine

Deliverables — product documents, specs, roadmaps, plans, reports, user-facing docs — belong to the
project, not to me. They are written in an impersonal project voice and contain only content the
project itself owns. This applies equally to documents a sub-agent drafts: the same rules go into
its brief, and its text is reviewed against them before acceptance.

- **These rule documents are governed documents too.** `CLAUDE.md`, the Constitution, and the rule
  files bind the assistant, so the first person appears in them deliberately and in one form only:
  the assistant's own behaviour commitments ("I never claim a build passes without its log") —
  never opinion, narration, or unprompted guidance. An edit that turns a rule into a narrative is a
  defect.
- **No first person, no narrator** in a project deliverable. No "I recommend", "I believe", "let
  me", "we should". The document states the requirement, decision, or fact itself: "The system
  retries failed payments three times", not "I propose retrying failed payments three times". The
  document gate greps for these phrases, so this rule fails a build rather than a review.
- **No meta-commentary.** Nothing about how the document was produced, what was considered and
  rejected in conversation, what will be done next, or what the reader might ask. A document is
  read long after the conversation ends; anything true only inside the conversation does not belong
  in it.
- **No unprompted guidance.** Recommendations, options, and trade-offs appear only when the
  document's purpose is a proposal — and then as the project's options with a stated basis, never
  as my opinion or advice.
- **Rationale has a home.** Why a decision was made lives in its decision record; the deliverable
  states the decision and references the record, it does not argue it.
- **No leakage between layers.** Process narration and live status belong to `activeContext.md`;
  candidates belong to `backlog.md`. A deliverable contains what is decided and approved, marked
  with its status — never a diary of the work or a broadcast of the assistant's thinking.
- **Checkable test.** Every sentence must survive the question: "would the owner write this
  sentence, as the project, into this document?" If not, it is cut or moved to the layer that owns
  it.

## Mechanics

- **Encoding and shape.** UTF-8, LF endings, one trailing newline, no trailing whitespace —
  enforced by `.gitattributes`, `.editorconfig`, and the gate. See the Constitution, *Portability*.
- **Wrapping.** Governed documents wrap at 100 columns so a diff shows the sentence that changed
  rather than the whole paragraph. `CLAUDE.md` is the single stated exception: its budget is
  measured in lines, so wrapping it would corrupt the measure.
- **Budgets** are declared in `.claude/tools/check-docs.py` and stated in `CLAUDE.md`,
  *Document budgets*. A document over budget is compressed or its budget is challenged; it is
  never quietly exceeded.
- **References name a section, decisions name a number.** A cross-reference is written in
  italics and must match a real heading or bold label somewhere in the document set — the gate
  resolves every one. A decision is cited as `decision 0004`.
- **Fenced code blocks carry a language tag** (` ```text ` where there is no better one), so a
  block is never mistaken for a heading by a parser or a reader.
- **Tables** state units in the header where a column carries one. Numbers in a table are real
  measurements or are marked as examples.
- **Headings** are sentence-shaped and stable: renaming one breaks every reference to it, so a
  rename is a deliberate edit that updates the referring documents in the same change.
- **Working language.** Deliverables and `memory-bank/` are written in the working language
  recorded in `techContext.md`; `CLAUDE.md`, the Constitution, and the rule files are always
  English. Technical tokens are never translated.

## Gate

`python .claude/tools/check-docs.py` is the gate for every governed document, and part of the
project's single gate command. It checks encoding and line shape, word and line budgets,
cross-reference resolution, Tier 1 completeness, the decision index against the decision files,
the first-person ban above, and the presence of `.claude/KIT_VERSION`. It exits non-zero on any
error and prints every finding with its file and line.

It runs in two places. A `PreToolUse` hook in `.claude/settings.json` runs it before any
`git commit` for fast feedback, but Claude Code treats a hook it cannot start, or one that times
out, as a non-blocking error and lets the commit proceed — so that layer fails open and is not
the gate. `.githooks/pre-commit` is the gate: git refuses a commit on any non-zero exit, so a
missing interpreter blocks the commit instead of skipping the check. Enable it once per clone
with `git config core.hooksPath .githooks`. See `CLAUDE.md`, *Quality gates*.
