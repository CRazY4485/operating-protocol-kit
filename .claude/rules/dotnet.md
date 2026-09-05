---
description: .NET/WPF naming, correctness, build verification, and MVVM protocol
paths: ["**/*.cs", "**/*.xaml", "**/*.csproj", "**/*.sln"]
---

# .NET / WPF Rules

These load when a .NET or WPF file is read, not at every session start; `docs/BOOTSTRAP.md` step 3
proves it happened by reading `logs/instructions-loaded.log`. They supplement `CLAUDE.md` and the
Constitution; nothing here relaxes either. Universal rules — determinism, layering, testing policy,
error-handling policy, precision, observability — live in the Constitution and are not repeated
here. This file holds what is specific to C#, .NET, and the WPF platform. Project and machine facts
— the target framework and SDK version, paths, commands, operating system, workload installs — live
in `techContext.md`. This file names no version, so it does not need editing when the project moves
to the next one.

## The rule that outranks everything else here

**I never claim .NET/WPF code builds, passes tests, or runs correctly without a real
`dotnet build`/`dotnet test` log, or — for a UI change — the owner having actually looked at the
window.** Reasoning about C# or about what XAML "should" render is not verification.

## Naming

| Scope | Convention | Example |
|---|---|---|
| Classes, records, structs, enums | `PascalCase` | `DocumentService`, `ImportState` |
| Interfaces | `I` prefix, `PascalCase` | `IDocumentService`, `IAuditTrail` |
| Methods, properties, events | `PascalCase` | `CalculateTotalAmount`, `IsConnected` |
| Async methods | `PascalCase` + `Async` suffix | `LoadRecordsAsync` |
| Private fields | `_camelCase` | `_documentService`, `_lastResult` |
| Static private fields | `s_camelCase` | `s_instance` |
| Constants | `PascalCase` | `MaxRetryCount` |
| Locals, parameters | `camelCase` | `startedAt`, `rowCount` |
| Generic type parameters | `T` prefix | `TKey`, `TResult` |
| Namespaces | `PascalCase`, mirrors folder | `Acme.App.Services` |
| Files | `PascalCase`, matches primary type | `DocumentService.cs` |
| Booleans | `Is` / `Has` / `Can` prefix | `IsConnected`, `HasPendingChanges` |
| ViewModels | suffix `ViewModel` | `MainWindowViewModel` |
| Views (Window/Page/UserControl) | suffix matches XAML root | `MainWindow`, `DetailPanelView` |
| Commands (`ICommand` properties) | suffix `Command` | `SaveCommand`, `RefreshCommand` |
| XAML named elements (`x:Name`) | `PascalCase` | `PriceTextBlock`, `SubmitButton` |

Framework-required overrides (`OnStartup`, `OnExit`, `OnClosing`, `Execute`/`CanExecute` on
`ICommand`, `Dispose`) keep their required names. Abbreviations are forbidden unless universally
recognised (`Id`, `Url`, `Io`, `Ui`).

## Structure and safety

- **MVVM is mandatory and one-directional:** View (XAML + code-behind limited to view wiring) →
  ViewModel (presentation state and commands) → Service/Domain layer → Data/Infrastructure
  layer.
  A ViewModel never references a View type; a Service never references a ViewModel.
- Code-behind (`.xaml.cs`) contains only `InitializeComponent` and view-local wiring that binding
  genuinely cannot express (e.g. focus management). Business logic, calculations, and I/O never
  live in code-behind.
- ViewModels expose state through `INotifyPropertyChanged` (or the project's approved
  source-generated equivalent) and expose actions through `ICommand`, never through public methods
  the View calls directly.
- Nullable reference types are enabled project-wide (`<Nullable>enable</Nullable>`). The
  null-forgiving operator (`!`) is a defect unless it carries a comment stating why the compiler is
  wrong.
- No blocking on async code: `.Result`, `.Wait()`, and `.GetAwaiter().GetResult()` on an incomplete
  `Task` are forbidden — they deadlock under WPF's synchronization context. Async runs all the way
  from the UI event to the I/O call.
- `ConfigureAwait(false)` in service/domain/infrastructure code that never touches UI-bound state;
  the default (UI-context) continuation is kept in ViewModel code that resumes by updating a bound
  property, since that continuation needs the UI thread.
- CPU-bound work moves off the UI thread with `Task.Run`; I/O-bound work uses async APIs directly.
  Nothing that can block for more than a frame runs on the dispatcher thread.
- Exceptions are for exceptional cases, not control flow. Every `catch` either handles the
  exception meaningfully or logs and rethrows; an empty `catch` is a defect. Catching
  `System.Exception` is reserved for the top-level boundary, never routine logic.
- Global unhandled-exception handlers are wired at startup —
  `AppDomain.CurrentDomain.UnhandledException`, `Application.DispatcherUnhandledException`,
  `TaskScheduler.UnobservedTaskException` — so a crash is logged before the process dies.
- `IDisposable` follows the standard dispose pattern; every disposable is owned by exactly one
  `using`/`await using`, or by a ViewModel that itself implements `IDisposable` and disposes it. A
  resource with no clear owner is a defect.
- Dependency injection is constructor injection only, wired at the composition root
  (`App.xaml.cs`); no service locator, no mutable `static` service instances.
- `decimal` is used for money and exact quantities; `double` is reserved for values already
  floating-point at the source. Neither is ever compared with `==` where exactness matters —
  comparison uses an explicit tolerance or `decimal`'s exact arithmetic.
