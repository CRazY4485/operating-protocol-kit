<#
.SYNOPSIS
    Install the operating-protocol kit into a project.

.DESCRIPTION
    What it guarantees, in order of importance:

      1. `git config core.hooksPath .githooks` is set. Without it git never runs
         the pre-commit hook, and the document gate silently stops failing closed
         while still looking installed. This one command is the main reason this
         script exists.
      2. Exactly the right files are copied. README.md, CHANGELOG.md and the two
         install scripts describe the kit itself and stay with it.
      3. Nothing existing is destroyed. A file already present in the target is
         left untouched and the kit's version is written beside it as
         '<name>.kit-new', for you to merge. .gitignore is appended to, never
         replaced.
      4. The install is reversible. The script refuses to run on a dirty working
         tree, so 'git checkout . ; git clean -fd' undoes everything it did.

    It rewrites no paths: every reference in the kit is relative to the project
    root, and the hooks resolve it themselves at run time.

.PARAMETER Target
    The project directory. Defaults to the current directory.

.EXAMPLE
    .\install.ps1 C:\src\my-project
#>

[CmdletBinding()]
param(
    [string]$Target = "."
)

$ErrorActionPreference = "Stop"

$kit = $PSScriptRoot
if (-not (Test-Path -LiteralPath $Target)) {
    Write-Error "install: target directory does not exist: $Target"
    exit 1
}
$Target = (Resolve-Path -LiteralPath $Target).Path

if ($kit -eq $Target) {
    Write-Error "install: target is the kit itself; pass the project directory."
    exit 1
}

# --- preconditions ---------------------------------------------------------

git -C $Target rev-parse --git-dir *> $null
if (-not $?) {
    Write-Host "install: $Target is not a git repository." -ForegroundColor Red
    Write-Host "install: run 'git init' there first - the kit requires git for its"
    Write-Host "install: checkpoints, its pre-commit gate, and its recovery model."
    exit 1
}

$dirty = git -C $Target status --porcelain
if ($dirty) {
    Write-Host "install: $Target has uncommitted changes." -ForegroundColor Red
    Write-Host "install: commit or stash them first, so this install can be undone"
    Write-Host "install: with 'git checkout . ; git clean -fd'."
    exit 1
}

$report = New-Object System.Collections.Generic.List[string]

# --- copying ---------------------------------------------------------------

function Copy-One {
    param([string]$Relative)

    $source = Join-Path $kit $Relative
    $destination = Join-Path $Target $Relative
    $parent = Split-Path -Parent $destination
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }

    if (-not (Test-Path -LiteralPath $destination)) {
        Copy-Item -LiteralPath $source -Destination $destination
        $report.Add("copied $Relative")
        return
    }

    $left = Get-FileHash -LiteralPath $source -Algorithm SHA256
    $right = Get-FileHash -LiteralPath $destination -Algorithm SHA256
    if ($left.Hash -eq $right.Hash) {
        $report.Add("same $Relative")
        return
    }

    Copy-Item -LiteralPath $source -Destination "$destination.kit-new"
    $report.Add("kept $Relative (kit version written as $Relative.kit-new)")
}

