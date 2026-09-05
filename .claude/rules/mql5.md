---
description: MQL5 naming, correctness, build verification, and live-promotion protocol
paths: ["**/*.mq5", "**/*.mqh"]
---

# MQL5 Rules

These load when an MQL5 file is read, not at every session start; `docs/BOOTSTRAP.md` step 3
proves it happened by reading `logs/instructions-loaded.log`. They supplement `CLAUDE.md` and the
Constitution; nothing here relaxes either. Universal rules — determinism, layering, testing
policy,
error-handling policy, precision, observability — live in the Constitution and are not repeated
here. This file holds what is specific to the MQL5 language and the MetaTrader platform. Machine
facts — paths, commands, operating system, terminal locations — live in `techContext.md`.

## The rule that outranks everything else here

**I never claim MQL5 code compiles, works, or is finished without a real compile log.**
Not once, in either mode below. Reasoning about the code is not verification.

## Naming

| Scope | Convention | Example |
|---|---|---|
| Functions | `PascalCase` | `CalculateLotSize`, `CloseAllPositions` |
| Classes | `C` prefix | `CTradeManager`, `CRiskGuard` |
| Class members | `m_` prefix | `m_magicNumber`, `m_lastError` |
| Input parameters | `Inp` prefix | `InpLotSize`, `InpMagicNumber` |
| Globals | `g_` prefix | `g_tradeManager` |
| Locals | `camelCase` | `openPrice`, `barCount` |
| Constants, macros, enum members | `UPPER_SNAKE_CASE` | `MAX_SLIPPAGE_POINTS` |
| Enum types | `ENUM_` prefix | `ENUM_SIGNAL_DIRECTION` |
| Files | `PascalCase` | `TradeManager.mqh`, `MainExpert.mq5` |
| Booleans | `Is` / `Has` / `Can` prefix | `isTradeAllowed`, `hasOpenPosition` |

Platform-defined handlers (`OnInit`, `OnTick`, `OnTimer`, `OnDeinit`, `OnTester`, `OnChartEvent`)
keep their required names. Abbreviations are forbidden unless universally recognised (`tp`, `sl`,
`atr`).

## Structure and safety

- `.mq5` files are thin entry points: event handlers only, delegating to `.mqh` units.
- **Layering is mandatory and one-directional:** `signal/strategy` (decides) → `risk` (sizes and
  vetoes) → `execution` (places orders) → `logging`. Each layer is a separate `.mqh` unit and
  knows nothing of the layer above it.
- MQL5 has no exceptions. Every trade, indicator, file, and symbol call has its return value
  checked, and every failure logs `GetLastError()` — plus `MqlTradeResult.retcode` for trade
  operations — together with the parameters that produced it. An unchecked return is a defect.
- Trade-server failures are classified before any retry: transient codes (`TRADE_RETCODE_REQUOTE`,
  `TRADE_RETCODE_PRICE_CHANGED`, `TRADE_RETCODE_CONNECTION`, `TRADE_RETCODE_TIMEOUT`) get a bounded
  retry with backoff and a refreshed price; permanent codes (`TRADE_RETCODE_INVALID_STOPS`,
  `TRADE_RETCODE_NO_MONEY`, `TRADE_RETCODE_MARKET_CLOSED`) never retry — they log and surface as a
  failure to the strategy layer.
- Inputs are validated in `OnInit`, which returns `INIT_PARAMETERS_INCORRECT` / `INIT_FAILED`
  rather than trading with bad state. Indicator handles are created once in `OnInit`, never per
  tick, and released in `OnDeinit` (`IndicatorRelease`).
- No hardcoded lot sizes, symbols, magic numbers, slippage, timeframes, or pip distances — all are
  `input` parameters or named constants.
- Trading decisions are a pure function of explicitly passed market state, never of ambient
  terminal state read mid-calculation. Strategy logic does not call `TimeCurrent()`,
  `SymbolInfoDouble()`, or `AccountInfoDouble()` itself; the boundary gathers those and passes
  them in.
- `OnTick` and `OnTimer` complete well inside the event interval: no unbounded loops, no file or
  network I/O, no heavy recomputation per tick, bounded `CopyRates`/`CopyBuffer` counts whose
  returned element count is checked, and recomputation on bar change rather than on every tick.
  Never `Sleep` inside `OnTick`.
- Array orientation is set explicitly with `ArraySetAsSeries` at the point of use; never assume the
  platform default.
- **Prices and volumes are normalised before use:** price to `SYMBOL_DIGITS`, volume to
  `SYMBOL_VOLUME_STEP` and clamped to min/max. Stop distances respect `SYMBOL_TRADE_STOPS_LEVEL`
  and the freeze level, and the filling mode is read from the symbol rather than assumed.
