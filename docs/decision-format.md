# Decision Records — what earns one, and how it is written

Read this when a decision record is about to be written, not on every task. The index,
`memory-bank/decisions/decisions.md`, is Tier 1 and stays a table; this file holds the schema so
the index does not carry it. The immutability rule, the supersede flow, and the obligation to read
a governing decision before changing what it governs are defined in `CLAUDE.md`, *Decisions*, and
are not repeated here.

This file is English, like every rule document. The index and the records themselves are written in
the working language recorded in `techContext.md`; technical tokens stay in English verbatim.

## What earns a record

- Architecture and module boundaries: a decision about where something lives.
- A contract crossing a system boundary: interface, data format, schema, protocol, versioning.
- A dependency choice — what was selected, which alternative was rejected, under which licence and
  obligations.
- Any deviation from the Constitution, with the owner's approval.
- Irreversible operations: the stages, the gate on each stage, the residual risk accepted.
- Protective mechanisms and stop conditions: what stops, who triggers it, how it was demonstrated.
- The exact contents of the pre-authorised zone.
- The resolution of a recurring obstacle, so the same problem is not investigated twice.
- A verified fact about the toolchain or platform that the process depends on — for example
  whether path-scoped rules load in the installed version. A dependency on unverified behaviour is
  the thing a record exists to prevent.

## What earns no record

The value of the log is its brevity; recording everything makes it unreadable and eats the Tier 1
budget.

- Naming, formatting, local refactoring — the code and the gates are their own documentation.
- Technical choices a gate already enforces.
- Ideas and proposals not yet approved → `backlog.md`.
- One-off task detail → the commit message and `progress.md`.

## Format of the index

- Numbers are four digits, zero-padded (`0001`). A number is never reused, not even a withdrawn
  decision's.
- Dates are ISO 8601, UTC (`2026-08-21`).
- Status takes exactly two values: `active`, or `superseded by NNNN`.
- A superseded row moves out of the table into `superseded.md`, where it keeps its line plus the
  successor's number and the supersede date.
- Code and documents cite a decision by number (`decision 0004`), never by title: a title can
  change, a number cannot.
- `tools/check-docs.py` checks that every number in the index has a matching `NNNN-*.md` file and
  that every such file appears in the index.

## Structure of a record (`NNNN-short-title.md`)

```text
# NNNN — Title
Date (UTC) · Status: active | superseded by NNNN · Approved: owner, <date>

## Context
Which problem, which constraints. The facts known at the moment of the decision — not what was
learned afterwards.

## Decision
What was decided. One or two sentences.

## Alternatives rejected
What was considered and why it was not chosen. This section is the most valuable one: it stops the
same alternative from being proposed again.

## Consequences
What became easier, what became harder, which new constraint appeared.

## What this decision forbids
Concretely: what must not be done in future.

## Review trigger
Which event reopens this decision — a measurement crossing a threshold, a dependency going
unmaintained, a requirement changing. If it is left empty, the reason is written; "never" is also
an answer.
```

The filename states the decision's subject, not its outcome (`0002-runtime-exchange-format.md`),
because the outcome can change through supersession while the subject does not.
