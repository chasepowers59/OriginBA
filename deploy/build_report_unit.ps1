param(
    [string]$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$bundleDir = Join-Path $RootDir "deploy\billing_master_report_unit"
$zipPath = Join-Path $RootDir "deploy\billing_master_report_unit.zip"
$reportsDir = Join-Path $bundleDir "reports\origin"
$subDir = Join-Path $reportsDir "subreports"

if (Test-Path $bundleDir) { Remove-Item $bundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $subDir -Force | Out-Null

Copy-Item (Join-Path $RootDir "reports\billing_master.jrxml") (Join-Path $reportsDir "billing_master.jrxml")
Copy-Item (Join-Path $RootDir "reports\subreports\line_items.jrxml") (Join-Path $subDir "line_items.jrxml")
Copy-Item (Join-Path $RootDir "server\input_controls\billing_master_input_controls.json") (Join-Path $reportsDir "input_controls.json")
Copy-Item (Join-Path $RootDir "server\input_controls\billing_master_input_controls_rest.json") (Join-Path $reportsDir "input_controls_rest.json")

$billingJasper = Join-Path $RootDir "reports\billing_master.jasper"
$lineItemsJasper = Join-Path $RootDir "reports\subreports\line_items.jasper"
if (Test-Path $billingJasper) { Copy-Item $billingJasper (Join-Path $reportsDir "billing_master.jasper") }
if (Test-Path $lineItemsJasper) { Copy-Item $lineItemsJasper (Join-Path $subDir "line_items.jasper") }

$manifest = @'
{
  "reportUnitUri": "/reports/origin/billing_master",
  "label": "Billing Master",
  "description": "Multi-tenant billing report (master + line item subreport).",
  "datasourceCandidates": ["C2M_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
  "resources": [
    "reports/origin/billing_master.jrxml",
    "reports/origin/subreports/line_items.jrxml",
    "reports/origin/input_controls.json",
    "reports/origin/input_controls_rest.json"
  ]
}
'@
$manifest | Out-File (Join-Path $bundleDir "manifest.json") -Encoding utf8

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $bundleDir "*") -DestinationPath $zipPath
Write-Output "Created bundle: $zipPath"