- Doubles are never compared with `==`; comparison uses a named tolerance derived from `_Point` or
  the symbol digits.
- Positions and orders are identified by ticket and by the EA's own magic number; never by index
  assumptions across a loop that can change underneath it.
- `OnInit` reconstructs its view of the world from the terminal's live state —
  `PositionsTotal`/`PositionSelect`, `OrdersTotal`, `HistorySelect` — rather than trusting only
  in-memory or file state carried over from before. A restart, crash, or recompile must never leave
  the EA blind to a position it already opened.
- Each EA instance owns a distinct magic number so it can never act on another instance's
  positions.
- `OnInit` logs a startup banner — version, symbol, timeframe, and every input value — so any
  run or backtest can be reconstructed from its journal alone.
- `OnDeinit` reads the `reason` code before acting: no trade or state-mutating call is relied on to
  complete for `REASON_CHARTCLOSE`, `REASON_CLOSE`, or `REASON_REMOVE`, since the terminal is
  already tearing down and completion cannot be assumed.
- Logging goes through one `Logger.mqh` unit writing structured lines to both the terminal
  journal (`Print`) and a file under `Files/`. Ad-hoc `Print` calls elsewhere are a defect.
- **The log file is bounded.** `Logger.mqh` rotates on a fixed size or on date, keeps a stated
  number of files, and deletes past that. An EA runs for months on a VPS, so an unbounded log is
  a disk-full incident waiting for a quiet weekend. The limits and the retention period are
  recorded in `techContext.md`; see the Constitution, *Observability Standards*.
- Paths are terminal-relative (`Files/`, `MQL5/`), never absolute and never built by string
  concatenation of OS paths.
- `WebRequest` and DLL imports step outside the platform sandbox onto the network and the OS; each
  is enabled only with a decision record naming the exact allowed URL or DLL — never turned on by
  default or left open-ended.

## Toolchain detection

The toolchain depends on the machine. At bootstrap — and again whenever the operating system
differs from the last session — I detect and record in `memory-bank/techContext.md`: OS,
`metaeditor64` path, invocation prefix (none, or `wine`), include directory, terminal path, and
which mode below applies.

I verify the recorded paths still resolve before relying on them. A path that worked last session
on another OS is not evidence.

## Mode A — I compile

Applies where MetaEditor is reachable from my environment, natively or under Wine. **Mode A is the
target state.** Getting it working is a one-time setup task worth doing properly, because every
session afterwards is faster and costs the owner nothing. It is never treated as a per-session
gamble to be abandoned quietly.

- Compile through MetaEditor's command line with the compile, include, and log switches, prefixed
  with `wine` where required. A syntax-only switch exists for fast iteration. The exact commands
  for this machine live in `techContext.md`.
- **I compile in batches, not per edit.** One compile per completed, coherent change set — never
  after each individual file edit. Compilation is the slow step, so a cycle that compiles ten times
  where one would do is a design error on my part.
- **Traps that cost real time if forgotten:**
  - The log is written beside the source file and is **UTF-16** — decode it before reading, never
    `cat` it raw, or the output looks like binary noise. This is a documented exception to the
    Constitution's UTF-8 rule.
  - **MetaEditor may also save sources as UTF-16LE**, which the repository's `text=auto eol=lf`
    normalisation would corrupt. The real encoding of `.mq5`/`.mqh` is measured at bootstrap, not
    assumed, and where it is UTF-16 the `working-tree-encoding` lines in `.gitattributes` are
    enabled and verified by committing one file and reopening it in MetaEditor.
  - On errors no `.ex5` is produced, so a missing or stale binary is itself a failure signal; I
    check the timestamp rather than trusting the log alone.
  - A command-line compile does **not** reload the EA into an already-running terminal. The
    terminal must be restarted, or the file recompiled in the editor, before behaviour changes.
- Pass condition: `0 errors, 0 warnings` in the log **and** a freshly timestamped `.ex5`. I paste
  the real log lines and never paraphrase a compile result.
- Backtesting runs through the terminal's config-file interface; I read the generated report and
  the tester journal. Under Wine this may need a virtual display.
- If the invocation fails on paths, display, or a Wine crash: I retry at most twice, then stop and
  report the exact failure. I do not silently fall back forever. A reproducible Mode A failure
  becomes its own diagnostic task and, once solved, a decision record — so the same obstacle is
  never debugged twice. Mode B covers the interim only, and I say plainly that it is temporary.

## Mode B — the owner compiles

Applies when no MetaEditor is reachable from my environment.

This mode spends the owner's attention, which is the project's scarcest resource. Every rule here
exists to spend less of it.

