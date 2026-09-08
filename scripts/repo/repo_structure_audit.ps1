param(
  [string]$RootPath = (Resolve-Path '.').Path
)

# The machine-enforced structure contract. Rewritten 2026-09-08 with the reorganization
# (docs/roadmap/repository_structure_standard.md is the prose form). Two checks:
#   1. the directories every tool, CI gate and index doc pins must exist;
#   2. no SQL, XML or script outside archive/ may name a retired snapshot table.

$requiredDirs = @(
  'domains/exports',
  'domains/working',
  'sql/performance/bill_cycle',
  'sql/performance/billed_usage/validation',
  'sql/performance/snapshots/deployment_steps',
  'sql/reconciliation/billing',
  'sql/diagnostics',
  'sql/diagnostics/cisadm_dictionary',
  'scripts/performance',
  'scripts/repo',
  'docs/roadmap',
  'knowledge_base/c2m_cisadm',
  '.claude/skills',
  'archive'
)

# The eight snapshot tables still refreshed and scheduled (the active-8). A job or
# procedure name carries the table name with a JOB_REFRESH_/REFRESH_/JOB_BASELINE_ prefix.
$activeSnapshots = @(
  'FT_RPT_CURR', 'BSEG_BILLED_USAGE_RPT_CURR', 'BSEG_SQ_USAGE_RPT_CURR', 'D1_MSRMT_RPT_CURR',
  'FT_GL_DISTRIBUTION_RPT_CURR', 'D1_USAGE_RPT_CURR', 'D1_USAGE_SCALAR_DTL_RPT_CURR'
)

$missing = @()
foreach ($dir in $requiredDirs) {
  if (-not (Test-Path (Join-Path $RootPath $dir))) { $missing += $dir }
}

$rootClutter = Get-ChildItem -Path $RootPath -File -Filter '*.zip' | Select-Object -ExpandProperty Name

$retired = @{}
$scan = @('sql', 'domains', 'scripts', 'deploy/jaspersoft_standard_offering') | ForEach-Object { Join-Path $RootPath $_ } | Where-Object { Test-Path $_ }
Get-ChildItem -Path $scan -Recurse -File -Include *.sql, *.xml, *.py, *.sh, *.ps1, *.json, *.csv |
  Where-Object { $_.FullName -notmatch '[\\/]archive[\\/]' -and $_.Name -notmatch '^scheduler_jobs_' } |
  ForEach-Object {
    $text = Get-Content -Raw -LiteralPath $_.FullName -ErrorAction SilentlyContinue
    if (-not $text) { return }
    foreach ($m in [regex]::Matches($text, '\b[A-Z0-9_]+_RPT_CURR\b')) {
      $name = $m.Value -replace '^(JOB_BASELINE_|JOB_REFRESH_|JOB_ONCE_FULL_|REFRESH_)', ''
      if ($activeSnapshots -notcontains $name) {
        if (-not $retired.ContainsKey($name)) { $retired[$name] = @() }
        $rel = $_.FullName.Substring($RootPath.Length).TrimStart('\', '/')
        if ($retired[$name] -notcontains $rel) { $retired[$name] += $rel }
      }
    }
  }

Write-Host '=== Repo Structure Audit ==='
if ($missing.Count -eq 0) { Write-Host '[PASS] Required folders exist.' }
else { Write-Host '[FAIL] Missing folders:'; $missing | ForEach-Object { Write-Host "  - $_" } }

if ($rootClutter.Count -gt 0) { Write-Host '[WARN] Root-level zip artifacts detected:'; $rootClutter | ForEach-Object { Write-Host "  - $_" } }
else { Write-Host '[PASS] No root-level zip clutter detected.' }

if ($retired.Count -eq 0) { Write-Host '[PASS] Only the active-8 snapshot tables are named outside archive/.' }
else {
  Write-Host '[FAIL] Retired snapshot tables named outside archive/ (archive them, or add to the active list with evidence):'
  foreach ($k in ($retired.Keys | Sort-Object)) { Write-Host "  - $k : $($retired[$k] -join ', ')" }
}

if ($missing.Count -gt 0 -or $retired.Count -gt 0) { exit 1 }
exit 0
