#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="${ROOT_DIR}/deploy/ops_hub_dashboard_report_unit"
ZIP_PATH="${ROOT_DIR}/deploy/ops_hub_dashboard_report_unit.zip"

mkdir -p "${BUNDLE_DIR}/reports/origin"

cp "${ROOT_DIR}/reports/ops_hub_dashboard.jrxml" "${BUNDLE_DIR}/reports/origin/ops_hub_dashboard.jrxml"
cp "${ROOT_DIR}/server/input_controls/ops_hub_dashboard_input_controls.json" "${BUNDLE_DIR}/reports/origin/input_controls.json"

if [[ -f "${ROOT_DIR}/reports/ops_hub_dashboard.jasper" ]]; then
  cp "${ROOT_DIR}/reports/ops_hub_dashboard.jasper" "${BUNDLE_DIR}/reports/origin/ops_hub_dashboard.jasper"
fi

cat > "${BUNDLE_DIR}/manifest.json" <<'JSON'
{
  "reportUnitUri": "/reports/origin/ops_hub_dashboard",
  "label": "SmartCity Ops Hub Dashboard",
  "description": "9-workstream KPI dashboard for SmartCity municipal operations.",
  "datasourceCandidates": ["C2M_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
  "resources": [
    "reports/origin/ops_hub_dashboard.jrxml",
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
