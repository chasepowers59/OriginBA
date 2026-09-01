#!/usr/bin/env bash
# Load the Demo 25.4 warehouse (cisadm + reporting) from the local landing build
# into its OWN Supabase project. The target URL — which contains YOUR database
# password — is read from the environment or prompted for; it is never printed.
#
#   TARGET_DB_URL='postgresql://postgres.<ref>:<pw>@aws-0-us-east-2.pooler.supabase.com:5432/postgres' \
#     ./deploy/load_demo25_to_supabase.sh
#
# Get it from Supabase → Connect → "Session pooler" (IPv4, port 5432) on the
# DEMO 25.4 PROJECT, not the INT_DEV one. Two reasons this gets its own project:
#   - the two instances share ID space (an ACCT_ID already collides), so blending
#     them into one set of tables would corrupt both;
#   - each free project has its own 500 MB, and per-org warehouse URLs are how the
#     portal keeps tenants apart since the 2026-09-01 isolation fix.
# Afterwards set WAREHOUSE_DATABASE_URL_DEMO25 to the POOLED url (port 6543).
set -euo pipefail

SRC_DB="${SRC_DB:-originba_v2_demo25}"
SRC_HOST="${SRC_HOST:-localhost}"; SRC_PORT="${SRC_PORT:-5432}"
SRC_USER="${SRC_USER:-$(whoami)}"

# The free tier is 500 MB and Demo 25.4 is ~4.79M rows, 4.3M of which are two
# tables. They are capped rather than dropped, so the usage and meter-ops canvases
# still have real data in the cloud copy (an empty canvas is a defect this repo
# explicitly watches for).
#
# Capped by ROW COUNT, newest first, not by a date window: measurements and batch
# runs are distributed very differently here (a 12-month window takes 61,652 of
# 3,565,096 measurements but 746,518 of 748,848 batch runs, because the batch
# history is one old block), so a single window cannot bound both.
MSRMT_CAP="${MSRMT_CAP:-100000}"
BATCH_CAP="${BATCH_CAP:-50000}"
# d1_init_msrmt_data is 177 MB for 83,681 rows -- ~2.2 KB each, raw payloads. No mart
# consumes it (stg_init_msrmt_data has no downstream model), so it is capped hardest.
INIT_MSRMT_CAP="${INIT_MSRMT_CAP:-10000}"

if [ -z "${TARGET_DB_URL:-}" ]; then
  read -r -s -p "Supabase session-pooler URL for the DEMO 25.4 project: " TARGET_DB_URL
  echo
fi

for d in /opt/homebrew/opt/postgresql@16/bin /opt/homebrew/opt/postgresql@17/bin; do
  [ -d "$d" ] && PATH="$d:$PATH"
done
command -v pg_dump >/dev/null || { echo "pg_dump not found (brew install postgresql@16)"; exit 1; }

SRC=(-h "$SRC_HOST" -p "$SRC_PORT" -U "$SRC_USER" -d "$SRC_DB")
# The same two facts are giant on BOTH sides: the landing tables and the canvases
# built from them. Capping only the cisadm pair would still ship a 3.5M-row
# rpt_measurement.
BIG=(cisadm.d1_msrmt cisadm.ci_batch_run cisadm.d1_init_msrmt_data
     reporting.rpt_measurement reporting.rpt_batch)

echo "1/4  Structure (cisadm + reporting)…"
pg_dump "${SRC[@]}" -n cisadm -n reporting --schema-only --no-owner --no-privileges \
  | psql "$TARGET_DB_URL" -v ON_ERROR_STOP=1 -q

echo "2/4  Data, excluding the two capped tables…"
pg_dump "${SRC[@]}" -n cisadm -n reporting --data-only --no-owner --no-privileges \
  --exclude-table="${BIG[0]}" --exclude-table="${BIG[1]}" --exclude-table="${BIG[2]}" \
  --exclude-table="${BIG[3]}" --exclude-table="${BIG[4]}" \
  | psql "$TARGET_DB_URL" -v ON_ERROR_STOP=1 -q