# The copy set is whatever git tracks in the kit, minus the files that describe
# the kit itself. Deriving it from git means .gitignore is the single source of
# truth: build output, caches and logs can never be copied into a project.
$kitOnly = @("README.md", "CHANGELOG.md", "install.sh", "install.ps1", "LICENSE", ".gitignore")
foreach ($tracked in (git -C $kit ls-files)) {
    if ($kitOnly -contains $tracked) { continue }
    if ($tracked -like "tests/*") { continue }  # the kit's own test suite
    Copy-One -Relative ($tracked -replace '/', '\')
}

# .gitignore is merged rather than replaced: a project's own ignores matter.
$marker = "# --- operating-protocol kit ---"
$targetIgnore = Join-Path $Target ".gitignore"
$kitIgnore = Get-Content -LiteralPath (Join-Path $kit ".gitignore") -Raw
if (-not (Test-Path -LiteralPath $targetIgnore)) {
    Set-Content -LiteralPath $targetIgnore -Value ($marker + "`n" + $kitIgnore) -Encoding utf8 -NoNewline
    $report.Add("copied .gitignore")
}
elseif ((Get-Content -LiteralPath $targetIgnore -Raw) -like "*$marker*") {
    $report.Add("same .gitignore (kit block already present)")
}
else {
    Add-Content -LiteralPath $targetIgnore -Value ("`n" + $marker + "`n" + $kitIgnore) -Encoding utf8
    $report.Add("appended .gitignore (kit block added, existing rules kept)")
}

# --- the step that makes the gate binding ----------------------------------

git -C $Target config core.hooksPath .githooks
$report.Add("set core.hooksPath = .githooks")

# --- report ----------------------------------------------------------------

Write-Host ""
Write-Host "Installed into $Target"
Write-Host ""
foreach ($line in ($report | Sort-Object)) { Write-Host "  $line" }

$kept = @($report | Where-Object { $_ -like "kept *" }).Count
if ($kept -gt 0) {
    Write-Host ""
    Write-Host "$kept file(s) already existed and were left untouched."
    Write-Host "Their kit versions are beside them as *.kit-new - merge, then delete."
}

# --- prerequisites the gate needs at commit time ---------------------------

# The same order as install.sh and .githooks/pre-commit. `python3` comes first
# because the name ends up in a settings file the whole team shares, and it is
# the one name that also exists on macOS and Linux. A Microsoft Store alias
# that is not a real interpreter fails the version probe and is skipped.
$interpreter = $null
foreach ($candidate in @("python3", "python", "py")) {
    $found = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($null -eq $found) { continue }
    & $candidate -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)" *> $null
    if ($?) { $interpreter = $candidate; break }
}

Write-Host ""
if ($null -eq $interpreter) {
    Write-Host "WARNING: no Python 3.9+ interpreter found on PATH." -ForegroundColor Yellow
    Write-Host "The document gate cannot run, so .githooks/pre-commit will refuse every"
    Write-Host "commit until Python is installed. That is deliberate: the gate fails"
    Write-Host "closed rather than passing unchecked work."
    exit 1
}

$version = & $interpreter --version 2>&1
Write-Host "Gate interpreter: $interpreter ($version)"

# The hooks in .claude\settings.json are exec form: `command` must name a real
# interpreter. The shipped default is `python3`, which a stock Windows install
# does not have, and `python` there is often the Microsoft Store app-execution
# alias rather than an interpreter. Claude Code treats a hook it cannot start as
# a NON-BLOCKING error and proceeds, so a wrong name here disables the hooks
# silently. Write the interpreter this machine just proved instead of guessing.
$env:KIT_INTERPRETER = $interpreter
$patchHooks = @'
import json, os, sys

interpreter = os.environ["KIT_INTERPRETER"]
for path in sys.argv[1:]:
    try:
        with open(path, encoding="utf-8") as handle:
            config = json.load(handle)
    except (OSError, ValueError):
        continue  # absent, or not ours to rewrite
    changed = 0
    for groups in config.get("hooks", {}).values():
        for group in groups:
            for hook in group.get("hooks", []):
                if hook.get("args") and hook.get("command") != interpreter:
                    hook["command"] = interpreter
                    changed += 1
    if not changed:
        continue
    try:
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(config, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
    except OSError:
        print(f"WARNING: could not set the hook interpreter in {path}")
        continue
    print(f"set the hook interpreter to {interpreter} in {os.path.basename(path)} ({changed} hooks)")
'@

# Only into a file this run wrote: the settings.json it copied into a project
# that had none, or the .kit-new beside the project's own. A settings.json the
# project already had is the project's file - it can hold hooks of its own,
# which a rewrite would point at Python - and it stays byte-for-byte as it was.
$settings = $null
if ($report -contains "copied .claude\settings.json") {
    $settings = Join-Path $Target ".claude\settings.json"
}
elseif (@($report | Where-Object { $_ -like "kept .claude\settings.json (*" }).Count -gt 0) {
    $settings = Join-Path $Target ".claude\settings.json.kit-new"
}

if ($null -ne $settings) {
    $patchHooks | & $interpreter - $settings
    if ($interpreter -ne "python3") {
        Write-Host "NOTE: the hooks name '$interpreter', which may not exist on another operating system." -ForegroundColor Yellow
        Write-Host "Where it does not, the hooks fail open there; the document gate warns about it."
    }
}

Write-Host ""
Write-Host "Running the document gate once, so the install is proven rather than assumed:"
Write-Host ""

& $interpreter (Join-Path $Target ".claude\tools\check-docs.py") --root $Target
if (-not $?) {
    Write-Host ""
    Write-Host "The gate did not pass. Fix the findings above before starting work." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Next: follow docs/BOOTSTRAP.md from step 1."
