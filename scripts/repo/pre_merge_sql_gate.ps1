param(
  [string]$PythonExe = 'python'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$workflowScript = Join-Path $repoRoot 'scripts/performance/run_sql_quality_workflow.ps1'

if (-not (Test-Path $workflowScript)) {
  throw "Workflow script not found: $workflowScript"
}

Push-Location $repoRoot
try {
  Write-Host 'Running pre-merge SQL gate (static read-only checks)...'
  & $workflowScript -PythonExe $PythonExe
  if ($LASTEXITCODE -ne 0) {
    throw "Pre-merge SQL gate failed with exit code $LASTEXITCODE"
  }
  Write-Host 'Pre-merge SQL gate passed.'
}
finally {
  Pop-Location
}
