#!/usr/bin/env bash
set -euo pipefail

# Builds a deployable report bundle zip (JRXML + optional compiled JASPER + metadata).
# This bundle is intended for deploy/deploy_jasper.sh import flows.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUNDLE_DIR="${ROOT_DIR}/deploy/billing_master_report_unit"
ZIP_PATH="${ROOT_DIR}/deploy/billing_master_report_unit.zip"

mkdir -p "${BUNDLE_DIR}/reports/origin/subreports"

cp "${ROOT_DIR}/reports/billing_master.jrxml" "${BUNDLE_DIR}/reports/origin/billing_master.jrxml"
cp "${ROOT_DIR}/reports/subreports/line_items.jrxml" "${BUNDLE_DIR}/reports/origin/subreports/line_items.jrxml"
cp "${ROOT_DIR}/server/input_controls/billing_master_input_controls.json" "${BUNDLE_DIR}/reports/origin/input_controls.json"
cp "${ROOT_DIR}/server/input_controls/billing_master_input_controls_rest.json" "${BUNDLE_DIR}/reports/origin/input_controls_rest.json"

# Optionally include compiled .jasper files if present (CI compile step).
if [[ -f "${ROOT_DIR}/reports/billing_master.jasper" ]]; then
  cp "${ROOT_DIR}/reports/billing_master.jasper" "${BUNDLE_DIR}/reports/origin/billing_master.jasper"
fi
if [[ -f "${ROOT_DIR}/reports/subreports/line_items.jasper" ]]; then
  cp "${ROOT_DIR}/reports/subreports/line_items.jasper" "${BUNDLE_DIR}/reports/origin/subreports/line_items.jasper"
fi

cat > "${BUNDLE_DIR}/manifest.json" <<'JSON'
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
JSON

rm -f "${ZIP_PATH}"
(
  cd "${BUNDLE_DIR}"
  zip -rq "${ZIP_PATH}" .
)

echo "Created bundle: ${ZIP_PATH}"
