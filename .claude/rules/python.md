---
description: Python naming, typing, structure, tooling, and test conventions
paths: ["**/*.py"]
---

# Python Rules

These rules supplement `CLAUDE.md` and the Constitution; nothing here relaxes either. Universal
rules — determinism, error handling, testing policy, security, time and precision — live in the
Constitution and are **not** repeated here. This file holds only what is specific to Python.

## Naming (PEP 8)

| Scope | Convention | Example |
|---|---|---|
| Variables and functions | `snake_case` | `calculate_position_size`, `total_price` |
| Classes | `PascalCase` | `OrderService`, `RiskCalculator` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT_SECONDS` |
| Modules and packages | `snake_case` | `order_service.py`, `risk_model.py` |
| Non-public | Leading underscore | `_normalise_price` |
| Booleans | `is_` / `has_` / `can_` prefix | `is_active`, `has_session`, `can_retry` |
| Event handlers | `on_` or `handle_` prefix | `on_submit`, `handle_error` |
| Type variables | `PascalCase`, short | `T`, `ItemT` |
| Tests | `test_` prefix, one behaviour per name | `test_rejects_zero_quantity` |

The Constitution's *Naming Conventions* apply in full; Python adds one exception to the
single-letter rule — short type variables (`T`, `KT`) — and the recognised abbreviations `id`,
`url`, `api`.

## Typing

- Type hints on every public function signature, including the return type. The type checker runs
  as a quality gate, so an untyped public function is an unfinished one.
- The type checker runs in strict mode. `Any`, `cast`, and `# type: ignore` each require a one-line
  comment justifying them; a blanket ignore at file level is forbidden (see `CLAUDE.md`, *Gate
  integrity*).
- Prefer precise types: `Sequence`/`Mapping` for read-only parameters, `Literal` and `Enum` over
  bare strings, `TypedDict` or a dataclass over a free-form `dict`, `NewType` for identifiers that
  must not be interchanged.
- Public data structures are `@dataclass(frozen=True)` or equivalent immutable types unless
  mutation is the point.
- Abstractions use `typing.Protocol` for structural contracts, or an ABC where a shared base
  implementation genuinely exists.

## Structure

- Public API is declared explicitly with `__all__`; anything else is internal, and other modules
  never import it.
- Import side effects are forbidden: importing a module must not read files, open connections, read
  the environment, or start work. Entry points do that, guarded by `if __name__ == "__main__":`,
  which itself only wires and delegates.
- No wildcard imports, no mutable default arguments, no module-level mutable state.
- Business logic is importable and testable with no GUI event loop, no server, and no external
  process running. UI code contains zero business logic, zero I/O, and zero decisions.
- Non-deterministic dependencies — clock, randomness, network, filesystem, environment, external
  services — are injected as parameters or constructor arguments, never reached for inside logic.
- Paths use `pathlib`, never string concatenation and never a hardcoded absolute path.
- Resources are acquired with `with` (or `contextlib` helpers), so they are released on every path
  including failure.

## Errors and logging

- Exceptions are typed and domain-specific, rooted in one project base error
  (`ProjectError` → `ValidationError`, `IntegrationError`, …).
- `except` clauses name the narrowest applicable type; bare `except:` and `except Exception: pass`
  are defects. Re-raise with `raise ... from err` so the cause survives.
- `logging` only — never `print` — through the project's logging unit. No f-string interpolation
  into log calls where lazy `%s` formatting applies.

## Async

- An `async def` function never performs blocking work; blocking calls go through
  `asyncio.to_thread` or an executor.
- Every `await` on an external operation has a timeout; every created task is awaited or
  explicitly tracked, never fire-and-forget.
- No mixing of event loops, and no `asyncio.run` inside library code.

## Security

The Constitution's *Security Baseline* governs. These are the Python constructs that violate it
most often, named here so they are caught by a reviewer rather than argued about.

- No `eval`, `exec`, or `compile` on a value that did not originate in the codebase.
- No `pickle`, `marshal`, or `shelve` for data crossing a trust boundary; use JSON or a
  schema-validated format. `yaml.safe_load`, never `yaml.load`.
- `subprocess` is called with an argument list and `shell=False`; a command assembled by string
  formatting is a defect, and `os.system` is never used.
- `secrets`, not `random`, for tokens, keys, salts, and anything an attacker must not predict.
  `random` is for simulation, and its seed is injected like any other non-deterministic input.
- `tempfile.mkstemp` or `TemporaryDirectory`, never a predictable path in a shared temp directory.
- A path derived from external input is resolved and checked against its intended root before use,
  so `..` cannot escape it.
- Every call to an external service sets an explicit timeout and verifies TLS; `verify=False`
  requires a decision record.

## Tooling and tests

- Formatter, linter, type checker, and test suite all pass with clean output; together they are the
  project's Python gate.
- Dependencies are pinned in a committed lockfile, and the project runs inside a virtual
  environment declared there.
- Test policy is defined in the Constitution, *Testing Standards*. Python specifics only:
  - `pytest`, with fixtures for setup rather than `setUp` methods, and `pytest.raises` for expected
    failures — asserting the exception type and its message content.
  - `tests/` mirrors the `src/` layout one-to-one.
  - Substitutes are injected through the function or constructor; patching module internals is a
    last resort and is justified in a comment when used.
  - Parametrise boundary cases instead of copying a test body.
