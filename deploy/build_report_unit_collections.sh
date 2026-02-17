#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="${ROOT_DIR}/deploy/collections_prioritization_report_unit"
ZIP_PATH="${ROOT_DIR}/deploy/collections_prioritization_report_unit.zip"

mkdir -p "${BUNDLE_DIR}/reports/origin"

cp "${ROOT_DIR}/reports/collections_prioritization.jrxml" "${BUNDLE_DIR}/reports/origin/collections_prioritization.jrxml"
cp "${ROOT_DIR}/server/input_controls/collections_prioritization_input_controls.json" "${BUNDLE_DIR}/reports/origin/input_controls.json"

if [[ -f "${ROOT_DIR}/reports/collections_prioritization.jasper" ]]; then
  cp "${ROOT_DIR}/reports/collections_prioritization.jasper" "${BUNDLE_DIR}/reports/origin/collections_prioritization.jasper"
fi

cat > "${BUNDLE_DIR}/manifest.json" <<'JSON'
{
  "reportUnitUri": "/reports/origin/collections_prioritization",
  "label": "Collections Prioritization",
  "description": "Ranked collections queue by aged debt and active risk alerts.",
  "datasourceCandidates": ["C2M_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
  "resources": [
    "reports/origin/collections_prioritization.jrxml",
    "reports/origin/input_controls.json"
  ]
}
JSON

rm -f "${ZIP_PATH}"
(
  cd "${BUNDLE_DIR}"
  zip -rq "${ZIP_PATH}" .
)

echo "Created bundle: ${ZIP_PATH}"
