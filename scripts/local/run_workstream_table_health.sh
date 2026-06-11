#!/usr/bin/env bash
# Run workstream table health checks and refresh AI context bundle for a client.
set -euo pipefail

CLIENT="${1:-demo}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

python3 scripts/build_workstream_table_health_sql.py
python3 scripts/local/capture_workstream_table_health.py --client "$CLIENT"
python3 scripts/build_ai_cisadm_context.py --client "$CLIENT"
echo "[PASS] Workstream table health complete for client=${CLIENT}"