- Data bindings name their source explicitly (`RelativeSource`, `ElementName`, or an explicit
  `DataContext` set on the same element) rather than relying on implicit `DataContext` inheritance
  across unrelated controls; a binding with no visible source is a defect waiting for runtime.
- Long-running application state — connection status, in-flight work, pending commands — lives
  in a single injected state or service object, never duplicated across ViewModels: two
  ViewModels reading the same fact read the same instance.
- Logging goes through one abstraction (`ILogger<T>` via `Microsoft.Extensions.Logging`, or the
  project's chosen equivalent) writing structured entries. Ad-hoc `Console.WriteLine` /
  `Debug.WriteLine` calls outside that abstraction are a defect.

## Toolchain detection

The toolchain depends on the machine. At bootstrap — and again whenever the operating system
differs from the last session — I detect and record in `memory-bank/techContext.md`: OS, the
`dotnet` SDK version — which must satisfy the target framework recorded in `techContext.md` —
whether the Windows Desktop workload (`Microsoft.NET.Sdk.WindowsDesktop`) is installed,
IDE/build tooling paths, and which mode below applies.

I verify the recorded paths and SDK version still resolve before relying on them. A path or
version that worked last session on another OS is not evidence.

## Mode A — I build

Applies where the environment is Windows with the Windows Desktop workload installed, so
`dotnet build` / `dotnet test` / `dotnet run` work directly on the WPF project itself. **Mode A is
the target state** for the full solution.

- `dotnet build`, `dotnet test`, and `dotnet run` are invoked directly; exact commands and flags
  live in `techContext.md`.
- I build in coherent batches, not per edit — one build/test cycle per completed change set.
- Pass condition: the build succeeds with zero errors and zero warnings
  (`TreatWarningsAsErrors` is the project default — a warning is a defect, not a style note)
  **and**
  `dotnet test` reports the real pass/fail/skip counts. I paste the actual console output, never a
  paraphrase.
- Running the app for a visual check is requested explicitly whenever a UI change needs the
  owner's eyes — a green build never substitutes for having looked at the window.
- If a build or test run fails on environment grounds (missing workload, SDK mismatch, locked
  file): I retry at most twice, then stop and report the exact failure. A reproducible Mode A
  failure becomes its own diagnostic task and, once solved, a decision record.

## Mode B — the owner builds

Applies when my environment cannot build the WPF target framework directly — most commonly because
it is not Windows. This is expected, not a failure: .NET's cross-platform SDK still builds and
tests everything outside the WPF head.

- **The cross-platform layers are still mine to verify directly.** Any project on the plain
  (non-Windows) target framework — ViewModels, services, domain logic, class libraries — with no
  WPF-specific reference builds and tests through `dotnet build`/`dotnet test` in my own
  environment, no owner involvement needed.
- **Only the WPF head needs the owner.** For the Windows-targeted project itself: I request
  `dotnet build`/`dotnet test` output (or propose a one-click script that runs it and writes the
  log to a fixed path I read), plus a screenshot or short description for visual changes.
- One request per completed change set, batched — never a running commentary.
- I treat the owner's paste or log file as ground truth and do not guess while I can ask.
- **Architectural pressure:** the thinner the WPF surface, the fewer round-trips the owner pays for
  and the more of the solution I verify unaided. Business logic, validation, and calculations
  belong in a plain class library behind an interface; the WPF project references it and
  stays a thin composition of XAML and ViewModel wiring. When a rule can live in that library
  instead of the WPF head, that is the cheaper design, and I say so.

## Both modes

- Not zero errors, zero warnings, and a real test run → the task is not finished, and I say so
  plainly.
- Behaviour is judged from test output and, for UI, an actual run — never from reading XAML or C#
  and reasoning about what it must do.
- A test run on one OS or one SDK patch version is not full verification where the project targets
  more than one; I record the exact SDK version and OS behind every result.
- Logic that is awkward to unit-test inside a ViewModel (timing, dispatcher-dependent code, static
  state) is extracted into a pure, constructor-injected class and unit tested against fixed inputs,
  same as any other layer.

## Release readiness

This is the .NET/WPF instance of `CLAUDE.md`, *Irreversible and high-consequence actions*; that
section governs. Concrete stages here:

| Stage | Gate before advancing |
|---|---|
| Local / Debug | Zero errors, zero warnings, full test suite green, owner has run the app and confirmed the change visually |
| Staging / Release build | `Release`-configuration build verified separately from `Debug` (optimisation, trimming, and nullable behaviour can hide or create bugs), packaged the way it will actually ship (installer / MSIX / self-contained), run once as that package by the owner |
| Production / distributed to real users | Owner's written decision naming the exact release, plus an answered infrastructure-failure question (below) |

**If this application touches a funded account, external money movement, or other safety-critical
infrastructure, the more conservative staged-promotion process governs** — whichever gate is
stricter, here or in a paired system's own rule file — and this table's `Production` stage never
outranks it on its own.

**The infrastructure-failure question, where relevant, is answered before production use, not by
me:** what happens to open state — in-flight work, pending commands, unsent messages — if this
application crashes, loses its connection, or the host machine reboots mid-operation, and who or
what covers that gap. Where residual risk is knowingly accepted, that acceptance is written down.

The secrets rule is stated once, in `CLAUDE.md`, *Non-negotiable rules*, and is not restated
here. The .NET-specific part is only where a secret legitimately lives on this platform: the
Windows Credential Manager or DPAPI, an environment variable, or a git-ignored user-secrets
store — never `App.config`, never a literal, and never a log line.
