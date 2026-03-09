param(
  [Parameter(Mandatory=$true)]
  [string]$ConnectString,
  [string]$SchemaOwner = 'CISADM',
  [string]$SqlPlusExe = 'sqlplus',
  [string]$DiscoverySqlDir = 'sql/diagnostics/cisadm_dictionary',
  [string]$ReadOnlyGuardScript = 'scripts/repo/sql_read_only_guard.py',
  [string]$CoverageBuilderScript = 'scripts/performance/build_cisadm_dictionary_coverage.py',
  [string]$PrefilterBuilderScript = 'scripts/performance/build_prefilter_candidates.py',
  [string]$PythonExe = 'python',
  [string]$OutputDir = 'output/cisadm_dictionary'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$discoveryDirPath = (Resolve-Path (Join-Path $repoRoot $DiscoverySqlDir) -ErrorAction SilentlyContinue)
if (-not $discoveryDirPath) {
  throw "Dictionary SQL directory not found: $DiscoverySqlDir"
}
$discoveryDir = $discoveryDirPath.Path

$guardPath = Resolve-Path (Join-Path $repoRoot $ReadOnlyGuardScript) -ErrorAction SilentlyContinue
if (-not $guardPath) {
  throw "Read-only guard script not found: $ReadOnlyGuardScript"
}

$coverageBuilderPath = Resolve-Path (Join-Path $repoRoot $CoverageBuilderScript) -ErrorAction SilentlyContinue
if (-not $coverageBuilderPath) {
  throw "Coverage builder script not found: $CoverageBuilderScript"
}

$prefilterBuilderPath = Resolve-Path (Join-Path $repoRoot $PrefilterBuilderScript) -ErrorAction SilentlyContinue
if (-not $prefilterBuilderPath) {
  throw "Prefilter builder script not found: $PrefilterBuilderScript"
}

$outputDirPath = Join-Path $repoRoot $OutputDir
New-Item -ItemType Directory -Path $outputDirPath -Force | Out-Null

$scripts = @(
  [pscustomobject]@{ Sql = '01_tables.sql'; Out = 'tables.csv' },
  [pscustomobject]@{ Sql = '02_columns.sql'; Out = 'columns.csv' },
  [pscustomobject]@{ Sql = '03_constraints.sql'; Out = 'constraints.csv' },
  [pscustomobject]@{ Sql = '04_constraint_columns.sql'; Out = 'constraint_columns.csv' },
  [pscustomobject]@{ Sql = '05_indexes.sql'; Out = 'indexes.csv' },
  [pscustomobject]@{ Sql = '06_index_columns.sql'; Out = 'index_columns.csv' },
  [pscustomobject]@{ Sql = '07_views.sql'; Out = 'views.csv' },
  [pscustomobject]@{ Sql = '08_view_dependencies.sql'; Out = 'view_dependencies.csv' },
  [pscustomobject]@{ Sql = '09_mviews.sql'; Out = 'mviews.csv' },
  [pscustomobject]@{ Sql = '10_synonyms_to_cisadm.sql'; Out = 'synonyms_to_cisadm.csv' },
  [pscustomobject]@{ Sql = '11_table_partitions.sql'; Out = 'table_partitions.csv' },
  [pscustomobject]@{ Sql = '12_table_stats.sql'; Out = 'table_stats.csv' },
  [pscustomobject]@{ Sql = '13_column_stats.sql'; Out = 'column_stats.csv' },
  [pscustomobject]@{ Sql = '14_fk_join_map.sql'; Out = 'fk_join_map.csv' },
  [pscustomobject]@{ Sql = '15_keyword_table_map.sql'; Out = 'keyword_table_map.csv' }
)

Push-Location $discoveryDir
try {
  Write-Host "Running SQL read-only guard for dictionary discovery..."
  & $PythonExe $guardPath.Path '.'
  if ($LASTEXITCODE -ne 0) {
    throw "Read-only guard failed with exit code $LASTEXITCODE"
  }

  $results = @()
  foreach ($job in $scripts) {
    if (-not (Test-Path $job.Sql)) {
      throw "Dictionary script not found: $job.Sql"
    }

    $outputPath = Join-Path $outputDirPath $job.Out
    $outputPathSql = $outputPath.Replace('\', '/')
    $sqlPath = (Resolve-Path $job.Sql).Path.Replace('\', '/')
    $driverPath = "tmp_dictionary_$($job.Sql.Replace('.sql',''))_run.sql"

    $driverLines = @(
      "set define on",
      "set verify off",
      "set feedback off",
      "set heading on",
      "set trimspool on",
      "set pagesize 50000",
      "set linesize 32767",
      "set markup csv on quote on",
      "whenever sqlerror exit failure",
      "define schema_owner = $SchemaOwner",
      "spool $outputPathSql",
      "@$sqlPath",
      "spool off",
      "exit"
    )

    ($driverLines -join "`n") | Set-Content $driverPath -Encoding UTF8

    Write-Host "Extracting $($job.Sql) -> $outputPath"
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    & $SqlPlusExe -S $ConnectString "@$driverPath"
    $exitCode = $LASTEXITCODE
    $sw.Stop()

    if ($exitCode -ne 0) {
      throw "Dictionary extraction failed for $($job.Sql) with sqlplus exit code $exitCode"
    }

    $fileInfo = Get-Item $outputPath
    $results += [pscustomobject]@{
      Script = $job.Sql
      OutputCsv = $outputPath
      ElapsedSeconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
      FileBytes = $fileInfo.Length
      LastWriteTime = $fileInfo.LastWriteTime.ToString('s')
    }
  }

  $manifestPath = Join-Path $outputDirPath 'manifest.csv'
  $results | Export-Csv -Path $manifestPath -NoTypeInformation
  Write-Host "Dictionary extraction complete: $manifestPath"

  Write-Host "Building workstream coverage summary..."
  & $PythonExe $coverageBuilderPath.Path --dictionary-dir $outputDirPath
  if ($LASTEXITCODE -ne 0) {
    throw "Coverage builder failed with exit code $LASTEXITCODE"
  }

  Write-Host "Building indexed prefilter candidates..."
  & $PythonExe $prefilterBuilderPath.Path --dictionary-dir $outputDirPath
  if ($LASTEXITCODE -ne 0) {
    throw "Prefilter builder failed with exit code $LASTEXITCODE"
  }
}
finally {
  Get-ChildItem -Path . -Filter 'tmp_dictionary_*_run.sql' -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
  Pop-Location
}
