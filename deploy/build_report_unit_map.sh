#!/usr/bin/env bash
set -euo pipefail

# Builds map report bundle for source organization Origin_DEV.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="${ROOT_DIR}/deploy/map_meters_coverage_report_unit"
ZIP_PATH="${ROOT_DIR}/deploy/map_meters_coverage_report_unit.zip"

rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}/organizations/Origin_DEV/reports/maps/subreports"

cp "${ROOT_DIR}/reports/map_meters_coverage.jrxml" \
   "${BUNDLE_DIR}/organizations/Origin_DEV/reports/maps/map_meters_coverage.jrxml"
cp "${ROOT_DIR}/reports/subreports/line_items_fieldwork.jrxml" \
   "${BUNDLE_DIR}/organizations/Origin_DEV/reports/maps/subreports/line_items_fieldwork.jrxml"
cp "${ROOT_DIR}/server/input_controls/map_meters_input_controls.json" \
   "${BUNDLE_DIR}/organizations/Origin_DEV/reports/maps/input_controls.json"
cp "${ROOT_DIR}/server/input_controls/map_meters_input_controls_rest.json" \
   "${BUNDLE_DIR}/organizations/Origin_DEV/reports/maps/input_controls_rest.json"

if [[ -f "${ROOT_DIR}/reports/map_meters_coverage.jasper" ]]; then
  cp "${ROOT_DIR}/reports/map_meters_coverage.jasper" \
     "${BUNDLE_DIR}/organizations/Origin_DEV/reports/maps/map_meters_coverage.jasper"
fi
if [[ -f "${ROOT_DIR}/reports/subreports/line_items_fieldwork.jasper" ]]; then
  cp "${ROOT_DIR}/reports/subreports/line_items_fieldwork.jasper" \
     "${BUNDLE_DIR}/organizations/Origin_DEV/reports/maps/subreports/line_items_fieldwork.jasper"
fi

cat > "${BUNDLE_DIR}/manifest.json" <<'JSON'
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
JSON

rm -f "${ZIP_PATH}"
(
  cd "${BUNDLE_DIR}"
  zip -rq "${ZIP_PATH}" .
)

echo "Created bundle: ${ZIP_PATH}"