echo "3/4  Capped tables (newest ${MSRMT_CAP} measurements, ${BATCH_CAP} batch runs)…"
copy_capped() {  # <source select> <target table>
  psql "${SRC[@]}" -v ON_ERROR_STOP=1 -qAt -c "\\copy ($1) TO STDOUT" \
    | psql "$TARGET_DB_URL" -v ON_ERROR_STOP=1 -q -c "\\copy $2 FROM STDIN"
}
copy_capped "SELECT * FROM cisadm.d1_msrmt ORDER BY msrmt_dttm DESC LIMIT ${MSRMT_CAP}" cisadm.d1_msrmt
copy_capped "SELECT * FROM cisadm.ci_batch_run ORDER BY batch_bus_dt DESC LIMIT ${BATCH_CAP}" cisadm.ci_batch_run
copy_capped "SELECT * FROM cisadm.d1_init_msrmt_data ORDER BY load_dttm DESC LIMIT ${INIT_MSRMT_CAP}" cisadm.d1_init_msrmt_data
# The canvases are capped on the SAME ordering, and they are 1:1 with their landing
# tables here, so the cloud copy stays internally consistent.
copy_capped "SELECT * FROM reporting.rpt_measurement ORDER BY \"Measurement Date/Time\" DESC LIMIT ${MSRMT_CAP}" reporting.rpt_measurement
copy_capped "SELECT * FROM reporting.rpt_batch ORDER BY \"Start Time\" DESC LIMIT ${BATCH_CAP}" reporting.rpt_batch

echo "4/4  Nulling protected columns in the cloud copy…"
# MICR_ID is bank routing, WEB_PASSWD* are credentials, ALERT_INFO is free-text
# operational notes, EXT_ACCT_ID is the external bank account on autopay. The
# app's SQL fence blocks all four; this is defence in depth for the cloud copy.
psql "$TARGET_DB_URL" -v ON_ERROR_STOP=1 -q <<'SQL'
DO $$
DECLARE r record;
BEGIN
  FOR r IN
    SELECT table_name, column_name
    FROM information_schema.columns
    WHERE table_schema = 'cisadm'
      AND (lower(column_name) = 'micr_id'
           OR lower(column_name) LIKE 'web_passwd%'
           OR lower(column_name) = 'alert_info'
           OR lower(column_name) = 'ext_acct_id')
  LOOP
    EXECUTE format('UPDATE cisadm.%I SET %I = NULL WHERE %I IS NOT NULL',
                   r.table_name, r.column_name, r.column_name);
  END LOOP;
END $$;
SQL

echo
echo "Verifying — every protected column must read 0:"
psql "$TARGET_DB_URL" -tAc "
  SELECT 'micr_id='||(SELECT count(micr_id) FROM cisadm.ci_pay_tndr)
       ||' web_passwd='||(SELECT count(web_passwd) FROM cisadm.ci_per)
       ||' web_passwd_ans='||(SELECT count(web_passwd_ans) FROM cisadm.ci_per)
       ||' alert_info='||(SELECT count(alert_info) FROM cisadm.ci_acct)
       ||' ext_acct_id='||(SELECT count(ext_acct_id) FROM cisadm.ci_acct_apay);"

echo "Row totals:"
psql "$TARGET_DB_URL" -tAc "
  SELECT 'cisadm='||(SELECT sum(n_live_tup) FROM pg_stat_user_tables WHERE schemaname='cisadm')
       ||' reporting='||(SELECT sum(n_live_tup) FROM pg_stat_user_tables WHERE schemaname='reporting');"
psql "$TARGET_DB_URL" -tAc "SELECT 'database size = '||pg_size_pretty(pg_database_size(current_database()));"

echo
echo "Done. Set WAREHOUSE_DATABASE_URL_DEMO25 to this project's POOLED url (6543)."
