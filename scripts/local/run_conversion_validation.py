#!/usr/bin/env python3
"""
Run conversion validation gates and discovery profiles by workstream.

Usage:
  python3 scripts/local/run_conversion_validation.py --client odessa_dev
  python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream billing
  python3 scripts/local/run_conversion_validation.py --client odessa_dev --discovery-only
  python3 scripts/local/run_conversion_validation.py --client odessa_dev --reference citycorp
  python3 scripts/local/run_conversion_validation.py --client odessa_dev --gates-only --report-file /tmp/validation.txt
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATION_ROOT = REPO_ROOT / "sql" / "odessa_dev" / "conversion_validation"
RUNNER = REPO_ROOT / "scripts" / "local" / "run_client_oracle_sql.py"

WORKSTREAMS = ("billing", "workflow", "meter_ops", "devices", "field_ops", "vee", "usage")

# Gate filename stems that emit WARN — pass exit code unless --strict-warn.
WARN_GATES = {
    "02_install_event_off_population",
    "06_bseg_sq_days_gal_pattern",
    "07_todo_assignee_population",
    "install_event_off_population",
    "bseg_sq_days_gal_pattern",
    "todo_assignee_population",
    "ft_bill_sa_linkage",
    "todo_open_fk_account_resolution",
    "measurement_without_measr_comp",
    "vee_imd_measr_comp_link",
    "usage_c1_bridge_rate",
}

DISCOVERY_COMPARE_ROWS = [
    ("Install OFF count", "01_install_event_profile", r"OFF\s*\|\s*(\d+)"),
    (
        "Bill header blank (acct has cycle)",
        "02_billing_device_bridge_profile",
        r"BILL_HEADER_BLANK \| BILL_HEADER_POPULATED\s*\n[-+]+\s*\n\d+\s*\|\s*(\d+)",
    ),
    (
        "D1EI missing on ON installs",
        "02_billing_device_bridge_profile",
        r"MISSING_D1EI\s*\n[-+]+\s*\n\d+\s*\|\s*\d+\s*\|\s*(\d+)",
    ),
    (
        "Water SQ DAYS/GAL/1",
        "02_billing_device_bridge_profile",
        r"DAYS_GAL_ONE\s*\n[-+]+\s*\n\d+\s*\|\s*(\d+)",
    ),
    (
        "Frozen water bseg w/o SQ",
        "03_billing_profile",
        r"WITHOUT_SQ\s*\n[-+]+\s*\n\d+\s*\|\s*(\d+)",
    ),
    (
        "Open todos blank assignee",
        "04_workflow_profile",
        r"BLANK_ASSIGNEE \| HAS_ASSIGNEE\s*\n[-+]+\s*\n\d+\s*\|\s*(\d+)",
    ),
    ("D1FA activities", "05_field_ops_usage_vee_profile", r"D1FA_ACTIVITY_CNT\s*\n[-+]+\s*\n(\d+)"),
    (
        "D1_USAGE w/ C1 BD-PROC",
        "05_field_ops_usage_vee_profile",
        r"WITH_C1_BD_PROC\s*\n[-+]+\s*\n\d+\s*\|\s*(\d+)",
    ),
]

FAILURE_CNT_RE = re.compile(
    r"SEVERITY\s*\|\s*FAILURE_CNT\s*\n[-+]+\s*\n[^\n]*\|\s*(?:FAIL|WARN)\s*\|\s*([\d,]+)",
    re.IGNORECASE,
)
METRIC_RE = re.compile(
    r"DETAIL\s*\|\s*METRIC\s*\n[-+]+\s*\n[^\n]*\|\s*(?:FAIL|WARN)\s*\|\s*[^\|]+\|\s*(\S+)",
    re.IGNORECASE,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run conversion validation gates by workstream.")
    parser.add_argument("--client", default="odessa_dev")
    parser.add_argument("--reference", help="Reference client for discovery compare (e.g. citycorp)")
    parser.add_argument("--workstream", choices=WORKSTREAMS, help="Run gates for one workstream only")
    parser.add_argument("--discovery-only", action="store_true")
    parser.add_argument("--gates-only", action="store_true", help="Skip discovery profiles")
    parser.add_argument("--gate", help="Run one gate (filename stem)")
    parser.add_argument("--strict-warn", action="store_true", help="Treat WARN gates as failures")
    parser.add_argument("--json", action="store_true")
    parser.add_argument(
        "--report-file",
        help="Write full run output to this path (stdout still prints unless --quiet).",
    )
    parser.add_argument("--quiet", action="store_true", help="Suppress stdout; use with --report-file.")
    return parser.parse_args()


def discovery_files() -> list[Path]:
    return sorted((VALIDATION_ROOT / "discovery").glob("*.sql"))


def gate_files(workstream: str | None = None) -> list[Path]:
    root = VALIDATION_ROOT / "gates"
    if workstream:
        folder = root / workstream
        return sorted(folder.glob("*.sql")) if folder.is_dir() else []
    return sorted(root.rglob("*.sql"))


def run_sql(
    client: str,
    sql_file: Path,
    *,
    fail_if_any_rows: bool,
    as_json: bool,
    fail_last_select_only: bool = False,
) -> tuple[int, str]:
    cmd = [sys.executable, str(RUNNER), "--client", client, "--file", str(sql_file)]
    if fail_if_any_rows:
        cmd.append("--fail-if-any-rows")
    if fail_last_select_only:
        cmd.append("--fail-last-select-only")
    if as_json:
        cmd.extend(["--format", "json"])
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def gate_stem(path: Path) -> str:
    return path.stem


def print_section(title: str, *, emit=print) -> None:
    emit(f"\n{'=' * 72}\n{title}\n{'=' * 72}")


def extract_discovery_metric(output: str, profile_pattern: str, value_pattern: str) -> str | None:
    anchor = re.search(profile_pattern, output, re.IGNORECASE)
    if not anchor:
        return None
    window = output[anchor.start() : anchor.start() + 5000]
    match = re.search(value_pattern, window, re.IGNORECASE)
    return match.group(1).strip() if match else None


def parse_gate_detail(output: str) -> str:
    match = FAILURE_CNT_RE.search(output)
    if match:
        return f"{match.group(1)} failure row(s)"
    match = METRIC_RE.search(output)
    if match:
        return match.group(1)
    return ""


def run_discovery(
    client: str,
    *,
    as_json: bool,
    emit,
    label: str = "DISCOVERY",
) -> tuple[int, str]:
    combined = ""
    for path in discovery_files():
        print_section(f"{label}: {path.name} [{client}]", emit=emit)
        code, out = run_sql(client, path, fail_if_any_rows=False, as_json=as_json)
        emit(out.rstrip())
        combined += out + "\n"
        if code != 0:
            return code, combined
    return 0, combined


def print_discovery_compare(client_out: str, ref_out: str, *, emit) -> None:
    print_section("DISCOVERY COMPARE (client vs reference)", emit=emit)
    emit(f"{'Metric':<40} {'Client':>14} {'Reference':>14}")
    emit("-" * 72)
    for label, profile, pattern in DISCOVERY_COMPARE_ROWS:
        client_val = extract_discovery_metric(client_out, profile, pattern) or "—"
        ref_val = extract_discovery_metric(ref_out, profile, pattern) or "—"
        emit(f"{label:<40} {client_val:>14} {ref_val:>14}")


def main() -> int:
    args = parse_args()
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

    emit(f"# Conversion validation run — {datetime.now(timezone.utc).isoformat()}")
    emit(f"# client={args.client} reference={args.reference or '-'} workstream={args.workstream or 'all'}")

    if args.gate:
        matches = [p for p in gate_files() if p.stem == args.gate or p.name.startswith(args.gate)]
        if not matches:
            emit(f"Unknown gate: {args.gate}")
            if report_handle:
                report_handle.close()
            print(f"Unknown gate: {args.gate}", file=sys.stderr)
            return 2
        targets = matches[:1]
        should_run_discovery = False
    else:
        targets = gate_files(args.workstream)
        should_run_discovery = not args.gates_only

    fail_count = warn_count = pass_count = 0
    client_discovery_out = ref_discovery_out = ""

    if should_run_discovery:
        code, client_discovery_out = run_discovery(args.client, as_json=args.json, emit=emit)
        if code != 0:
            if report_handle:
                report_handle.close()
            return code
        if args.reference:
            code, ref_discovery_out = run_discovery(
                args.reference, as_json=args.json, emit=emit, label="DISCOVERY (ref)"
            )
            if code != 0:
                if report_handle:
                    report_handle.close()
                return code
            print_discovery_compare(client_discovery_out, ref_discovery_out, emit=emit)
        if args.discovery_only:
            emit("\nDiscovery complete.")
            if report_handle:
                report_handle.close()
            return 0

    results: list[tuple[str, str, int, str]] = []
    for path in targets:
        stem = gate_stem(path)
        ws = path.parent.name if path.parent.name != "gates" else "?"
        is_warn = stem in WARN_GATES
        print_section(f"GATE [{ws}]: {path.name} [{args.client}]", emit=emit)
        code, out = run_sql(
            args.client,
            path,
            fail_if_any_rows=True,
            as_json=args.json,
            fail_last_select_only=True,
        )
        emit(out.rstrip())
        detail = parse_gate_detail(out)
        if code == 0:
            status = "PASS"
            pass_count += 1
        elif is_warn and not args.strict_warn:
            status = "WARN"
            warn_count += 1
        else:
            status = "FAIL" if not is_warn else "FAIL(strict)"
            fail_count += 1
        results.append((f"{ws}/{stem}", status, code, detail))

    print_section("SUMMARY", emit=emit)
    for name, status, code, detail in results:
        suffix = f" — {detail}" if detail else ""
        emit(f"  {status:12} {name} (exit {code}){suffix}")
    emit(f"\n  Passed: {pass_count}  Warnings: {warn_count}  Failed: {fail_count}")

    if fail_count > 0:
        emit("\nConversion validation FAILED.")
        exit_code = 1
    elif warn_count > 0:
        emit("\nPassed with WARNINGS (--strict-warn to fail on WARN).")
        exit_code = 0
    else:
        emit("\nConversion validation PASSED.")
        exit_code = 0

    if report_handle:
        report_handle.close()
        if not args.quiet:
            print(f"\nReport written to {args.report_file}")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
