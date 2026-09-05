# Architectural Constitution

> Mandatory coding standards for all contributors and AI agents, on any project.
> Non-compliance is a defect. Any deviation requires explicit owner approval and a decision
> record in `memory-bank/decisions/`.
>
> **Scope:** this document governs code and architecture, and only rules that hold regardless of
> stack or domain. Agent workflow, session discipline, verification procedure, and build/test
> commands are governed by `CLAUDE.md`. Language mechanisms and per-language conventions live in
> `.claude/rules/<language>.md`, loaded automatically when a file of that type is touched. Project
> facts — stack, versions, module names, numeric budgets, supported operating systems — live in
> `memory-bank/techContext.md` and `systemPatterns.md`. Rules are not duplicated across these files.
>
> **Generality test:** a rule belongs here only if it would still be correct on a different project
> in a different domain. Domain vocabulary in this document is a defect, not a detail.
>
> **References** name a section, never a number, so renumbering can never mislead a reader.

---

## Clean Code · SOLID · DRY · KISS

### Clean Code
- Every function does **one thing** and does it well; name it after that one thing.
- Functions target 20 lines; 40 is a **smell signal**, not an automatic instruction to split.
  Both figures are defaults and may be replaced in `memory-bank/techContext.md`.
  Past it, either justify the length in one sentence or restructure. Splitting purely to satisfy a
  line count produces shallow helpers that scatter the logic instead of clarifying it — worse than
  the long function was. Validation blocks and platform event handlers are legitimate exceptions.
- No magic numbers or strings — use named constants with clear intent. Any value that changes
  behaviour, identifies something, or carries a unit is a named constant or a configuration input,
  never a literal buried in logic.
- Code must be self-documenting; if a name needs a comment to explain it, rename it.
- Delete dead code rather than commenting it out; version control holds the history.

### SOLID

| Principle | Enforcement Rule |
|-----------|-----------------|
| **S** Single Responsibility | One class / module = one reason to change. |
| **O** Open / Closed | Extend through new code. Modifying stable code is permitted once a test covering its existing behaviour exists and passes; modifying it with no such test is the defect this rule guards against. |
| **L** Liskov Substitution | Subtypes must honour every contract of their base type. |
| **I** Interface Segregation | Prefer multiple small, focused interfaces over one large one. |
| **D** Dependency Inversion | Across a module boundary, and for any collaborator that must be substitutable in a test, depend on an abstraction rather than a concrete type. Within a module, concrete types are used directly. The mechanism for each language is named in its rule file. |

### DRY — Don't Repeat Yourself
- Every piece of knowledge has **one single, authoritative representation** in the codebase.
- Extract repeated logic into shared utilities or base classes; duplication is a defect.
- A constant, format, or schema shared across a process, service, or language boundary is defined
  once on one side and generated, exported, or documented for the other in
  `memory-bank/systemPatterns.md`. Hand-copied duplicates across a boundary are a defect: they
  drift silently and fail at runtime.

### KISS — Keep It Simple, Stupid
- Choose the simplest solution that fully satisfies the requirement.
- Avoid premature optimisation; complexity must be justified by a measurable need.

---

## Separation of Concerns (SOC)

- **Presentation, business logic, and data access** layers are strictly separated.
- UI components contain zero business logic, zero I/O, and zero data queries.
- Business logic must not depend on any framework, toolkit, transport, or vendor construct. A
  logic module that imports a UI toolkit, a database driver, or an external client is a defect.
- **Layering is directional.** Where responsibilities form a pipeline — decide → authorise/size
  → act → observe — each stage is its own unit and knows nothing of the stage above it. The
  concrete stage names for a project are defined in `systemPatterns.md`.
- Each module is responsible for exactly one domain concern.
- Cross-cutting concerns (logging, validation, retries, caching, authorisation) are handled via
  decorators, wrappers, middleware, or a dedicated unit — **never inline, never copy-pasted**.

---

## Deterministic Code

- Same inputs → same outputs, always. No hidden global state, mutable singletons, or implicit
  side effects.
- **Inject every non-deterministic dependency** so behaviour can be controlled in tests: clock,
  randomness, filesystem, network, database, environment, external service state, and any source
  of live data. Logic reaches for none of these directly; it receives them.
