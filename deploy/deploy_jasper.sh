#!/usr/bin/env bash
set -euo pipefail

# Environment-driven deployment only. No hard-coded credentials.
: "${JRS_URL:?Set JRS_URL, e.g. https://jasper.example.com/jasperserver}"
: "${JRS_USER:?Set JRS_USER}"
: "${JRS_PASSWORD:?Set JRS_PASSWORD}"

JRS_DATASOURCE="${JRS_DATASOURCE:-C2M_DEV_DS}"
REPORT_ZIP="${REPORT_ZIP:-deploy/billing_master_report_unit.zip}"
UPDATE_MODE="${UPDATE_MODE:-true}"

if [[ ! -f "${REPORT_ZIP}" ]]; then
  echo "Report package not found: ${REPORT_ZIP}"
  echo "Create an export/import compatible report unit zip first."
  exit 1
fi

echo "Deploying report unit package: ${REPORT_ZIP}"
echo "Using server datasource name: ${JRS_DATASOURCE}"

curl -sS -u "${JRS_USER}:${JRS_PASSWORD}" \
  -H "Content-Type: application/zip" \
  --data-binary @"${REPORT_ZIP}" \
  "${JRS_URL}/rest_v2/import?update=${UPDATE_MODE}" \
  -o /tmp/jrs_import_response.json

echo "Import response saved to /tmp/jrs_import_response.json"

echo "Applying input controls payload (best-effort)..."
if [[ -f "server/input_controls/billing_master_input_controls_rest.json" ]]; then
  curl -sS -u "${JRS_USER}:${JRS_PASSWORD}" \
    -H "Content-Type: application/json" \
    -X PUT \
    "${JRS_URL}/rest_v2/resources/reports/origin/billing_master_input_controls.json" \
    --data-binary @server/input_controls/billing_master_input_controls_rest.json \
    -o /tmp/jrs_input_controls_response.json || true
  echo "Input control response saved to /tmp/jrs_input_controls_response.json"
fi

echo "Sample render validation:"
echo "curl -sS -u \"\${JRS_USER}:\${JRS_PASSWORD}\" \\"
echo "  \"\${JRS_URL}/rest_v2/reports/reports/origin/billing_master.pdf?CLIENT_ID=1001&START_TS=2026-01-01T00:00:00&END_TS=2026-01-31T23:59:59\" \\"
echo "  -o /tmp/billing_master.pdf"
