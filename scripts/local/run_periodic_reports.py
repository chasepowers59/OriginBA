#!/usr/bin/env python3
"""
Run utility periodic report SQL packs.

Usage:
  python3 scripts/local/run_periodic_reports.py --client odessa_dev --all
  python3 scripts/local/run_periodic_reports.py --client odessa_dev --frequency annual
  python3 scripts/local/run_periodic_reports.py --client odessa_dev --workstream billing
  python3 scripts/local/run_periodic_reports.py --client odessa_dev --report A1
  python3 scripts/local/run_periodic_reports.py --client odessa_dev --validate
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS_ROOT = REPO_ROOT / "sql" / "periodic_reports"
MANIFEST_PATH = REPORTS_ROOT / "runner_manifest.json"
RUNNER = REPO_ROOT / "scripts" / "local" / "run_client_oracle_sql.py"

WORKSTREAMS = ("billing", "finance", "payments", "workflow", "usage", "field_ops", "executive")
FREQUENCIES = ("annual", "quarterly", "semi_annual")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run utility periodic report SQL packs.")
    parser.add_argument("--client", default="odessa_dev")
    parser.add_argument("--frequency", choices=FREQUENCIES)
    parser.add_argument("--workstream", choices=WORKSTREAMS)
    parser.add_argument("--report", help="Report ID from manifest (e.g. A1, Q3)")
    parser.add_argument("--all", action="store_true", help="Run all reports in manifest order")
    parser.add_argument("--validate", action="store_true", help="Run prerequisite + smoke validation only")
    parser.add_argument("--report-file", help="Write full run output to this path")
    parser.add_argument("--quiet", action="store_true")
    return parser.parse_args()


def load_manifest() -> list[dict]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return data["reports"]


def run_sql(client: str, sql_file: Path) -> tuple[int, str]:
    cmd = [sys.executable, str(RUNNER), "--client", client, "--file", str(sql_file)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def print_section(title: str, *, emit) -> None:
    emit(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def select_reports(args: argparse.Namespace, manifest: list[dict]) -> list[dict]:
    if args.report:
        matches = [r for r in manifest if r["id"].upper() == args.report.upper()]
        if not matches:
            raise SystemExit(f"Unknown report id: {args.report}")
        return matches
    if not args.all and not args.frequency and not args.workstream:
        raise SystemExit("Specify --all, --frequency, --workstream, --report, or --validate")
    selected = manifest
    if args.frequency:
        selected = [r for r in selected if r["frequency"] == args.frequency]
    if args.workstream:
        selected = [r for r in selected if r["workstream"] == args.workstream]
    return selected


def main() -> int:
    args = parse_args()
    manifest = load_manifest()

    report_handle = None
    if args.report_file:
        report_path = Path(args.report_file).expanduser().resolve()
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_handle = report_path.open("w", encoding="utf-8")

    def emit(message: str = "") -> None:
        if not args.quiet:
            print(message)
        if report_handle is not None:
            report_handle.write(message + "\n")

    emit(f"# Periodic reports run — {datetime.now(timezone.utc).isoformat()}")
    emit(f"# client={args.client}")

    if args.validate:
        for name in ("00_prerequisite_snapshot_coverage.sql", "01_row_count_smoke.sql"):
            path = REPORTS_ROOT / "validation" / name
            print_section(f"VALIDATION: {name}", emit=emit)
            code, out = run_sql(args.client, path)
            emit(out.rstrip())
            if code != 0:
                if report_handle:
                    report_handle.close()
                return code
        emit("\nValidation complete.")
        if report_handle:
            report_handle.close()
        return 0

    try:
        targets = select_reports(args, manifest)
    except SystemExit as exc:
        if report_handle:
            report_handle.close()
        print(str(exc), file=sys.stderr)
        return 2

    pass_count = fail_count = 0
    results: list[tuple[str, str, int]] = []

    for entry in targets:
        path = REPORTS_ROOT / entry["file"]
        if not path.exists():
            print_section(f"REPORT [{entry['id']}]: MISSING {entry['file']}", emit=emit)
            results.append((entry["id"], "MISSING", 2))
            fail_count += 1
            continue
        print_section(
            f"REPORT [{entry['id']}]: {entry['file']} ({entry['frequency']}/{entry['workstream']})",
            emit=emit,
        )
        code, out = run_sql(args.client, path)
        emit(out.rstrip())
        status = "PASS" if code == 0 else "FAIL"
        if code == 0:
            pass_count += 1
        else:
            fail_count += 1
        results.append((entry["id"], status, code))

    print_section("SUMMARY", emit=emit)
    for report_id, status, code in results:
        emit(f"  {status:8} {report_id} (exit {code})")
    emit(f"\n  Passed: {pass_count}  Failed: {fail_count}")

    if fail_count:
        emit("\nPeriodic reports FAILED.")
        exit_code = 1
    else:
        emit("\nPeriodic reports PASSED.")
        exit_code = 0

    if report_handle:
        report_handle.close()
        if not args.quiet:
            print(f"\nReport written to {args.report_file}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
