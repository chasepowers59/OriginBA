#!/usr/bin/env bash
set -euo pipefail

# Strict deployment helper (no credentials stored)
# Required env:
#   JRS_URL, JRS_USER, JRS_PASSWORD, IMPORT_ZIP
# Optional:
#   SOURCE_ORG (default Origin_DEV)

SOURCE_ORG="${SOURCE_ORG:-Origin_DEV}"

if [[ -z "${JRS_URL:-}" || -z "${JRS_USER:-}" || -z "${JRS_PASSWORD:-}" || -z "${IMPORT_ZIP:-}" ]]; then
  echo "Missing required environment variables: JRS_URL, JRS_USER, JRS_PASSWORD, IMPORT_ZIP"
  exit 1
fi

echo "Deploying from source organization: ${SOURCE_ORG}"
echo "Mode: Legacy Key + UPDATE only (compliance)"

curl -sS -u "${JRS_USER}:${JRS_PASSWORD}" \
  -H "Content-Type: application/zip" \
  -X POST \
  "${JRS_URL}/rest_v2/import?update=true&skipUserUpdate=true&includeAccessEvents=false" \
  --data-binary "@${IMPORT_ZIP}" \
  -o deploy_map_report_response.json

echo "Import response saved to deploy_map_report_response.json"
echo "Next required steps:"
echo "1) Re-import target datasource backup"
echo "2) Run City Checker (SmartCity)"
echo "3) Smoke test map_meters_coverage and verify create dates"
