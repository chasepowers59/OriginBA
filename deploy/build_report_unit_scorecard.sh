#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="${ROOT_DIR}/deploy/client_value_scorecard_report_unit"
ZIP_PATH="${ROOT_DIR}/deploy/client_value_scorecard_report_unit.zip"

mkdir -p "${BUNDLE_DIR}/reports/origin"

cp "${ROOT_DIR}/reports/client_value_scorecard.jrxml" "${BUNDLE_DIR}/reports/origin/client_value_scorecard.jrxml"
cp "${ROOT_DIR}/server/input_controls/client_value_scorecard_input_controls.json" "${BUNDLE_DIR}/reports/origin/input_controls.json"

if [[ -f "${ROOT_DIR}/reports/client_value_scorecard.jasper" ]]; then
  cp "${ROOT_DIR}/reports/client_value_scorecard.jasper" "${BUNDLE_DIR}/reports/origin/client_value_scorecard.jasper"
fi

cat > "${BUNDLE_DIR}/manifest.json" <<'JSON'
{
  "reportUnitUri": "/reports/origin/client_value_scorecard",
  "label": "Client Value Scorecard",
  "description": "Executive scorecard with debt, billing, payment, and contact-quality KPIs.",
  "datasourceCandidates": ["C2M_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
  "resources": [
    "reports/origin/client_value_scorecard.jrxml",
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
