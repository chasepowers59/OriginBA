param(
    [string]$RootDir = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
)

$ErrorActionPreference = "Stop"

$bundleDir = Join-Path $RootDir "deploy\map_meters_coverage_report_unit"
$zipPath = Join-Path $RootDir "deploy\map_meters_coverage_report_unit.zip"
$baseDir = Join-Path $bundleDir "organizations\Origin_DEV\reports\maps"
$subreportDir = Join-Path $baseDir "subreports"

if (Test-Path $bundleDir) { Remove-Item $bundleDir -Recurse -Force }
New-Item -ItemType Directory -Path $subreportDir -Force | Out-Null

Copy-Item (Join-Path $RootDir "reports\map_meters_coverage.jrxml") (Join-Path $baseDir "map_meters_coverage.jrxml")
Copy-Item (Join-Path $RootDir "reports\subreports\line_items_fieldwork.jrxml") (Join-Path $subreportDir "line_items_fieldwork.jrxml")
Copy-Item (Join-Path $RootDir "server\input_controls\map_meters_input_controls.json") (Join-Path $baseDir "input_controls.json")
Copy-Item (Join-Path $RootDir "server\input_controls\map_meters_input_controls_rest.json") (Join-Path $baseDir "input_controls_rest.json")

$mapJasper = Join-Path $RootDir "reports\map_meters_coverage.jasper"
if (Test-Path $mapJasper) { Copy-Item $mapJasper (Join-Path $baseDir "map_meters_coverage.jasper") }

$subJasper = Join-Path $RootDir "reports\subreports\line_items_fieldwork.jasper"
if (Test-Path $subJasper) { Copy-Item $subJasper (Join-Path $subreportDir "line_items_fieldwork.jasper") }

$manifest = @'
{
  "sourceOrganization": "Origin_DEV",
  "reportUnitUri": "/organizations/Origin_DEV/reports/maps/map_meters_coverage",
  "label": "Map Meters Coverage",
  "description": "Map-centric meter coverage and active field work report package.",
  "datasourceCandidates": ["ORIGIN_DEV_DS"],
  "resources": [
    "organizations/Origin_DEV/reports/maps/map_meters_coverage.jrxml",
    "organizations/Origin_DEV/reports/maps/subreports/line_items_fieldwork.jrxml",
    "organizations/Origin_DEV/reports/maps/input_controls.json",
    "organizations/Origin_DEV/reports/maps/input_controls_rest.json"
  ]
}
'@
$manifest | Out-File (Join-Path $bundleDir "manifest.json") -Encoding utf8

if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $bundleDir "*") -DestinationPath $zipPath
Write-Output "Created bundle: $zipPath"
