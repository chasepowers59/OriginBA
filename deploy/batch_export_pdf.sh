#!/usr/bin/env bash
set -euo pipefail

# Batch PDF export orchestration with chunking + retry/backoff + streaming to output dir.
# Credentials are server-managed via env vars; no hardcoded secrets.
#
# Required env:
#   JRS_URL, JRS_USER, JRS_PASSWORD
# Optional env:
#   REPORT_URI (default: reports/origin/billing_master)
#   CLIENT_LIST_FILE (default: sample_data/client_ids.txt)
#   START_TS, END_TS
#   CHUNK_SIZE (default: 50)
#   MAX_RETRIES (default: 4)
#   OUT_DIR (default: ./export_out)

: "${JRS_URL:?Set JRS_URL}"
: "${JRS_USER:?Set JRS_USER}"
: "${JRS_PASSWORD:?Set JRS_PASSWORD}"

REPORT_URI="${REPORT_URI:-reports/origin/billing_master}"
CLIENT_LIST_FILE="${CLIENT_LIST_FILE:-sample_data/client_ids.txt}"
START_TS="${START_TS:-2026-01-01T00:00:00}"
END_TS="${END_TS:-2026-01-31T23:59:59}"
CHUNK_SIZE="${CHUNK_SIZE:-50}"
MAX_RETRIES="${MAX_RETRIES:-4}"
OUT_DIR="${OUT_DIR:-export_out}"

mkdir -p "${OUT_DIR}"
if [[ ! -f "${CLIENT_LIST_FILE}" ]]; then
  echo "Missing client list: ${CLIENT_LIST_FILE}"
  exit 1
fi

retry_render() {
  local client_id="$1"
  local out_file="$2"
  local attempt=1
  local delay=2

  while (( attempt <= MAX_RETRIES )); do
    if curl -fsS -u "${JRS_USER}:${JRS_PASSWORD}" \
      "${JRS_URL}/rest_v2/reports/${REPORT_URI}.pdf?CLIENT_ID=${client_id}&START_TS=${START_TS}&END_TS=${END_TS}" \
      -o "${out_file}"; then
      return 0
    fi
    sleep "${delay}"
    delay=$(( delay * 2 ))
    attempt=$(( attempt + 1 ))
  done
  return 1
}

line_no=0
chunk_no=1
while IFS= read -r client_id; do
  [[ -z "${client_id}" ]] && continue
  line_no=$(( line_no + 1 ))
  if (( (line_no - 1) % CHUNK_SIZE == 0 )); then
    echo "Starting chunk ${chunk_no}..."
    chunk_no=$(( chunk_no + 1 ))
  fi

  out_file="${OUT_DIR}/billing_master_client_${client_id}.pdf"
  if retry_render "${client_id}" "${out_file}"; then
    echo "OK client ${client_id} -> ${out_file}"
  else
    echo "FAILED client ${client_id}" >&2
  fi
done < "${CLIENT_LIST_FILE}"

echo "Batch export completed."
