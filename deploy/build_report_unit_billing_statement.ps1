param(
    [string]$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$bundleDir = Join-Path $RootDir "deploy\billing_customer_statement_report_unit"
$zipPath = Join-Path $RootDir "deploy\billing_customer_statement_report_unit.zip"
$reportsDir = Join-Path $bundleDir "reports\origin"
$subDir = Join-Path $reportsDir "subreports"

if (Test-Path $bundleDir) { Remove-Item $bundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $subDir -Force | Out-Null

Copy-Item (Join-Path $RootDir "reports\billing_customer_statement.jrxml") (Join-Path $reportsDir "billing_customer_statement.jrxml")
Copy-Item (Join-Path $RootDir "reports\subreports\line_items.jrxml") (Join-Path $subDir "line_items.jrxml")
Copy-Item (Join-Path $RootDir "server\input_controls\billing_customer_statement_input_controls.json") (Join-Path $reportsDir "input_controls.json")
Copy-Item (Join-Path $RootDir "server\input_controls\billing_customer_statement_input_controls_rest.json") (Join-Path $reportsDir "input_controls_rest.json")

$mainJasper = Join-Path $RootDir "reports\billing_customer_statement.jasper"
if (Test-Path $mainJasper) { Copy-Item $mainJasper (Join-Path $reportsDir "billing_customer_statement.jasper") }
$subJasper = Join-Path $RootDir "reports\subreports\line_items.jasper"
if (Test-Path $subJasper) { Copy-Item $subJasper (Join-Path $subDir "line_items.jasper") }

$manifest = @'
{
  "reportUnitUri": "/reports/origin/billing_customer_statement",
  "label": "Billing Customer Statement",
  "description": "Single bill statement template by BILL_ID.",
  "datasourceCandidates": ["ORIGIN_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
  "resources": [
    "reports/origin/billing_customer_statement.jrxml",
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
