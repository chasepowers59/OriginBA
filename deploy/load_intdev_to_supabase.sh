#!/usr/bin/env bash
# Build the REAL INT_DEV 25.4 reporting layer and load it into Supabase, replacing the
# fabricated fixtures. INT_DEV is internal Origin dev data (real C2M 25.4 shape, no client
# PII), which is why it is the one warehouse safe to put in a cloud database.
#
# One command, run from the OriginBA-3 repo root, with VPN ON:
#
#   TARGET_DB_URL='postgresql://postgres.<ref>:<pw>@aws-0-<region>.pooler.supabase.com:5432/postgres' \
#     ./deploy/load_intdev_to_supabase.sh
#
# TARGET_DB_URL contains your Supabase password and is read from the environment only —
# never printed, never committed. Use the Supabase "Session pooler" URL (IPv4, port 5432)
# for the bulk load; the app itself reads the Transaction pooler (6543) at runtime.
#
# What it does (each step is skippable via SKIP_EXTRACT / SKIP_DBT once the DB is built):
#   1. Preflight: VPN reachability, TARGET_DB_URL, the dbt venv.
#   2. Extract the INT_DEV Oracle census into a local Postgres landing DB (VPN).
#   3. dbt build the staging -> core -> reporting layer (full-refresh AND incremental).
#   4. Dump reporting.* into Supabase via the existing, secret-safe load_test_data.sh.
#
# Requires: the pinned dbt venv in the dbt repo, VPN to the INT_DEV Oracle host, and the
# INT_DEV_* credentials in OriginBA-3/.env (or point INTDEV_ENV_FILE / *_KEY at them).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(cd "$HERE/.." && pwd)"
DBT_DIR="${ORIGINBA_DBT_DIR:-$(cd "$APP_DIR/../originba_dbt" && pwd)}"

# The local landing DB (Homebrew Postgres on 5432, beside originba_v2). Never the docker
# fixtures container on 5433 — that holds the fabricated data we are replacing.
PG_DB="${INTDEV_PG_DB:-originba_v2_int_dev_full}"
SRC_HOST="${SRC_HOST:-localhost}"; SRC_PORT="${SRC_PORT:-5432}"
SRC_USER="${SRC_USER:-$(whoami)}"

# INT_DEV credential resolution for the extractor (defaults read OriginBA-3/.env).
INTDEV_ENV_FILE="${INTDEV_ENV_FILE:-$APP_DIR/.env}"
INTDEV_USER_KEY="${INTDEV_USER_KEY:-INT_DEV_DB_USER}"
INTDEV_PASSWORD_KEY="${INTDEV_PASSWORD_KEY:-INT_DEV_DB_PASSWORD}"
INTDEV_DSN_KEY="${INTDEV_DSN_KEY:-INT_DEV_ORACLE_DSN}"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
die() { printf '\n\033[1;31mERROR: %s\033[0m\n' "$*" >&2; exit 1; }

# ---- 1. Preflight -----------------------------------------------------------------
say "Preflight"
[ -n "${TARGET_DB_URL:-}" ] || die "Set TARGET_DB_URL to the Supabase Session-pooler URL (see the header)."
[ -x "$DBT_DIR/.venv/bin/dbt" ] || die "dbt venv not found at $DBT_DIR/.venv — set ORIGINBA_DBT_DIR or create it."
[ -f "$INTDEV_ENV_FILE" ] || die "INT_DEV env file not found at $INTDEV_ENV_FILE (set INTDEV_ENV_FILE)."

