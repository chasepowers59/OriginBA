#!/usr/bin/env bash
# Load the fabricated reporting fixtures (all 38 canvases) into a target Postgres,
# e.g. Supabase. The target URL — which contains YOUR database password — is read
# from the environment or prompted for; it is never printed or logged.
#
#   TARGET_DB_URL='postgresql://postgres:<pw>@db.<ref>.supabase.co:5432/postgres' \
#     ./deploy/load_test_data.sh
#
# Get the URL from Supabase → Connect → "Direct connection" (port 5432); use the
# direct connection (not the 6543 pooler) for a bulk load. The app itself uses the
# pooled URL at runtime.
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

echo "Dumping reporting.* from ${SRC_DB} and loading into the target…"
pg_dump -h "$SRC_HOST" -p "$SRC_PORT" -U "$SRC_USER" -d "$SRC_DB" \
  -n reporting --no-owner --no-privileges \
  | psql "$TARGET_DB_URL" -v ON_ERROR_STOP=1 -q

echo "Done. Verifying a couple of canvases:"
psql "$TARGET_DB_URL" -tAc \
  "select 'rpt_financial_txn='||count(*) from reporting.rpt_financial_txn
   union all select 'rpt_bill_segment='||count(*) from reporting.rpt_bill_segment;"
echo "Loaded. Point WAREHOUSE_DATABASE_URL at this database (pooled URL, port 6543)."
