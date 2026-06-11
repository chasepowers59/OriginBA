#!/usr/bin/env bash
# Deploy, refresh, and validate all 12 workstream consolidation snapshots on demo.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLIENT="${1:-demo}"
LOG_DIR="$ROOT/deploy/snapshot_rollout_logs/${CLIENT}/consolidation"
RUNNER=(python3 "$ROOT/scripts/local/run_client_oracle_sql.py" --client "$CLIENT")

mkdir -p "$LOG_DIR"

declare -a SNAPSHOTS=(
  "customer_ops/acct_customer|refresh_acct_customer_rpt_curr"
  "customer_ops/case_prem_contact|refresh_case_prem_contact_rpt_curr"
  "new_services/pipeline|refresh_new_service_pipeline_rpt_curr"
  "field_ops/field_activity|refresh_field_activity_rpt_curr"
  "field_ops/crew_ops|refresh_crew_ops_rpt_curr"
  "meter_ops/device_sp|refresh_device_sp_rpt_curr"
  "payments_cashiering/pay_event|refresh_pay_event_rpt_curr"
  "finance/billable_charge|refresh_billable_charge_rpt_curr"
  "debt_mgmt/sa_aged_bal|refresh_sa_aged_bal_rpt_curr"
  "debt_mgmt/wo_proc|refresh_wo_proc_rpt_curr"
  "common/ops_exception|refresh_ops_exception_rpt_curr"
  "common/workflow_queue|refresh_workflow_queue_rpt_curr"
)

echo "=== Consolidation snapshot demo QA | client=$CLIENT | $(date -u +%Y-%m-%dT%H:%M:%SZ) ===" | tee "$LOG_DIR/qa_run.log"

echo "--- Deploy 02a procedures ---" | tee -a "$LOG_DIR/qa_run.log"
for entry in "${SNAPSHOTS[@]}"; do
  path="${entry%%|*}"
  proc="${entry##*|}"
  sql_file="$ROOT/sql/performance/snapshots/${path}/02a_full_history_refresh_procedure.sql"
  echo "DEPLOY $proc" | tee -a "$LOG_DIR/qa_run.log"
  "${RUNNER[@]}" --file "$sql_file" --log-file "$LOG_DIR/deploy_${proc}.log"
done

echo "--- Refresh all snapshots ---" | tee -a "$LOG_DIR/qa_run.log"
for entry in "${SNAPSHOTS[@]}"; do
  proc="${entry##*|}"
  refresh_sql="$LOG_DIR/_refresh_${proc}.sql"
  cat >"$refresh_sql" <<EOF
BEGIN cisadm.${proc}; END;
/
EOF
  echo "REFRESH $proc" | tee -a "$LOG_DIR/qa_run.log"
  "${RUNNER[@]}" --file "$refresh_sql" --log-file "$LOG_DIR/refresh_${proc}.log"
done

echo "--- Procedure compile status ---" | tee -a "$LOG_DIR/qa_run.log"
"${RUNNER[@]}" --sql "
SELECT object_name, status
FROM all_objects
WHERE owner = 'CISADM'
  AND object_type = 'PROCEDURE'
  AND object_name LIKE 'REFRESH_%_RPT_CURR'
ORDER BY object_name
" | tee -a "$LOG_DIR/qa_run.log"

echo "--- Row counts ---" | tee -a "$LOG_DIR/qa_run.log"
"${RUNNER[@]}" --sql "
SELECT 'ACCT_CUSTOMER_RPT_CURR' AS table_name, COUNT(*) AS row_count FROM cisadm.acct_customer_rpt_curr
UNION ALL SELECT 'CASE_PREM_CONTACT_RPT_CURR', COUNT(*) FROM cisadm.case_prem_contact_rpt_curr
UNION ALL SELECT 'NEW_SERVICE_PIPELINE_RPT_CURR', COUNT(*) FROM cisadm.new_service_pipeline_rpt_curr
UNION ALL SELECT 'FIELD_ACTIVITY_RPT_CURR', COUNT(*) FROM cisadm.field_activity_rpt_curr
UNION ALL SELECT 'CREW_OPS_RPT_CURR', COUNT(*) FROM cisadm.crew_ops_rpt_curr
UNION ALL SELECT 'DEVICE_SP_RPT_CURR', COUNT(*) FROM cisadm.device_sp_rpt_curr
UNION ALL SELECT 'PAY_EVENT_RPT_CURR', COUNT(*) FROM cisadm.pay_event_rpt_curr
UNION ALL SELECT 'BILLABLE_CHARGE_RPT_CURR', COUNT(*) FROM cisadm.billable_charge_rpt_curr
UNION ALL SELECT 'SA_AGED_BAL_RPT_CURR', COUNT(*) FROM cisadm.sa_aged_bal_rpt_curr
UNION ALL SELECT 'WO_PROC_RPT_CURR', COUNT(*) FROM cisadm.wo_proc_rpt_curr
UNION ALL SELECT 'OPS_EXCEPTION_RPT_CURR', COUNT(*) FROM cisadm.ops_exception_rpt_curr
UNION ALL SELECT 'WORKFLOW_QUEUE_RPT_CURR', COUNT(*) FROM cisadm.workflow_queue_rpt_curr
ORDER BY 1
" | tee -a "$LOG_DIR/qa_run.log"

echo "--- Package validation scripts ---" | tee -a "$LOG_DIR/qa_run.log"
for entry in "${SNAPSHOTS[@]}"; do
  path="${entry%%|*}"
  proc="${entry##*|}"
  val_file="$ROOT/sql/performance/snapshots/${path}/04_validation_queries.sql"
  echo "VALIDATE $proc" | tee -a "$LOG_DIR/qa_run.log"
  "${RUNNER[@]}" --file "$val_file" --log-file "$LOG_DIR/validate_${proc}.log" || true
done

echo "--- Extended null audit ---" | tee -a "$LOG_DIR/qa_run.log"
"${RUNNER[@]}" --file "$ROOT/sql/performance/snapshots/docs/consolidation_demo_qa_extended.sql" \
  --log-file "$LOG_DIR/validate_extended.log" || true

echo "=== QA run complete | log: $LOG_DIR/qa_run.log ===" | tee -a "$LOG_DIR/qa_run.log"
