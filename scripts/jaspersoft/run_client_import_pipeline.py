#!/usr/bin/env python3
"""
Run the local client-promotion pipeline in one command:
1. rewrite and validate a Jasper export ZIP for all mapped target orgs
2. archive the original export ZIP only after rewrite succeeds

Default packaging matches validated Origin_STAGE / Origin_DEV promotion:
tenant-root layout, light-touch repackage, import inside each client tenant.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_PROMOTION = REPO_ROOT / "deploy" / "jaspersoft_client_promotion"
DEFAULT_CLIENT_DS = REPO_ROOT / "deploy" / "jaspersoft_datasources" / "clients"
STANDARD_OFFERING_FOLDER = "/SmartCity/Report/Standard_Offering"


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
        default=str(DEFAULT_PROMOTION / "client_org_mapping.csv"),
        help="CSV file with rows target_org,target_datasource.",
    )
    parser.add_argument(
        "--src-org",
        default="Origin_DEV",
        help="Source organization name in the package.",
    )
    parser.add_argument(
        "--src-ds",
        default="Origin_DEV_DS",
        help="Source datasource name in the package.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_PROMOTION / "prepared_imports"),
        help="Directory where import-ready ZIPs should be written.",
    )
    parser.add_argument(
        "--datasource-export-dir",
        default=str(DEFAULT_CLIENT_DS),
        help="Directory with one datasource export folder or ZIP per client.",
    )
    parser.add_argument(
        "--archive-dir",
        default=str(DEFAULT_PROMOTION / "archive"),
        help="Directory where the original source ZIP should be moved after success.",
    )
    parser.add_argument(
        "--import-module-folder-uri",
        default=STANDARD_OFFERING_FOLDER,
        help="Repository folder URI imported by index.xml.",
    )
    parser.add_argument(
        "--output-stem",
        help="Override output ZIP stem for all targets (default: <org>_Standard_Offering).",
    )
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="Do not move the source ZIP to archive after a successful rewrite.",
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


def output_stem_for_target(
    target_org: str,
    target_ds: str,
    *,
    output_stem: str | None,
    import_module_folder_uri: str,
) -> str:
    if output_stem:
        return output_stem
    if import_module_folder_uri.endswith("Standard_Offering"):
        return f"{target_org}_Standard_Offering"
    return target_org


def run_command(command: List[str]) -> int:
    completed = subprocess.run(command, check=False)
    return completed.returncode


def build_rewrite_command(args: argparse.Namespace) -> List[str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "prepare_client_imports.py"),
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
        "--promotion-mode",
        "client",
        "--repository-layout",
        "tenant_root",
        "--repository-uri-style",
        "org_relative",
        "--import-module-folder-uri",
        args.import_module_folder_uri,
        "--light-touch-tenant-root",
        "--import-into-existing-tenant",
        "--use-canonical-index-encryption",
    ]
    if args.datasource_export_dir:
        command.extend(["--datasource-export-dir", args.datasource_export_dir])
    if args.output_stem:
        command.extend(["--output-stem", args.output_stem])
    if args.dry_run:
        command.append("--dry-run")
    return command


def build_archive_command(args: argparse.Namespace) -> None:
    pass


def ensure_outputs_exist(
    outdir: str,
    mapping_entries: List[Tuple[str, str]],
    *,
    output_stem: str | None,
    import_module_folder_uri: str,
    dry_run: bool,
) -> None:
    if dry_run:
        return

    missing_outputs = []
    for target_org, target_ds in mapping_entries:
        stem = output_stem_for_target(
            target_org,
            target_ds,
            output_stem=output_stem,
            import_module_folder_uri=import_module_folder_uri,
        )
        output_zip = os.path.join(outdir, f"{stem}_import.zip")
        if not os.path.isfile(output_zip):
            missing_outputs.append(output_zip)

    if missing_outputs:
        raise FileNotFoundError(
            "Rewrite reported success but some output ZIPs are missing: "
            + ", ".join(missing_outputs)
        )


def main() -> int:
    args = parse_args()
    args.source_zip = os.path.abspath(args.source_zip)
    args.mapping = os.path.abspath(args.mapping)
    args.outdir = os.path.abspath(args.outdir)
    if args.datasource_export_dir:
        args.datasource_export_dir = os.path.abspath(args.datasource_export_dir)
    args.archive_dir = os.path.abspath(args.archive_dir)

    if not os.path.isfile(args.source_zip):
        print(f"ERROR: Source ZIP not found: {args.source_zip}")
        return 2
    if not os.path.isfile(args.mapping):
        print(f"ERROR: Mapping file not found: {args.mapping}")
        return 2
    if args.datasource_export_dir and not os.path.isdir(args.datasource_export_dir):
        print(f"ERROR: Datasource export directory not found: {args.datasource_export_dir}")
        return 2

    try:
        mapping_entries = read_mapping(args.mapping)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    print("Step 1/2: rewrite and validate (tenant-root light-touch + client datasource overlay)")
    rewrite_code = run_command(build_rewrite_command(args))
    if rewrite_code != 0:
        print("\nPipeline stopped. Source ZIP was not archived because rewrite/validation failed.")
        return rewrite_code

    try:
        ensure_outputs_exist(
            args.outdir,
            mapping_entries,
            output_stem=args.output_stem,
            import_module_folder_uri=args.import_module_folder_uri,
            dry_run=args.dry_run,
        )
    except FileNotFoundError as exc:
        print(f"\nPipeline stopped. {exc}")
        print("Source ZIP was not archived.")
        return 1

    if args.skip_archive or args.dry_run:
        if args.dry_run:
            print("\nDry-run complete. No files were moved.")
        else:
            print("\nPipeline complete (archive skipped).")
        return 0

    print("\nStep 2/2: archive original export")
    archive_code = run_command(
        [
            sys.executable,
            str(SCRIPT_DIR / "archive_processed_export.py"),
            "--source-zip",
            args.source_zip,
            "--archive-dir",
            args.archive_dir,
        ]
    )
    if archive_code != 0:
        print("\nPipeline completed rewrite, but archive step failed.")
        return archive_code

    print("\nPipeline complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
