param(
    [string]$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$bundleDir = Join-Path $RootDir "deploy\collections_prioritization_report_unit"
$zipPath = Join-Path $RootDir "deploy\collections_prioritization_report_unit.zip"
$reportsDir = Join-Path $bundleDir "reports\origin"

if (Test-Path $bundleDir) { Remove-Item $bundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null

Copy-Item (Join-Path $RootDir "reports\collections_prioritization.jrxml") (Join-Path $reportsDir "collections_prioritization.jrxml")
Copy-Item (Join-Path $RootDir "server\input_controls\collections_prioritization_input_controls.json") (Join-Path $reportsDir "input_controls.json")
Copy-Item (Join-Path $RootDir "server\input_controls\collections_prioritization_input_controls_rest.json") (Join-Path $reportsDir "input_controls_rest.json")

$jasper = Join-Path $RootDir "reports\collections_prioritization.jasper"
if (Test-Path $jasper) { Copy-Item $jasper (Join-Path $reportsDir "collections_prioritization.jasper") }

$manifest = @'
{
  "reportUnitUri": "/reports/origin/collections_prioritization",
  "label": "Collections Prioritization",
  "description": "Ranked collections queue by aged debt and active risk alerts.",
  "datasourceCandidates": ["C2M_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
  "resources": [
    "reports/origin/collections_prioritization.jrxml",
    "reports/origin/input_controls.json",
    "reports/origin/input_controls_rest.json"
  ]
}
'@
$manifest | Out-File (Join-Path $bundleDir "manifest.json") -Encoding utf8

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $bundleDir "*") -DestinationPath $zipPath
Write-Output "Created bundle: $zipPath"
