---
description: <Language> naming, structure, gates, and test conventions
paths: ["**/*.<extension>"]
---

# <Language> Rules

<!-- The skeleton for a language that has no rule file yet. Copy it to
.claude/rules/<language>.md, replace every <placeholder>, and delete each comment once its section
is written. CLAUDE.md, *Quality gates*, makes a language with no rule file a blocker; this is how
that blocker is cleared. Hold to what is specific to the language: universal rules live in the
Constitution and are referenced, never restated. A section that does not apply says so and why,
rather than being dropped. It is kept out of .claude/rules/ on purpose: Claude Code loads every
Markdown file there as a rule. -->

These rules supplement `CLAUDE.md` and the Constitution; nothing here relaxes either. Project and
machine facts — versions, paths, commands — live in `techContext.md`, so this file names none of
them.

## The rule that outranks everything else here

<!-- The one claim never made in this language without evidence: what counts as "it builds" or
"it passes", and the log or observation that proves it. -->

## Naming

<!-- One row per scope the language has. The Constitution's *Naming Conventions* apply in full; list
the language's own conventions and any exception to the Constitution, with its reason. -->

| Scope | Convention | Example |
|---|---|---|
| Types | | |
| Functions or methods | | |
| Variables and parameters | | |
| Constants | | |
| Files and modules | | |
| Tests | | |

## Structure

<!-- How a dependency is injected in this language — constructor, parameter, module — where side
effects are allowed, and how a module declares its public surface. -->

## Errors

<!-- The error model: exceptions, result values or error codes; the project's base error; what a
caller must never swallow; how a failure reaches the log. -->

## Security

<!-- The constructs in this language that break the Constitution's *Security Baseline* most often,
named so a reviewer catches them: evaluating strings, deserialising untrusted data, shelling out,
predictable randomness, temporary files, TLS. -->

## Gate and pass condition

<!-- The formatter, linter, type or compile check and test runner, and the exact output that counts
as a pass. The single command that runs them is recorded in techContext.md; this section defines
what that command must contain. -->

## Testing

<!-- The test runner and its conventions. Where the language has none, the reachable equivalent the
Constitution's *Testing Standards* require — extraction into pure functions tested in a host
language, a scripted harness, or a scenario run whose output is the evidence — and what that
equivalent cannot cover. -->
