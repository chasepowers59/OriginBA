#!/usr/bin/env bash
# Limited-privilege 25.4 TEST install for one client.
# Creates tables/views/procs, grants via CISADM DDL helper, seeds lookups,
# then kicks all full-history baselines in parallel.
set -euo pipefail
CLIENT="${1:?client required}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
RUN=(python3 "$ROOT/scripts/local/run_client_oracle_sql.py" --client "$CLIENT")
LOGDIR="$ROOT/deploy/snapshot_rollout_logs/${CLIENT}/install_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$LOGDIR"
exec > >(tee -a "$LOGDIR/install.log") 2>&1

echo "=== $CLIENT: DDL helper ==="
"${RUN[@]}" --file "$ROOT/sql/performance/snapshots/deployment_steps/clients/newark_25_4_ddl_helper.sql"
"${RUN[@]}" --sql "
CREATE OR REPLACE PROCEDURE cisadm.originba_ddl_helper2(p_sql IN VARCHAR2) AUTHID DEFINER AS
BEGIN
  EXECUTE IMMEDIATE p_sql;
END;
/"

echo "=== $CLIENT: create 7 snapshot tables (skip if exist) ==="
for f in \
  sql/performance/snapshots/finance/ft_rpt_curr/01_create_snapshot_table.sql \
  sql/performance/snapshots/billed_usage/bseg_billed_usage/01_create_snapshot_table.sql \
  sql/performance/snapshots/billed_usage/bseg_sq_usage/01_create_snapshot_table.sql \
  sql/performance/snapshots/meter_ops/d1_msrmt/00_create_snapshot_table.sql \
  sql/performance/snapshots/finance/ft_gl_distribution/01_create_snapshot_table.sql \
  sql/performance/snapshots/meter_ops/d1_usage/01_create_snapshot_table.sql \
  sql/performance/snapshots/meter_ops/d1_usage_scalar_dtl/01_create_snapshot_table.sql
do
  echo "-- $f"
  if ! "${RUN[@]}" --file "$ROOT/$f"; then
    echo "WARN: create failed for $f (may already exist); continuing"
  fi
done

echo "=== $CLIENT: CMS_SA_SNAPSHOT create if missing ==="
EXISTS=$("${RUN[@]}" --sql "SELECT COUNT(*) AS c FROM all_tables WHERE owner='CISADM' AND table_name='CMS_SA_SNAPSHOT'" | awk '/\|/{next} /^[0-9]+$/{print; exit} /^[[:space:]]*[0-9]+[[:space:]]*$/{print $1; exit}')
# Fallback parse from table output
if [[ -z "${EXISTS}" ]]; then
  EXISTS=$("${RUN[@]}" --sql "SELECT COUNT(*) AS c FROM all_tables WHERE owner='CISADM' AND table_name='CMS_SA_SNAPSHOT'" | sed -n 's/[^0-9]*\([0-9][0-9]*\).*/\1/p' | tail -1)
fi
if [[ "${EXISTS:-0}" == "0" ]]; then
  # Create without DROP: use helper to run CREATE if script DROP fails
  if ! "${RUN[@]}" --file "$ROOT/sql/performance/snapshots/debt_mgmt/cms_sa_snapshot/01_create_cms_sa_snapshot_table.sql"; then
    echo "WARN: CMS_SA_SNAPSHOT create script failed; may need manual create"
  fi
fi

echo "=== $CLIENT: CMS views without GRANTs ==="
python3 - <<PY
from pathlib import Path
root = Path("$ROOT")
files = [
    "sql/performance/snapshots/meter_ops/cms_d1_dvc_identifier_view/01_create_cms_d1_dvc_identifier_view.sql",
    "sql/performance/snapshots/meter_ops/cms_d1_dvc_boda_view/01_create_cms_d1_dvc_boda_view.sql",
    "sql/performance/snapshots/meter_ops/cms_asset_identifier_view/01_create_cms_w1_asset_identifier_view.sql",
    "sql/performance/snapshots/field_ops/cms_activity_views/01_create_cms_activity_views.sql",
    "sql/performance/snapshots/customer_ops/cms_ci_case_views/01_create_cms_ci_case_views.sql",
]
out = Path("/tmp/cms_views_no_grants_${CLIENT}.sql")
parts = []
for f in files:
    lines = [ln for ln in (root / f).read_text().splitlines() if not ln.strip().upper().startswith("GRANT ")]
    parts.append("\n".join(lines))
out.write_text("\n\n".join(parts) + "\n")
print(out)
PY
"${RUN[@]}" --file "/tmp/cms_views_no_grants_${CLIENT}.sql"

echo "=== $CLIENT: refresh procedures ==="
"${RUN[@]}" --file "$ROOT/sql/performance/snapshots/deployment_steps/02_deploy_all_initial_full_history_procedures.sql"
"${RUN[@]}" --file "$ROOT/sql/performance/snapshots/deployment_steps/02b_deploy_domain_support_procedures.sql"

echo "=== $CLIENT: grants via helper2 ==="
sed 's/originba_ddl_helper(/originba_ddl_helper2(/g' \
  "$ROOT/sql/performance/snapshots/deployment_steps/clients/newark_25_4_post_create_grants.sql" \
  > "/tmp/post_create_grants_helper2_${CLIENT}.sql"
"${RUN[@]}" --file "/tmp/post_create_grants_helper2_${CLIENT}.sql"

echo "=== $CLIENT: lookup seed + CISREAD synonyms ==="
"${RUN[@]}" --file "$ROOT/sql/performance/snapshots/debt_mgmt/cms_sa_snapshot/06_seed_cm_snapshot_type_flg_lookups.sql" || true
for syn in ft_rpt_curr bseg_billed_usage_rpt_curr bseg_sq_usage_rpt_curr d1_msrmt_rpt_curr \
           ft_gl_distribution_rpt_curr d1_usage_rpt_curr d1_usage_scalar_dtl_rpt_curr cms_sa_snapshot \
           cms_ci_case_vw cms_ci_case_log_vw; do
  "${RUN[@]}" --sql "CREATE OR REPLACE SYNONYM cisread.${syn} FOR cisadm.${syn}"
done

echo "=== $CLIENT: object inventory ==="
"${RUN[@]}" --sql "
SELECT object_type, object_name, status
FROM all_objects
WHERE owner='CISADM'
  AND (
    object_name LIKE '%_RPT_CURR'
    OR object_name IN ('CMS_SA_SNAPSHOT','REFRESH_CMS_SA_SNAPSHOT')
    OR object_name LIKE 'CMS_%_VW'
  )
ORDER BY object_type, object_name
"

if [[ "${SKIP_BASELINE_KICK:-0}" == "1" ]]; then
  echo "=== $CLIENT: SKIP_BASELINE_KICK=1 — baselines not started (use 3-stream runner for PROD) ==="
else
  echo "=== $CLIENT: kick parallel baselines ==="
  # Prefer 2-3 concurrent jobs on constrained TEST/PROD hosts; this script still
  # submits all 8 — operators may stagger heavy tables manually if I/O contends.
  "${RUN[@]}" --file "$ROOT/sql/performance/snapshots/deployment_steps/clients/run_all_baselines_parallel_now.sql"
fi

echo "=== $CLIENT: NOTE — after baselines SUCCEEDED, run post-load indexes ==="
echo "  python3 scripts/local/run_client_oracle_sql.py --client $CLIENT \\"
echo "    --file sql/performance/snapshots/deployment_steps/clients/post_load_snapshot_indexes_limited_priv.sql"
echo "INSTALL_SUBMITTED:$CLIENT logs=$LOGDIR"
