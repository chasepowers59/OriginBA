#!/usr/bin/env bash
# Capture workstream table health for all configured SmartCity clients.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

CLIENTS=(demo newark fonddulac collegestation ellensburg citycorp odessa)

python3 scripts/build_workstream_physical_catalog.py
python3 scripts/build_fk_join_map_full.py
python3 scripts/build_workstream_table_health_sql.py

for client in "${CLIENTS[@]}"; do
  echo "=== Client: ${client} ==="
  if python3 scripts/local/capture_workstream_table_health.py --client "$client"; then
    python3 scripts/build_ai_cisadm_context.py --client "$client" --out "output/ai_cisadm_context_${client}.json"
  else
    echo "[WARN] Skipped ${client} (connection or config unavailable)"
  fi
done

python3 scripts/build_ai_cisadm_context.py --client demo
echo "[PASS] Multi-client table health complete."