- Prefer **pure functions**; push impure operations to the outermost system boundary. An entry
  point gathers state, calls pure decision logic, and hands the result to the effectful layer.
- Ambient state read mid-calculation is a defect: a decision function receives everything it needs
  as parameters, so the same inputs can be replayed exactly.
- Every non-deterministic operation is explicitly labelled and covered by a test using a controlled
  substitute (mock, fake, or fixed dataset).

---

## Modular Structure

```
project-root/
├── CLAUDE.md                     # Process protocol (how work is done)
├── README.md                     # What the document set is, and how it installs
├── KIT_VERSION                   # Recorded in techContext.md at bootstrap
├── docs/
│   ├── ARCHITECTURAL_CONSTITUTION.md
│   ├── BOOTSTRAP.md              # One-time project setup procedure
│   ├── decision-format.md        # What earns a decision record, and its shape
│   └── templates/                # Decision index, superseded list, sub-agent brief
├── .claude/
│   ├── rules/                    # Path-scoped language and document rules
│   ├── hooks/                    # Hook scripts referenced by settings.json
│   └── settings.json             # Denied commands and paths; enforced hooks
├── tools/                        # Gate scripts, starting with check-docs.py
├── logs/                         # Gate evidence, git-ignored, written by the gate
├── memory-bank/                  # Project context and state, created at bootstrap
│   └── decisions/                # Decision index + one file per decision
├── src/<package>/                # Primary runtime
│   ├── modules/                  # Feature modules — each self-contained
│   ├── shared/                   # Reusable utilities, constants, types, base classes
│   ├── services/                 # External integrations: network, storage, other processes
│   ├── config/                   # Configuration and environment binding
│   └── <entry point>             # Application entry point — thin
└── tests/                        # Mirrors the source structure
```

- Each additional runtime or language gets its own top-level directory with the same internal
  discipline: a thin entry point, units of one concern each, and shared code in one place.
- Modules communicate only through their **public API** — never import internals directly. What is
  public is declared explicitly, not implied by whatever happens to be importable.
- Circular dependencies are strictly forbidden; enforce with a linter rule where the language has
  one.
- Entry points contain wiring and platform event handlers only, and delegate immediately; no
  business logic inside them.
- **File size:** 800 lines — a default, replaceable in `techContext.md` — is a smell signal on
  the same terms as function length. Extraction is
  justified by **cohesion** — a name describing something real, used in more than one place or
  genuinely separate in purpose — never by line count. Code pushed into `shared/` only because a
  file grew long creates coupling that did not exist before, and coupling is the expensive mistake,
  not length. Circular dependencies come from the direction of module dependencies, never from
  function size, and are forbidden separately.
- **Architecture preservation:** treat the codebase as production. Priority order:
  Stability → Modularity → Readability → Performance.

### Portability

Code must run unchanged on every operating system and environment listed in
`memory-bank/techContext.md`. Portability is a code rule, not an environment detail.

- No hardcoded absolute paths, drive letters, home directories, or install locations in source
  code. Paths are built with the language's path abstraction, never by string concatenation.
- No OS-specific shell invocations inside application code. Platform differences are confined to
  configuration and to the tooling commands recorded in `techContext.md`, which lists the command
  per operating system.
- Text files are UTF-8 with LF line endings; `.gitattributes` enforces this so the same file does
  not change shape between machines. Any tool that emits or requires another encoding is documented
  as an explicit exception in that tool's rule file, together with how to decode it, and is
  declared per pattern in `.gitattributes` (`working-tree-encoding`) so the repository stays UTF-8
  while the tool keeps working. The real encoding of every source type is measured at bootstrap,
  never assumed.
- Filenames are treated as case-sensitive everywhere, regardless of the host filesystem.
- Any code path that must branch on the operating system does so in one place, behind a named
  function in `shared/`, never scattered through modules.

---

## Naming Conventions

Names carry the design, so they are not a matter of taste. Universal rules:

- Descriptive and unambiguous. No single-letter identifiers outside loop counters, and no
  abbreviations unless universally recognised in the project's domain and listed in
  `systemPatterns.md`.
- The same concept uses the same word everywhere in the system, across every language and
  interface; only the casing convention differs.
- Names carrying a unit or currency say so (`timeout_seconds`, `size_bytes`), so a caller cannot
  guess wrong.
- Booleans read as assertions, event handlers read as events, and a name that needs a comment to
  explain it is renamed instead.
