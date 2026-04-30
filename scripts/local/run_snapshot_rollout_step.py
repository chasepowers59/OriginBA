#!/usr/bin/env python3
"""
Run one named snapshot rollout step for one or more SmartCity clients.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


FRESH_CLIENTS = ["newark", "fonddulac", "collegestation", "citycorp"]
ALL_CLIENTS = FRESH_CLIENTS + ["ellensburg"]

STEPS = {
    "preflight": "sql/performance/snapshots/impact/16_snapshot_access_verification.sql",
    "create-tables": "sql/performance/snapshots/deployment_steps/01_create_all_active_snapshot_tables.sql",
    "deploy-baseline-procs": "sql/performance/snapshots/deployment_steps/02_deploy_all_initial_full_history_procedures.sql",
    "schedule-baseline": "sql/performance/snapshots/deployment_steps/03a_schedule_all_initial_full_history_refreshes.sql",
    "baseline-status": "sql/performance/snapshots/deployment_steps/03b_capture_initial_full_history_job_status.sql",
    "validate": "sql/performance/snapshots/deployment_steps/04_validate_all_active_snapshots.sql",
    "deploy-rolling-procs": "sql/performance/snapshots/deployment_steps/05_deploy_all_rolling_window_updates.sql",
    "run-operational": "sql/performance/snapshots/deployment_steps/06_run_all_operational_refreshes.sql",
    "schedule-operational": "sql/performance/snapshots/deployment_steps/07_schedule_all_active_snapshots.sql",
    "latest-runs": "sql/performance/snapshots/deployment_steps/08_capture_latest_active_snapshot_runs.sql",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a named snapshot rollout step.")
    parser.add_argument("--step", choices=sorted(STEPS), required=True)
    parser.add_argument(
        "--clients",
        default="fresh",
        help="Comma-separated clients, 'fresh', or 'all'. Fresh excludes Ellensburg.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def expand_clients(value: str) -> list[str]:
    normalized = value.strip().lower()
    if normalized == "fresh":
        return FRESH_CLIENTS
    if normalized == "all":
        return ALL_CLIENTS
    clients = [client.strip().lower() for client in normalized.split(",") if client.strip()]
    unknown = sorted(set(clients) - set(ALL_CLIENTS))
    if unknown:
        raise SystemExit(f"Unknown clients: {', '.join(unknown)}")
    return clients


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    runner = repo_root / "scripts/local/run_client_oracle_sql.py"
    sql_file = repo_root / STEPS[args.step]
    clients = expand_clients(args.clients)

    for client in clients:
        print(f"\n=== {client}: {args.step} ===")
        cmd = [
            sys.executable,
            str(runner),
            "--client",
            client,
            "--file",
            str(sql_file),
        ]
        if args.dry_run:
            cmd.append("--dry-run")
        result = subprocess.run(cmd, cwd=repo_root)
        if result.returncode != 0:
            return result.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
