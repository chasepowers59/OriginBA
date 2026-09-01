"""Cron entry point for scheduled report delivery.

Run every hour (Render cron job, launchd, or crontab):

    python -m api.report_schedule_runner            # deliver everything due
    python -m api.report_schedule_runner --dry-run  # render only, send nothing

Needs the same env as the API (PORTAL_AUTH_DATABASE_URL / WAREHOUSE_DATABASE_URL /
SMTP_*). Exits 0 when every due schedule delivered, 1 when any errored — so the
cron's own alerting sees failures.
"""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Deliver due report schedules")
    parser.add_argument("--dry-run", action="store_true",
                        help="render due schedules but do not send or mark them run")
    args = parser.parse_args()

    from api.report_schedules import run_due_schedules, smtp_configured

    if not args.dry_run and not smtp_configured():
        print("SMTP_HOST is not configured; refusing a live run (use --dry-run).")
        return 1

    failed = 0

    results = run_due_schedules(dry_run=args.dry_run)
    for r in results:
        line = f"[{r['status']}] {r.get('view')} -> {', '.join(r.get('recipients', []))}"
        if "row_count" in r:
            line += f" ({r['row_count']} rows)"
        print(line)
        if str(r["status"]).startswith("error"):
            failed += 1

    # KPI threshold alerts ride the same hourly heartbeat (skipped on dry-run:
    # evaluating a KPI hits the warehouse, and dry-run promises no side effects
    # on alert state).
    if not args.dry_run:
        from api.kpi_alerts import run_kpi_alerts
        for r in run_kpi_alerts():
            print(f"[alert {r['status']}] {r.get('kpi')} -> {', '.join(r.get('recipients', []))}")
            if str(r["status"]).startswith("error"):
                failed += 1

    if not results:
        print("No schedules due.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