- The per-scope casing tables live in `.claude/rules/<language>.md` and nowhere else, so two
  documents can never disagree.

---

## Error Handling & Logging

### Error handling
- **Never swallow errors silently.** Every failure path either handles, logs, or propagates.
- Where the language has exceptions: a typed hierarchy rooted in one project base error
  (`ProjectError` → `ValidationError`, `NotFoundError`, `IntegrationError`, …); catching is
  narrow, and a bare catch-all that continues is a defect.
- Where the language has no exceptions: **every** call that can fail has its return value checked,
  and each failure logs the platform error code together with the parameters that produced it. An
  ignored return value is a defect.
- Prefer returning errors as values for **expected** failures; reserve exceptions for genuinely
  exceptional conditions.
- **Fail fast at startup.** Invalid configuration, unavailable dependencies, or unmet
  preconditions stop initialisation with a clear message rather than running in a bad state.
- Error messages answer: **what failed**, **why**, and **what to do**.
- Validate all inputs at system boundaries (UI, CLI, entry points, file, socket, and API ingress)
  before they enter business logic. Internal code may then trust its types.
- An error crossing a boundary is translated into that boundary's error vocabulary — never leaked
  as a raw driver, vendor, or platform error to a caller that cannot interpret it.

### Logging
- Use structured logging; levels: `DEBUG` · `INFO` · `WARN` · `ERROR`.
- Every entry includes: `timestamp`, `level`, `component`, `run_id`, `message`.
- `run_id` is generated once per run and propagated across every process, service, and language
  boundary, so a single decision can be traced end to end.
- Logging goes through one logging unit per runtime. Ad-hoc console printing anywhere else in the
  codebase is a defect; a language without a logging library gets a single wrapper unit that
  provides one.
- **Never log** passwords, tokens, API keys, account identifiers, or personally identifiable
  information. Redaction happens in the logging unit, not at each call site.
- Errors at component boundaries include the full stack trace, or — where the language has
  none — the failing call, its parameters, and the platform error code.

---

## Time, Units, and Precision

Silent unit and precision errors survive every review because the code looks correct.

- Time is stored, computed, and logged in **UTC**; local time exists only at a display boundary.
  Timezone conversion happens in one named place.
- Timestamps carry an explicit timezone; a naive local timestamp crossing a boundary is a defect.
- Durations are typed or unit-suffixed, never bare numbers passed between functions.
- **Exact quantities — money, balances, quantised amounts — never use binary floating point.**
  Use the language's decimal or integer-minor-unit representation, decided once and recorded in
  `systemPatterns.md`.
- Floating-point values are never compared with `==`; comparison uses an explicit tolerance defined
  as a named constant.
- Rounding is explicit: the mode and the number of digits are stated at the point of rounding, and
  values are rounded once, at the boundary — never repeatedly through a calculation.

---

## Concurrency and Resource Lifecycle

- Prefer designs with no shared mutable state. Where it is unavoidable, it is guarded by one
  documented mechanism, and the locking order is written down in `systemPatterns.md`.
- Blocking work never runs on an event loop, UI thread, or callback that the platform expects to
  return quickly.
- **Every external call has a timeout.** No unbounded wait, no unbounded queue, no unbounded retry.
- Retries use bounded attempts with backoff, and only on operations that are **idempotent** or
  carry an idempotency key. A retry that can duplicate an effect is a defect.
- Every acquired resource — file, socket, handle, lock, connection, subscription — is released
  deterministically on every path, including the failure path, using the language's scope-bound
  mechanism.
- Long-running work is cancellable, and cancellation leaves state consistent.

---

## Configuration

- Configuration comes from environment variables or configuration files, never from literals in
  code, and is bound in one `config/` unit that the rest of the code depends on.
- Every configuration value is **validated at startup** — presence, type, and range — with a
  clear failure message. Discovering a bad value at first use is too late.
- Every value has a documented default, or is documented as required; the full set is listed in
  `techContext.md`.
- Secrets are read from the environment or a secret store, never committed. See `CLAUDE.md`,
  *Non-negotiable rules*.
- Logic never branches on environment name. Behaviour differences are expressed as named
  configuration flags, so the production path is the path that was tested.

---

## Security Baseline

- **Least privilege** for every credential, token, file permission, and network scope. Nothing runs
  with more authority than the task requires.
