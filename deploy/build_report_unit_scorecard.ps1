param(
    [string]$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$bundleDir = Join-Path $RootDir "deploy\client_value_scorecard_report_unit"
$zipPath = Join-Path $RootDir "deploy\client_value_scorecard_report_unit.zip"
$reportsDir = Join-Path $bundleDir "reports\origin"

if (Test-Path $bundleDir) { Remove-Item $bundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $reportsDir -Force | Out-Null

Copy-Item (Join-Path $RootDir "reports\client_value_scorecard.jrxml") (Join-Path $reportsDir "client_value_scorecard.jrxml")
Copy-Item (Join-Path $RootDir "server\input_controls\client_value_scorecard_input_controls.json") (Join-Path $reportsDir "input_controls.json")
Copy-Item (Join-Path $RootDir "server\input_controls\client_value_scorecard_input_controls_rest.json") (Join-Path $reportsDir "input_controls_rest.json")

$jasper = Join-Path $RootDir "reports\client_value_scorecard.jasper"
if (Test-Path $jasper) { Copy-Item $jasper (Join-Path $reportsDir "client_value_scorecard.jasper") }

$manifest = @'
{
  "reportUnitUri": "/reports/origin/client_value_scorecard",
  "label": "Client Value Scorecard",
  "description": "Executive scorecard with debt, billing, payment, and contact-quality KPIs.",
  "datasourceCandidates": ["C2M_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
  "resources": [
    "reports/origin/client_value_scorecard.jrxml",
    "reports/origin/input_controls.json",
    "reports/origin/input_controls_rest.json"
  ]
}
'@
$manifest | Out-File (Join-Path $bundleDir "manifest.json") -Encoding utf8

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $bundleDir "*") -DestinationPath $zipPath
Write-Output "Created bundle: $zipPath"
