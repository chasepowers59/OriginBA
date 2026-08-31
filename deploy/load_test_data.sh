#!/usr/bin/env bash
# Load the fabricated reporting fixtures (all 38 canvases) into a target Postgres,
# e.g. Supabase. The target URL — which contains YOUR database password — is read
# from the environment or prompted for; it is never printed or logged.
#
#   TARGET_DB_URL='postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres' \
#     ./deploy/load_test_data.sh
#
# Get the URL from Supabase → Connect → "Session pooler" (IPv4, port 5432). The
# "Direct connection" host (db.<ref>.supabase.co) is IPv6-only and will not resolve
# on an IPv4 network. Session pooler supports the full protocol a bulk load needs;
# the app itself uses the Transaction pooler (6543) at runtime.
set -euo pipefail

# local fixtures warehouse (the docker container on 5433)
SRC_HOST="${SRC_HOST:-localhost}"; SRC_PORT="${SRC_PORT:-5433}"
SRC_USER="${SRC_USER:-originba}"; SRC_DB="${SRC_DB:-originba_training}"
export PGPASSWORD="${SRC_PGPASSWORD:-originba}"

if [ -z "${TARGET_DB_URL:-}" ]; then
  read -r -s -p "Supabase direct connection URL (postgresql://…:5432/postgres): " TARGET_DB_URL
  echo
fi

# prefer a matching pg_dump; Homebrew keeps versioned ones under /opt/homebrew/opt
for d in /opt/homebrew/opt/postgresql@16/bin /opt/homebrew/opt/postgresql@17/bin; do
  [ -d "$d" ] && PATH="$d:$PATH"
done
command -v pg_dump >/dev/null || { echo "pg_dump not found (brew install postgresql@16)"; exit 1; }

# The SQL workspace queries the CISADM schema (what analysts know), so ship it
# alongside the reporting canvases. Secrets stay out of the cloud: MICR_ID,
# WEB_PASSWD% and ALERT_INFO are nulled post-load (the app's SQL fence blocks
# them too — this is defense in depth for the cloud copy).
echo "Dumping cisadm.* + reporting.* from ${SRC_DB} and loading into the target…"
pg_dump -h "$SRC_HOST" -p "$SRC_PORT" -U "$SRC_USER" -d "$SRC_DB" \
  -n cisadm -n reporting --no-owner --no-privileges \
  | psql "$TARGET_DB_URL" -v ON_ERROR_STOP=1 -q

echo "Nulling protected columns in the cloud copy…"
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
           OR lower(column_name) = 'alert_info')
  LOOP
    EXECUTE format('UPDATE cisadm.%I SET %I = NULL WHERE %I IS NOT NULL',
                   r.table_name, r.column_name, r.column_name);
  END LOOP;
END $$;
SQL

echo "Done. Verifying a couple of canvases:"
psql "$TARGET_DB_URL" -tAc \
  "select 'rpt_financial_txn='||count(*) from reporting.rpt_financial_txn
   union all select 'rpt_bill_segment='||count(*) from reporting.rpt_bill_segment;"
echo "Loaded. Point WAREHOUSE_DATABASE_URL at this database (pooled URL, port 6543)."