- Untrusted input is validated at the boundary and encoded at the point of use — parameterised
  queries and prepared statements only; never string-built commands, queries, or paths.
- No evaluation of untrusted input as code, and no deserialisation of untrusted data into
  executable object graphs.
- Authorisation is checked at the boundary of every operation that changes state or reveals data,
  not inferred from the caller having reached the function.
- **Fail closed:** when an authorisation, validation, or integrity check cannot complete, the
  operation is refused, not allowed.
- Dependencies are audited before and after any change to the dependency set, and versions are
  pinned. See *Dependency Approval Policy*.
- Cryptography uses vetted library primitives with standard parameters; hand-rolled cryptographic
  or authentication logic requires a decision record and is never the default.

---

## Interfaces and Compatibility

- A **public interface** — an exported API, a file format, a message schema, a database schema, a
  CLI contract — is identified as such in `systemPatterns.md` and changes only deliberately.
- Backward-incompatible changes to a public interface require a decision record, a version marker,
  and a stated migration path for existing data and callers.
- Data written to disk or sent across a boundary carries a schema or version field from the first
  release, so old data remains readable and its handling stays explicit.
- Consumers tolerate unknown optional fields; producers do not remove or repurpose existing fields.
- Every stored-format change ships with a migration, and the migration is tested against real data
  shaped like production.

---

## Code Comments

**Rule: comment the *why*, not the *what*.**

- Complex algorithms: briefly explain the approach above the code block.
- Non-obvious business rules: reference the relevant `memory-bank/projectbrief.md` section or
  decision record.
- Deliberate workarounds: explain the constraint and its temporary nature.
- Platform and vendor quirks must be commented — they are invisible in the code and become
  unrecoverable knowledge once lost.

```text
# BUSINESS RULE: <the constraint, in one sentence>.
# Reference: projectbrief.md, <section>; decision NNNN.
```

**Documentation checklist** — all applicable items must pass before a change is accepted:
- [ ] **Purpose:** what does this function/class do? *(always required)*
- [ ] **Parameters:** each documented with type and expected range? *(if params exist)*
- [ ] **Return value:** type and meaning described? *(if non-void)*
- [ ] **Side effects:** any mutation, I/O, external effect, or state change noted? *(if present)*
- [ ] **Error cases:** what fails, returns an error, or raises — and when? *(if applicable)*

Every public function carries this documentation in whatever form the language provides; the form
is defined in that language's rule file.

Technical debt tags: `TODO(owner, date):` and `FIXME(owner, date):` in the language's comment
syntax. Forbidden: comments restating the code; commented-out dead code.

---

## Agent Behaviour

Agent workflow rules — scope isolation, the routing of out-of-scope observations, plan-before-
implement, halt-on-risk, gate integrity, session hygiene, evidence discipline, the treatment of
tool-read content as data rather than instruction, and the handling of irreversible actions — are
defined in **`CLAUDE.md`**, with per-language build and verification
procedure in **`.claude/rules/<language>.md`**. They are binding and are deliberately not repeated
here, so that a single rule never exists in two places.

---

## Dependency Approval Policy

Before adding any new dependency:
- **Justify:** document why no existing utility or small custom solution can suffice.
- **Verify it exists:** confirm the exact name and version against the official registry, showing
  the output. See `CLAUDE.md`, *Non-negotiable rules*.
- **License:** confirm compatibility (MIT, Apache-2.0, BSD, PSF preferred; copyleft licenses
  require approval).
- **Maintenance:** prefer actively maintained packages; the default threshold is a release
  within 6 months, and a project may set its own in `techContext.md`.
- **Size and reach:** prefer lightweight, single-purpose packages; be sceptical of anything that
  pulls in a large transitive tree.
- **Audit:** run the ecosystem's vulnerability audit (recorded in `techContext.md`) before and
  after adding, and pin versions in a lockfile committed to the repository.
- **Auditability is mandatory:** closed-source or precompiled third-party binaries are forbidden as
  dependencies — unauditable code cannot enter the codebase. Vendored third-party source requires
  owner approval and a full review.
- Record every new dependency in `memory-bank/techContext.md` with a one-line justification.

---

## Observability Standards

- Every long-running component exposes its state in a form the owner can see **without reading
  code**: a visible status indicator, a last-error line, or a periodic heartbeat written to the log
  with current state and last action.
