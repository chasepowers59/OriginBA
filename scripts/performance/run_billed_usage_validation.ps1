param(
  [Parameter(Mandatory=$true)]
  [string]$ConnectString,
  [string]$SqlPlusExe = 'sqlplus',
  [string]$ValidationDir = 'sql/performance/billed_usage/validation',
  [string]$ReadOnlyGuardScript = 'scripts/repo/sql_read_only_guard.py',
  [string]$PythonExe = 'python',
  [int]$BudgetRangeASeconds = 45,
  [int]$BudgetRangeBSeconds = 90,
  [int]$BudgetRangeCSeconds = 180,
  [switch]$DisableBudgetEnforcement
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$validationDirPath = Resolve-Path (Join-Path $repoRoot $ValidationDir) -ErrorAction SilentlyContinue
if (-not $validationDirPath) {
  throw "Validation directory not found: $ValidationDir"
}
$validationDirResolved = $validationDirPath.Path

$guardPath = Resolve-Path (Join-Path $repoRoot $ReadOnlyGuardScript) -ErrorAction SilentlyContinue
if (-not $guardPath) {
  throw "Read-only guard script not found: $ReadOnlyGuardScript"
}

$singleRangeScript = Join-Path $validationDirResolved '07_run_single_range.sql'
if (-not (Test-Path $singleRangeScript)) {
  throw "Single-range validation script not found: $singleRangeScript"
}

$preflightScript = Join-Path $validationDirResolved '00_read_only_preflight.sql'
if (-not (Test-Path $preflightScript)) {
  throw "Read-only preflight script not found: $preflightScript"
}

$ranges = @(
  [pscustomobject]@{ Name = 'A'; Start = '2026-01-01'; End = '2026-01-08'; BudgetSeconds = $BudgetRangeASeconds },
  [pscustomobject]@{ Name = 'B'; Start = '2026-01-01'; End = '2026-02-01'; BudgetSeconds = $BudgetRangeBSeconds },
  [pscustomobject]@{ Name = 'C'; Start = '2025-11-01'; End = '2026-02-01'; BudgetSeconds = $BudgetRangeCSeconds }
)

Push-Location $validationDirResolved
try {
  Write-Host "Running SQL read-only guard before DB execution..."
  & $PythonExe $guardPath.Path '.'
  if ($LASTEXITCODE -ne 0) {
    throw "Read-only guard failed with exit code $LASTEXITCODE"
  }

  Write-Host "Running DB read-only privilege preflight..."
  $preflightDriver = @(
    "set define on",
    "set echo on",
    "set timing on",
    "whenever sqlerror exit failure",
    "@00_read_only_preflight.sql",
    "exit"
  ) -join "`n"
  $preflightDriverPath = 'tmp_preflight_run.sql'
  $preflightDriver | Set-Content $preflightDriverPath -Encoding UTF8
  & $SqlPlusExe -S $ConnectString "@tmp_preflight_run.sql"
  if ($LASTEXITCODE -ne 0) {
    throw "Read-only DB preflight failed with exit code $LASTEXITCODE"
  }

  Write-Host "Running billed-usage read-only validation with fail-fast zero-diff gates: $SqlPlusExe"
  Write-Host "Credential source: explicit ConnectString parameter only (no automatic .env loading)."

  $results = @()
  foreach ($r in $ranges) {
    $driverLines = @(
      "set define on",
      "set echo on",
      "set timing on",
      "whenever sqlerror exit failure",
      "spool billed_usage_validation_range_$($r.Name).log",
      "define start_ts = $($r.Start)",
      "define end_ts   = $($r.End)",
      "@07_run_single_range.sql",
      "spool off",
      "exit"
    )
    $driverPath = "tmp_range_$($r.Name)_run.sql"
    ($driverLines -join "`n") | Set-Content $driverPath -Encoding UTF8

    Write-Host "Running range $($r.Name): $($r.Start) -> $($r.End)"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $SqlPlusExe -S $ConnectString "@tmp_range_$($r.Name)_run.sql"
    $exitCode = $LASTEXITCODE
    $sw.Stop()

    if ($exitCode -ne 0) {
      throw "Range $($r.Name) failed with sqlplus exit code $exitCode"
    }

    $elapsed = [math]::Round($sw.Elapsed.TotalSeconds, 2)
    $budgetStatus = if ($DisableBudgetEnforcement) {
      'NOT_ENFORCED'
    } elseif ($elapsed -le $r.BudgetSeconds) {
      'PASS'
    } else {
      'FAIL'
    }

    $results += [pscustomobject]@{
      Range = $r.Name
      StartDate = $r.Start
      EndDate = $r.End
      ElapsedSeconds = $elapsed
      BudgetSeconds = $r.BudgetSeconds
      BudgetStatus = $budgetStatus
    }

    if (-not $DisableBudgetEnforcement -and $budgetStatus -eq 'FAIL') {
      throw "Range $($r.Name) exceeded budget: elapsed=${elapsed}s budget=$($r.BudgetSeconds)s"
    }
  }

  $summaryPath = 'performance_budget_summary.csv'
  $results | Export-Csv -Path $summaryPath -NoTypeInformation
  Write-Host "Validation complete. Range logs: billed_usage_validation_range_*.log"
  Write-Host "Performance summary: $summaryPath"
}
finally {
  Get-ChildItem -Path . -Filter 'tmp_*_run.sql' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
  Pop-Location
}
