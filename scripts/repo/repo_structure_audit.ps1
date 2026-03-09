param(
  [string]$RootPath = (Resolve-Path '.').Path
)

$requiredDirs = @(
  'domains/exports',
  'domains/working',
  'sql/performance/bill_cycle',
  'sql/performance/billed_usage/validation',
  'sql/reconciliation/billing',
  'sql/diagnostics',
  'sql/diagnostics/cisadm_dictionary',
  'scripts/performance',
  'scripts/repo',
  'docs/roadmap',
  'knowledge_base/c2m_cisadm'
)

$missing = @()
foreach ($dir in $requiredDirs) {
  $full = Join-Path $RootPath $dir
  if (-not (Test-Path $full)) {
    $missing += $dir
  }
}

$rootClutter = Get-ChildItem -Path $RootPath -File -Filter '*.zip' | Select-Object -ExpandProperty Name

Write-Host '=== Repo Structure Audit ==='
if ($missing.Count -eq 0) {
  Write-Host '[PASS] Required folders exist.'
} else {
  Write-Host '[FAIL] Missing folders:'
  $missing | ForEach-Object { Write-Host "  - $_" }
}

if ($rootClutter.Count -gt 0) {
  Write-Host '[WARN] Root-level zip artifacts detected:'
  $rootClutter | ForEach-Object { Write-Host "  - $_" }
} else {
  Write-Host '[PASS] No root-level zip clutter detected.'
}

if ($missing.Count -gt 0) { exit 1 }
exit 0
