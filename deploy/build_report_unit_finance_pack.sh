#!/usr/bin/env bash
# Bundle the SQL finance report pack (four main reports + their subreports + input controls)
# the way build_report_unit_billing_statement.sh does: reports/origin/... inside a zip with a
# manifest per report unit. Regenerate the JRXML first if a spec changed:
#   python3 scripts/jaspersoft/generate_sql_report_pack.py
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="${ROOT_DIR}/deploy/finance_pack_report_units"
ZIP_PATH="${ROOT_DIR}/deploy/finance_pack_report_units.zip"
rm -rf "${BUNDLE_DIR}"; mkdir -p "${BUNDLE_DIR}/reports/origin/subreports"

PACK=(
  "billing_by_cycle_period:billing_by_cycle_service_type:Billing by Cycle"
  "payments_by_tender_type_period:payments_by_tender_type_month:Payments by Tender Type"
  "adjustments_by_type_period:adjustments_by_type_top:Adjustments by Type"
  "gl_by_distribution_code_period:gl_by_distribution_code_month:GL Activity by Distribution Code"
)
for entry in "${PACK[@]}"; do
  IFS=: read -r main sub label <<<"${entry}"
  cp "${ROOT_DIR}/reports/${main}.jrxml" "${BUNDLE_DIR}/reports/origin/${main}.jrxml"
  cp "${ROOT_DIR}/reports/subreports/${sub}.jrxml" "${BUNDLE_DIR}/reports/origin/subreports/${sub}.jrxml"
  cp "${ROOT_DIR}/server/input_controls/${main}_input_controls.json" "${BUNDLE_DIR}/reports/origin/${main}_input_controls.json"
  cp "${ROOT_DIR}/server/input_controls/${main}_input_controls_rest.json" "${BUNDLE_DIR}/reports/origin/${main}_input_controls_rest.json"
  cat > "${BUNDLE_DIR}/${main}.manifest.json" <<JSON
{
  "reportUnitUri": "/reports/origin/${main}",
  "label": "${label}",
  "datasourceCandidates": ["ORIGIN_DEV_DS", "C2M_QA_DS", "C2M_PROD_DS"],
  "resources": [
    "reports/origin/${main}.jrxml",
    "reports/origin/subreports/${sub}.jrxml",
    "reports/origin/${main}_input_controls.json",
    "reports/origin/${main}_input_controls_rest.json"
  ]
}
JSON
done
rm -f "${ZIP_PATH}"; (cd "${BUNDLE_DIR}" && zip -rq "${ZIP_PATH}" .)
echo "Created bundle: ${ZIP_PATH}"
