#!/usr/bin/env python3
"""
Run the local client-promotion pipeline in one command:
1. rewrite and validate a Jasper export ZIP for all mapped target orgs
2. archive the original export ZIP only after rewrite succeeds
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from typing import List, Tuple


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run rewrite, validation, and archive for Jaspersoft client packages."
    )
    parser.add_argument(
        "--source-zip",
        required=True,
        help="Path to the source Jasper export ZIP.",
    )
    parser.add_argument(
        "--mapping",
        required=True,
        help="CSV file with rows target_org,target_datasource.",
    )
    parser.add_argument(
        "--src-org",
        required=True,
        help="Source organization name in the package.",
    )
    parser.add_argument(
        "--src-ds",
        required=True,
        help="Source datasource name in the package.",
    )
    parser.add_argument(
        "--outdir",
        default="prepared_imports",
        help="Directory where import-ready ZIPs should be written.",
    )
    parser.add_argument(
        "--datasource-export-dir",
        help=(
            "Optional directory containing one datasource export ZIP or folder "
            "per target. When provided, the target datasource export is injected "
            "into each output package."
        ),
    )
    parser.add_argument(
        "--archive-dir",
        default="archive",
        help="Directory where the original source ZIP should be moved after success.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run rewrite validation and archive planning without moving the source ZIP.",
    )
    return parser.parse_args()


def read_mapping(path: str) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row_number, row in enumerate(reader, start=1):
            if not row or all(not cell.strip() for cell in row):
                continue
            target_org = row[0].strip()
            if not target_org:
                raise ValueError(f"Mapping row {row_number} is missing a target organization.")
            target_ds = row[1].strip() if len(row) > 1 and row[1].strip() else f"{target_org}_DS"
            entries.append((target_org, target_ds))
    if not entries:
        raise ValueError("Mapping file does not contain any target rows.")
    return entries


def run_command(command: List[str]) -> int:
    completed = subprocess.run(command, check=False)
    return completed.returncode


def build_rewrite_command(args: argparse.Namespace) -> List[str]:
    command = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "prepare_client_imports.py"),
        "--source-zip",
        args.source_zip,
        "--mapping",
        args.mapping,
        "--src-org",
        args.src_org,
        "--src-ds",
        args.src_ds,
        "--outdir",
        args.outdir,
    ]
    if args.datasource_export_dir:
        command.extend(["--datasource-export-dir", args.datasource_export_dir])
    if args.dry_run:
        command.append("--dry-run")
    return command


def build_archive_command(args: argparse.Namespace) -> List[str]:
    command = [
        sys.executable,
        os.path.join(os.path.dirname(__file__), "archive_processed_export.py"),
        "--source-zip",
        args.source_zip,
        "--archive-dir",
        args.archive_dir,
    ]
    if args.dry_run:
        command.append("--dry-run")
    return command


def ensure_outputs_exist(outdir: str, mapping_entries: List[Tuple[str, str]], dry_run: bool) -> None:
    if dry_run:
        return

    missing_outputs = []
    for target_org, _target_ds in mapping_entries:
        output_zip = os.path.join(outdir, f"{target_org}_import.zip")
        if not os.path.isfile(output_zip):
            missing_outputs.append(output_zip)

    if missing_outputs:
        raise FileNotFoundError(
            "Rewrite reported success but some output ZIPs are missing: "
            + ", ".join(missing_outputs)
        )


def main() -> int:
    args = parse_args()
    source_zip = os.path.abspath(args.source_zip)
    mapping = os.path.abspath(args.mapping)
    outdir = os.path.abspath(args.outdir)

    if not os.path.isfile(source_zip):
        print(f"ERROR: Source ZIP not found: {source_zip}")
        return 2
    if not os.path.isfile(mapping):
        print(f"ERROR: Mapping file not found: {mapping}")
        return 2

    try:
        mapping_entries = read_mapping(mapping)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    print("Step 1/2: rewrite and validate")
    rewrite_code = run_command(build_rewrite_command(args))
    if rewrite_code != 0:
        print("\nPipeline stopped. Source ZIP was not archived because rewrite/validation failed.")
        return rewrite_code

    try:
        ensure_outputs_exist(outdir, mapping_entries, args.dry_run)
    except FileNotFoundError as exc:
        print(f"\nPipeline stopped. {exc}")
        print("Source ZIP was not archived.")
        return 1

    print("\nStep 2/2: archive original export")
    archive_code = run_command(build_archive_command(args))
    if archive_code != 0:
        print("\nPipeline completed rewrite, but archive step failed.")
        return archive_code

    if args.dry_run:
        print("\nDry-run complete. No files were moved.")
    else:
        print("\nPipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
