#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="${ROOT_DIR}/deploy/billing_customer_statement_report_unit"
ZIP_PATH="${ROOT_DIR}/deploy/billing_customer_statement_report_unit.zip"

mkdir -p "${BUNDLE_DIR}/reports/origin/subreports"

cp "${ROOT_DIR}/reports/billing_customer_statement.jrxml" "${BUNDLE_DIR}/reports/origin/billing_customer_statement.jrxml"
cp "${ROOT_DIR}/reports/subreports/line_items.jrxml" "${BUNDLE_DIR}/reports/origin/subreports/line_items.jrxml"
cp "${ROOT_DIR}/server/input_controls/billing_customer_statement_input_controls.json" "${BUNDLE_DIR}/reports/origin/input_controls.json"
cp "${ROOT_DIR}/server/input_controls/billing_customer_statement_input_controls_rest.json" "${BUNDLE_DIR}/reports/origin/input_controls_rest.json"

if [[ -f "${ROOT_DIR}/reports/billing_customer_statement.jasper" ]]; then
  cp "${ROOT_DIR}/reports/billing_customer_statement.jasper" "${BUNDLE_DIR}/reports/origin/billing_customer_statement.jasper"
fi
if [[ -f "${ROOT_DIR}/reports/subreports/line_items.jasper" ]]; then
  cp "${ROOT_DIR}/reports/subreports/line_items.jasper" "${BUNDLE_DIR}/reports/origin/subreports/line_items.jasper"
fi

cat > "${BUNDLE_DIR}/manifest.json" <<'JSON'
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
JSON

rm -f "${ZIP_PATH}"
(
  cd "${BUNDLE_DIR}"
  zip -rq "${ZIP_PATH}" .
)

echo "Created bundle: ${ZIP_PATH}"
