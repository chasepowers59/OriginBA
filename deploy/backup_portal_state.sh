#!/bin/bash
# Backup the portal's control-plane data: auth tables (portal_users, groups,
# audit log) and the portal_state schema (saved views, dashboards, schedules,
# alerts, annotations). The WAREHOUSE is rebuilt from dbt and is NOT backed up
# here — this protects the state users create by hand.
#
# Usage:  PORTAL_AUTH_DATABASE_URL=postgresql://... ./backup_portal_state.sh [outdir]
# Cron:   daily, alongside the report-schedule runner.
# The URL contains the password: it is passed to pg_dump via the environment and
# never echoed.
set -euo pipefail

OUTDIR="${1:-./backups}"

if [[ -z "${PORTAL_AUTH_DATABASE_URL:-}" ]]; then
  echo "PORTAL_AUTH_DATABASE_URL is not set — nothing to back up." >&2
  echo "Point it at the Supabase (or other Postgres) control-plane database." >&2
  exit 1
fi

mkdir -p "$OUTDIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$OUTDIR/portal_state_${STAMP}.sql.gz"

echo "Backing up portal auth tables + portal_state schema -> $OUT"
pg_dump "$PORTAL_AUTH_DATABASE_URL" \
  --no-owner --no-privileges \
  --schema=portal_state \
  --table='portal_users' \
  --table='portal_audit_log' \
  --table='portal_access_groups' \
  --table='portal_user_access_groups' \
  | gzip > "$OUT"

SIZE="$(du -h "$OUT" | cut -f1)"
echo "Done: $OUT ($SIZE)"
echo "Restore with: gunzip -c $OUT | psql \"\$PORTAL_AUTH_DATABASE_URL\""