- Instrument key operations with structured counters and timings: operations attempted, succeeded,
  rejected, and the latency of every boundary crossing.
- Propagate `run_id` across every component and log line, including across process and language
  boundaries (see *Error Handling & Logging*).
- **No silent failure:** any unrecoverable condition becomes visible to the owner within the same
  session — an `ERROR` log entry plus a user-visible signal in the interface the owner watches.
- Define what counts as a failure state, and how the owner is notified, alongside the feature —
  never as an afterthought.
- **Logs are bounded.** Every log destination has a size or age limit and a rotation policy fixed
  before first use; an unbounded log is a defect that fills a disk on a long enough run. The
  retention period and what may be kept after it are recorded in `techContext.md`.
- **Redaction is tested, not asserted.** The logging unit's redaction of secrets and personal data
  carries a test that feeds it a value that must never appear and asserts the output. A protective
  mechanism with no test that fires it does not exist; see `CLAUDE.md`, *Demonstration, not
  description.*
- **Stop conditions are code, not intentions.** Before a system is allowed to take irreversible
  action unattended, its limits and its kill switch exist as executable logic that has been made to
  fire on purpose. A halt condition that exists only as a written intention does not exist. Which
  limits apply is a project decision; that they exist and are demonstrated is not negotiable.

---

## Performance Budget

Universal rules. Every figure below is a **default**: a project overrides it in
`memory-bank/techContext.md`, and a project that keeps a default records that it did, so the
number in force is always traceable to a decision rather than to this document.

- **The hot path is sacred.** Any handler invoked at high frequency or under a hard deadline
  completes well inside its interval: no unbounded loops over history, no file or network I/O, no
  heavy recomputation per call. Cache what is stable and move periodic work to a scheduled path.
- **The interface never blocks.** Any operation exceeding ~100 ms runs off the interactive thread
  with visible progress; operations exceeding 500 ms become explicit background jobs.
- **Data access:** no N+1 query patterns; batch or paginate all access; unbounded queries are
  forbidden.
- **Caching decisions must be explicit and documented** — never added reactively. Every cache
  states what invalidates it.
- Startup time and memory ceilings are defined before the first release, and a performance claim is
  made only from a measurement, never from reasoning about the code.

---

## Testing Standards

Tests are the only durable safety net for an owner who may not read code. Untested behaviour is
unfinished behaviour, not a shortcut. This section is the single home for test rules; language rule
files add only tooling specifics.

- Every behaviour change ships with a test in the same change. A bug fix begins with a test that
  reproduces the bug and fails before the fix.
- Tests are deterministic (see *Deterministic Code*): no real clock, network, external service, or
  filesystem dependency — injected substitutes and fixed datasets only. An intermittently failing
  test is a defect and is fixed or removed, never re-run until it passes.
- One behaviour per test, stated in its name (`test_rejects_zero_quantity`).
- Tests exercise the public API and observable behaviour, not internal implementation detail, so a
  safe refactor does not break the suite.
- Boundaries and failure paths are tested, not only the happy path: empty, minimum, maximum,
  invalid input, and the error branch of every external call.
- Tests mirror the source structure, so the test for a module is findable without searching.
- Test code follows the same naming and clarity rules as production code, but may exceed the
  function-length limit where a scenario genuinely requires it.
- Coverage figures belong in `memory-bank/techContext.md` and are a diagnostic, never a target to
  be gamed. A high number over untested decision logic is worse than an honest low one.
- Logic that cannot be exercised by the automated suite is extracted into pure functions and tested
  against fixed data; whatever remains untestable is named explicitly in the report, never
  presented as covered.
- **Where a platform has no test runner**, its rule file defines the reachable equivalent —
  extraction into pure functions tested in a host language, a scripted harness, or a scenario run
  whose output is the evidence — and names what that equivalent cannot cover. "No runner exists"
  is never the end of the sentence: either an equivalent is defined, or the gap is an approved
  deviation with a decision record and a stated compensating control.
- Never weaken a test, a type check, or a linter rule to make a change pass. That is a Constitution
  violation regardless of how small the change looks.

---

*This Constitution is the single source of truth for architectural and coding decisions.
It supersedes personal preference. Propose changes to the owner and record the decision
as a decision record before deviating from it.*