# VPN / Oracle reachability: resolve the INT_DEV DSN host. Off-VPN this is ORA-12262.
DSN_LINE="$(grep -E "^${INTDEV_DSN_KEY}=" "$INTDEV_ENV_FILE" | head -1 | cut -d= -f2- || true)"
DSN_HOST="$(printf '%s' "$DSN_LINE" | tr -d '"' | sed -E 's#^.*@##; s#[:/].*$##' )"
[ -n "$DSN_HOST" ] || die "Could not read ${INTDEV_DSN_KEY} from $INTDEV_ENV_FILE."
if ! ping -c1 -t2 "$DSN_HOST" >/dev/null 2>&1 && ! nc -z -G2 "$DSN_HOST" 1521 >/dev/null 2>&1; then
  die "INT_DEV Oracle host '$DSN_HOST' is unreachable — connect the VPN and retry."
fi
command -v pg_dump >/dev/null 2>&1 || for d in /opt/homebrew/opt/postgresql@16/bin /opt/homebrew/opt/postgresql@17/bin; do [ -d "$d" ] && PATH="$d:$PATH"; done
command -v createdb >/dev/null || die "Postgres client tools (createdb/psql/pg_dump) not on PATH."
say "Preflight OK — VPN reachable, target + venv present."

cd "$DBT_DIR"

# ---- 2. Extract INT_DEV -> local Postgres landing ---------------------------------
if [ "${SKIP_EXTRACT:-0}" != "1" ]; then
  say "Extracting INT_DEV census into $PG_DB (this is slow — LOB reads + FK walk)"
  createdb "$PG_DB" 2>/dev/null || echo "  ($PG_DB already exists — reusing)"
  psql -d "$PG_DB" -v ON_ERROR_STOP=1 -q -f scripts/landing/01_create_landing_full.sql
  .venv/bin/python scripts/landing/extract_full.py \
    --client int_dev --pg-db "$PG_DB" \
    --env-file "$INTDEV_ENV_FILE" \
    --user-key "$INTDEV_USER_KEY" --password-key "$INTDEV_PASSWORD_KEY" --dsn-key "$INTDEV_DSN_KEY"
  psql -d "$PG_DB" -c "analyze" -q
else
  echo "SKIP_EXTRACT=1 — reusing existing $PG_DB"
fi

# ---- 3. Build the reporting layer (both paths, per CI discipline) -----------------
if [ "${SKIP_DBT:-0}" != "1" ]; then
  say "dbt build (full-refresh) on $PG_DB"
  DEV_PG_DBNAME="$PG_DB" .venv/bin/dbt build --target dev --full-refresh
  say "dbt build (incremental path)"
  DEV_PG_DBNAME="$PG_DB" .venv/bin/dbt build --target dev
else
  echo "SKIP_DBT=1 — assuming reporting.* is already built in $PG_DB"
fi

# Safety: the no-MICR test must have passed above; refuse to ship if MICR leaked.
if psql -d "$PG_DB" -tAc "select 1 from information_schema.columns where table_schema='reporting' and lower(column_name) like '%micr%' limit 1" | grep -q 1; then
  die "A MICR column reached the reporting layer — refusing to load to the cloud. Investigate before retrying."
fi

# ---- 4. Load reporting.* into Supabase (reuses the secret-safe loader) -------------
say "Loading reporting.* from $PG_DB into Supabase"
SRC_HOST="$SRC_HOST" SRC_PORT="$SRC_PORT" SRC_USER="$SRC_USER" SRC_DB="$PG_DB" \
  SRC_PGPASSWORD="${SRC_PGPASSWORD:-}" TARGET_DB_URL="$TARGET_DB_URL" \
  "$APP_DIR/deploy/load_test_data.sh"

say "Done. INT_DEV 25.4 reporting layer is in Supabase."
cat <<'NOTE'

Next:
  • Point WAREHOUSE_DATABASE_URL (Render, the `dev` org) at this Supabase DB (Transaction
    pooler, port 6543) and redeploy the API.
  • Real INT_DEV data has real (older) dates, so the exec dashboard's trailing windows may
    look sparse. Decide ONE of: (a) set the dashboard's default window to the data's max
    date, or (b) date-shift the loaded rows so recent windows populate — do NOT silently
    mutate values; add a "data as of <max date>" note if you shift.
NOTE
