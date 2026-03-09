param(
  [string]$PythonExe = 'python',
  [string]$SqlPlusExe = 'sqlplus',
  [switch]$RunDbChecks,
  [switch]$RunBilledUsageValidation,
  [switch]$RunDictionaryDiscovery,
  [string]$ConnectString,
  [string]$SchemaOwner = 'CISADM'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$sourceOfTruthScript = Join-Path $repoRoot 'scripts/validate_source_of_truth_sql.py'
$readOnlyGuardScript = Join-Path $repoRoot 'scripts/repo/sql_read_only_guard.py'
$repoAuditScript = Join-Path $repoRoot 'scripts/repo/repo_structure_audit.ps1'
$billedUsageRunner = Join-Path $repoRoot 'scripts/performance/run_billed_usage_validation.ps1'
$dictionaryRunner = Join-Path $repoRoot 'scripts/performance/run_cisadm_dictionary_discovery.ps1'

Push-Location $repoRoot
try {
  Write-Host '=== SQL Quality Workflow: Static Gates ==='
  & $PythonExe $sourceOfTruthScript `
    'sql/performance/billed_usage/validation' `
    'sql/performance/bill_cycle' `
    'sql/reconciliation/billing' `
    'sql/diagnostics/cisadm_dictionary'
  if ($LASTEXITCODE -ne 0) {
    throw "Source-of-truth SQL validation failed with exit code $LASTEXITCODE"
  }

  & $PythonExe $readOnlyGuardScript `
    'sql/performance/billed_usage/validation' `
    'sql/diagnostics/cisadm_dictionary'
  if ($LASTEXITCODE -ne 0) {
    throw "Read-only SQL guard failed with exit code $LASTEXITCODE"
  }

  & $repoAuditScript
  if ($LASTEXITCODE -ne 0) {
    throw "Repo structure audit failed with exit code $LASTEXITCODE"
  }

  Write-Host '=== SQL Quality Workflow: Static gates passed ==='

  if (-not $RunDbChecks) {
    Write-Host 'DB checks skipped (use -RunDbChecks with explicit -ConnectString to enable read-only DB validation).'
    return
  }

  if ([string]::IsNullOrWhiteSpace($ConnectString)) {
    throw 'RunDbChecks requested but ConnectString was not provided.'
  }

  Write-Host '=== SQL Quality Workflow: Read-Only DB Checks ==='
  if ($RunDictionaryDiscovery) {
    & $dictionaryRunner `
      -ConnectString $ConnectString `
      -SchemaOwner $SchemaOwner `
      -SqlPlusExe $SqlPlusExe `
      -PythonExe $PythonExe
    if ($LASTEXITCODE -ne 0) {
      throw "Dictionary discovery failed with exit code $LASTEXITCODE"
    }
  } else {
    Write-Host 'Dictionary discovery skipped (use -RunDictionaryDiscovery to enable).'
  }

  if ($RunBilledUsageValidation) {
    & $billedUsageRunner `
      -ConnectString $ConnectString `
      -SqlPlusExe $SqlPlusExe `
      -PythonExe $PythonExe
    if ($LASTEXITCODE -ne 0) {
      throw "Billed usage validation failed with exit code $LASTEXITCODE"
    }
  } else {
    Write-Host 'Billed usage validation skipped (use -RunBilledUsageValidation to enable).'
  }
}
finally {
  Pop-Location
}
