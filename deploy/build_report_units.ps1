param(
    [string]$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

& (Join-Path $PSScriptRoot "build_report_unit.ps1") -RootDir $RootDir
& (Join-Path $PSScriptRoot "build_report_unit_scorecard.ps1") -RootDir $RootDir
& (Join-Path $PSScriptRoot "build_report_unit_collections.ps1") -RootDir $RootDir
& (Join-Path $PSScriptRoot "build_report_unit_ops_hub.ps1") -RootDir $RootDir
& (Join-Path $PSScriptRoot "build_report_unit_lookup_audit.ps1") -RootDir $RootDir
& (Join-Path $PSScriptRoot "build_report_unit_map.ps1") -RootDir $RootDir
& (Join-Path $PSScriptRoot "build_report_unit_billing_statement.ps1") -RootDir $RootDir

Write-Output "All report unit bundles built."