- **First, remove the copying.** Before relying on repeated manual pastes I propose a one-click
  script that compiles and writes a decoded UTF-8 log to a fixed path. The owner runs it; I read
  the file. If that is possible, the paste ritual is unnecessary and I do not ask for it.
- Where a paste is genuinely needed: open the file in MetaEditor (F4 in the terminal), press **F7**,
  copy the whole **Errors** tab including the "N errors, N warnings" line, and paste it back.
- One request per completed change set, never a running commentary, and never one question at a
  time. I batch everything I need into a single message.
- I treat the paste as ground truth and do not guess while I can ask. For behaviour I request the
  Strategy Tester journal and/or the HTML report.
- **Architectural pressure:** the thinner the MQL5 surface, the fewer compile cycles the owner pays
  for. When a rule or calculation can live in a host language with an automated test suite instead
  of in the EA, that is the cheaper design, and I say so.

## Both modes

- Not `0 errors, 0 warnings` → the task is not finished, and I say so plainly. Warnings are not
  cosmetic in MQL5; they routinely mark type and scope mistakes that still compile.
- Behaviour is judged from Strategy Tester output, never from my reasoning about the code.
- A result from one symbol, timeframe, or date range is not a tested result. I record the exact
  symbol, period, model, spread setting, and date range behind every number I report.
- Logic that cannot be exercised in the tester is extracted into a pure function and tested
  against fixed data — see *Testing* below for how, on a project with no host language.

## Testing

The Constitution's *Testing Standards* apply in full and are not weakened here. MetaTrader ships no
unit-test runner, so this section defines the reachable equivalent; "there is no runner" is never
the end of the sentence.

- **Decision logic is pure and lives in `.mqh`.** A function that takes market state as parameters
  and returns a decision calls nothing from the terminal — no `TimeCurrent`, no `SymbolInfoDouble`,
  no `AccountInfoDouble`. That is what makes it testable at all, and it is already required by
  *Structure and safety*.
- **A test script is the runner.** `Tests/RunTests.mq5` is a script — not an EA — that calls those
  pure functions against fixed fixture arrays, counts assertions, prints `PASSED n / FAILED n` to
  the journal, and writes the same line to `Files/`. It compiles under the same `0 errors, 0
  warnings` condition as the product, and a run reporting zero assertions is a failure, not a pass.
- **The gate quotes real counts.** The recorded gate command compiles the product and the test
  script and runs the script; its output goes to the gate log like any other runtime's. A claim
  about behaviour cites those counts or it is unverified.
- **Where a host language exists in the project**, its suite is preferred for anything that can
  move there: it is faster, runs unattended, and costs the owner nothing. Moving a rule out of the
  EA into that language is the cheaper design, and I say so.
- **What this cannot cover is named, never implied.** Server interaction, fill behaviour, slippage,
  requotes, and connection loss are not reachable from a script. They are covered by named Strategy
  Tester scenarios with their full parameters recorded, and whatever remains untestable is stated
  as untested in the report rather than presented as covered.

## Promotion toward real money

This is the MQL5 instance of `CLAUDE.md`, *Irreversible and high-consequence actions*; that section
governs, and these are its concrete stages. Each stage needs the owner's separate, explicit
approval. I never advance a stage on my own judgement, and I never present a backtest as a
prediction.

| Stage | Gate before advancing |
|---|---|
| Strategy Tester | `0 errors, 0 warnings`; protective logic demonstrated by deliberately triggering it; results recorded with full test parameters |
| Demo account | An agreed minimum run with no unexplained behaviour, no silent errors in the journal, heartbeat visible to the owner |
| Live, smallest size | The owner's written decision stating the exact risk parameters they accept, plus an answered infrastructure-failure question (below) |

**The infrastructure-failure question must be answered before live use, not by me.** Protection that
runs inside the program stops when the program stops: terminal freezes, dropped connections, VPS
reboots, and power loss are certainties over a long enough run. Which mechanism covers that gap —
server-side stops, broker-level limits, external monitoring — what it costs in strategy terms, and
what residual risk is accepted, is a strategy decision belonging to the specification. My duty is to
surface the failure modes, lay out the options with their trade-offs, and record the owner's answer
as a decision. Where residual risk is knowingly accepted, that acceptance is written down, and
capital exposure is sized to it.

Alongside it, a plain-language runbook the owner can follow without me: how to stop trading from the
mobile terminal, how to tell a stalled EA from a quiet market, and who to contact at the broker.

The secrets rule is stated once, in `CLAUDE.md`, *Non-negotiable rules*, and is not restated here.
The MQL5-specific part is only this: I never operate the terminal against a funded account, and
trading parameters change only when the owner states the exact values, which I repeat back and
confirm before applying.
