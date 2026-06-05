#!/usr/bin/env python3
"""
Run one named snapshot rollout step for one or more SmartCity clients.

Compound install steps chain deploy actions with install-time validation gates
and fail fast when baseline jobs or snapshot sanity checks do not pass.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


FRESH_CLIENTS = ["newark", "fonddulac", "collegestation", "citycorp"]
ALL_CLIENTS = FRESH_CLIENTS + ["ellensburg", "demo"]
SIX_MONTH_ROLLING_DEPLOY = (
    "sql/performance/snapshots/deployment_steps/clients/citycorp/05_deploy_6month_rolling_window_updates.sql"
)
SIX_MONTH_SCHEDULE = (
    "sql/performance/snapshots/deployment_steps/clients/citycorp/07_schedule_all_active_snapshots.sql"
)

STEPS = {
    "preflight": "sql/performance/snapshots/impact/16_snapshot_access_verification.sql",
    "create-tables": "sql/performance/snapshots/deployment_steps/01_create_all_active_snapshot_tables.sql",
    "deploy-baseline-procs": "sql/performance/snapshots/deployment_steps/02_deploy_all_initial_full_history_procedures.sql",
    "schedule-baseline": "sql/performance/snapshots/deployment_steps/03a_schedule_all_initial_full_history_refreshes.sql",
    "baseline-status": "sql/performance/snapshots/deployment_steps/03b_capture_initial_full_history_job_status.sql",
    "baseline-jobs-gate": "sql/performance/snapshots/deployment_steps/03d_baseline_jobs_ready_gate.sql",
    "retry-bseg-billed-baseline": "sql/performance/snapshots/deployment_steps/03c_schedule_bseg_billed_baseline_retry.sql",
    "validate": "sql/performance/snapshots/deployment_steps/04_validate_all_active_snapshots.sql",
    "install-validation-gate": "sql/performance/snapshots/deployment_steps/04b_snapshot_install_validation_gate.sql",
    "deploy-rolling-procs": "sql/performance/snapshots/deployment_steps/05_deploy_all_rolling_window_updates.sql",
    "run-operational": "sql/performance/snapshots/deployment_steps/06_run_all_operational_refreshes.sql",
    "schedule-operational": "sql/performance/snapshots/deployment_steps/07_schedule_all_active_snapshots.sql",
    "latest-runs": "sql/performance/snapshots/deployment_steps/08_capture_latest_active_snapshot_runs.sql",
    "deploy-6month-rolling": SIX_MONTH_ROLLING_DEPLOY,
    "schedule-operational-6month": SIX_MONTH_SCHEDULE,
    "citycorp-deploy-6month-rolling": SIX_MONTH_ROLLING_DEPLOY,
    "citycorp-run-operational": (
        "sql/performance/snapshots/deployment_steps/clients/citycorp/06_run_operational_refreshes.sql"
    ),
    "citycorp-schedule-operational": SIX_MONTH_SCHEDULE,
    "run-baseline-now": (
        "sql/performance/snapshots/deployment_steps/clients/demo/run_all_baseline_refreshes_now.sql"
    ),
    "run-baseline-remaining": (
        "sql/performance/snapshots/deployment_steps/clients/demo/run_remaining_baseline_refreshes_now.sql"
    ),
}


@dataclass(frozen=True)
class StepAction:
    step: str
    fail_if_any_rows: bool = False
    log_label: str | None = None


COMPOUND_STEPS: dict[str, list[StepAction]] = {
    "baseline-and-validate": [
        StepAction("baseline-status", log_label="baseline_status"),
        StepAction("baseline-jobs-gate", fail_if_any_rows=True),
        StepAction("validate", log_label="full_validate"),
        StepAction("install-validation-gate", fail_if_any_rows=True),
    ],
    "operational-and-validate": [
        StepAction("run-operational"),
        StepAction("validate", log_label="full_validate"),
        StepAction("install-validation-gate", fail_if_any_rows=True),
    ],
    "cutover-and-validate": [
        StepAction("deploy-rolling-procs"),
        StepAction("run-operational"),
        StepAction("validate", log_label="full_validate"),
        StepAction("install-validation-gate", fail_if_any_rows=True),
    ],
}

SIMPLE_STEPS = sorted(STEPS)
COMPOUND_STEP_NAMES = sorted(COMPOUND_STEPS)
ALL_STEP_NAMES = sorted(set(SIMPLE_STEPS) | set(COMPOUND_STEP_NAMES))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a named snapshot rollout step.")
    parser.add_argument("--step", choices=ALL_STEP_NAMES, required=True)
    parser.add_argument(
        "--clients",
        default="fresh",
        help="Comma-separated clients, 'fresh', or 'all'. Fresh excludes Ellensburg.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--log-dir",
        default="deploy/snapshot_rollout_logs",
        help="Directory for chained step logs (compound steps only).",
    )
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


def run_single_step(
    *,
    repo_root: Path,
    runner: Path,
    client: str,
    step: str,
    dry_run: bool,
    fail_if_any_rows: bool = False,
    log_file: Path | None = None,
) -> int:
    sql_file = repo_root / STEPS[step]
    cmd = [
        sys.executable,
        str(runner),
        "--client",
        client,
        "--file",
        str(sql_file),
    ]
    if dry_run:
        cmd.append("--dry-run")
    if fail_if_any_rows:
        cmd.append("--fail-if-any-rows")
    if log_file is not None:
        cmd.extend(["--log-file", str(log_file)])

    print(f"\n=== {client}: {step} ===")
    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode


def run_compound_step(
    *,
    repo_root: Path,
    runner: Path,
    client: str,
    compound_name: str,
    dry_run: bool,
    log_dir: Path,
) -> int:
    actions = COMPOUND_STEPS[compound_name]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    client_log_dir = log_dir / client / compound_name
    client_log_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'=' * 72}")
    print(f"{client}: {compound_name} ({len(actions)} chained actions)")
    print(f"Logs: {client_log_dir}")
    print(f"{'=' * 72}")

    for index, action in enumerate(actions, start=1):
        log_file = None
        if action.log_label:
            log_file = client_log_dir / f"{index:02d}_{action.log_label}_{stamp}.log"

        exit_code = run_single_step(
            repo_root=repo_root,
            runner=runner,
            client=client,
            step=action.step,
            dry_run=dry_run,
            fail_if_any_rows=action.fail_if_any_rows,
            log_file=log_file,
        )
        if exit_code != 0:
            print(f"\nFAILED: {client} {compound_name} stopped at step {action.step}")
            summary = client_log_dir / f"FAILED_{stamp}.txt"
            summary.write_text(
                f"client={client}\ncompound={compound_name}\nfailed_step={action.step}\n",
                encoding="utf-8",
            )
            return exit_code

    passed = client_log_dir / f"PASSED_{stamp}.txt"
    passed.write_text(
        f"client={client}\ncompound={compound_name}\nstatus=PASSED\n",
        encoding="utf-8",
    )
    print(f"\nPASSED: {client} {compound_name}")
    return 0


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    runner = repo_root / "scripts/local/run_client_oracle_sql.py"
    clients = expand_clients(args.clients)
    log_dir = (repo_root / args.log_dir).resolve()

    for client in clients:
        if args.step in COMPOUND_STEPS:
            exit_code = run_compound_step(
                repo_root=repo_root,
                runner=runner,
                client=client,
                compound_name=args.step,
                dry_run=args.dry_run,
                log_dir=log_dir,
            )
        else:
            exit_code = run_single_step(
                repo_root=repo_root,
                runner=runner,
                client=client,
                step=args.step,
                dry_run=args.dry_run,
            )
        if exit_code != 0:
            return exit_code

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
