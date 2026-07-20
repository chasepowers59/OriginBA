#!/usr/bin/env python3
"""
Build Standard Offering import ZIPs for all SmartCity clients.

Uses tenant-root light-touch promotion (import inside each client tenant) and
injects each client's canonical JDBC datasource from deploy/jaspersoft_datasources/clients/.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
CLIENT_PROMOTION = REPO_ROOT / "deploy" / "jaspersoft_client_promotion"
CLIENT_DS_DIR = REPO_ROOT / "deploy" / "jaspersoft_datasources" / "clients"
PREPARED_DIR = CLIENT_PROMOTION / "prepared_imports"
MAPPING = CLIENT_PROMOTION / "client_org_mapping.csv"
CLIENT_PIPELINE = SCRIPT_DIR / "run_client_import_pipeline.py"
VERIFY_PREPARED = SCRIPT_DIR / "verify_prepared_import.py"
VERIFY_TENANT_SO = SCRIPT_DIR / "verify_standard_offering_tenant_import.py"

DEFAULT_SOURCE_ZIP = Path("/Users/chase/Downloads/standard offering.zip")
IMPORT_FOLDER = "/SmartCity/Report/Standard_Offering"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare Standard Offering import ZIPs for all mapped SmartCity clients."
    )
    parser.add_argument(
        "--source-zip",
        default=str(DEFAULT_SOURCE_ZIP),
        help="Tenant-root Standard Offering export ZIP from Origin_DEV.",
    )
    parser.add_argument(
        "--clients",
        nargs="*",
        help="Optional subset of client org IDs (for example Ellensburg CityCorp).",
    )
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="Do not move the source ZIP to archive after success.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate rewrite without writing output ZIPs.",
    )
    return parser.parse_args()


def run(cmd: list[str], label: str) -> None:
    print(f"\n[{label}] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def read_datasource_index_metadata(target_ds: str) -> tuple[str | None, str | None]:
    ds_index = CLIENT_DS_DIR / target_ds / "index.xml"
    if not ds_index.is_file():
        return None, None
    import xml.etree.ElementTree as ET

    root = ET.fromstring(ds_index.read_text(encoding="utf-8"))
    keyalias = None
    encrypted = None
    for prop in root.findall("property"):
        name = prop.get("name")
        value = (prop.get("value") or "").strip() or None
        if name == "keyalias":
            keyalias = value
        elif name == "encrypted":
            encrypted = value
    return keyalias, encrypted


def read_mapping(path: Path) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        org, ds = [part.strip() for part in line.split(",", 1)]
        rows.append((org, ds))
    return rows


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).expanduser().resolve()

    if not MAPPING.is_file():
        print(f"Missing mapping file: {MAPPING}", file=sys.stderr)
        return 1
    if not CLIENT_DS_DIR.is_dir():
        print(f"Missing client datasource directory: {CLIENT_DS_DIR}", file=sys.stderr)
        return 1
    if not source_zip.is_file():
        print(f"Source ZIP not found: {source_zip}", file=sys.stderr)
        return 1

    mapping = read_mapping(MAPPING)
    if args.clients:
        allowed = {name.strip() for name in args.clients}
        mapping = [(org, ds) for org, ds in mapping if org in allowed]
        if not mapping:
            print(f"No mapping rows matched --clients {args.clients}", file=sys.stderr)
            return 1

    for _org, target_ds in mapping:
        ds_dir = CLIENT_DS_DIR / target_ds
        if not ds_dir.is_dir():
            print(f"Missing canonical client datasource export: {ds_dir}", file=sys.stderr)
            return 1

    PREPARED_DIR.mkdir(parents=True, exist_ok=True)

    pipeline_cmd = [
        sys.executable,
        str(CLIENT_PIPELINE),
        "--source-zip",
        str(source_zip),
        "--mapping",
        str(MAPPING),
        "--src-org",
        "Origin_DEV",
        "--src-ds",
        "Origin_DEV_DS",
        "--outdir",
        str(PREPARED_DIR),
        "--datasource-export-dir",
        str(CLIENT_DS_DIR),
        "--archive-dir",
        str(CLIENT_PROMOTION / "archive"),
    ]
    if args.skip_archive:
        pipeline_cmd.append("--skip-archive")
    if args.dry_run:
        pipeline_cmd.append("--dry-run")
    if args.clients:
        # run_client_import_pipeline processes full mapping; filter by rebuilding mapping temp
        filtered_mapping = PREPARED_DIR / "_tmp" / "client_subset_mapping.csv"
        filtered_mapping.parent.mkdir(parents=True, exist_ok=True)
        filtered_mapping.write_text(
            "\n".join(f"{org},{ds}" for org, ds in mapping) + "\n",
            encoding="utf-8",
        )
        pipeline_cmd[pipeline_cmd.index(str(MAPPING))] = str(filtered_mapping)

    run(pipeline_cmd, "client-pipeline")

    if args.dry_run:
        return 0

    for target_org, target_ds in mapping:
        output_zip = PREPARED_DIR / f"{target_org}_Standard_Offering_import.zip"
        if not output_zip.is_file():
            print(f"Expected output missing: {output_zip}", file=sys.stderr)
            return 1

        run(
            [
                sys.executable,
                str(VERIFY_PREPARED),
                "--zip",
                str(output_zip),
                "--target-org",
                target_org,
                "--target-ds",
                target_ds,
                "--source-ds",
                "Origin_DEV_DS",
                "--source-org",
                "Origin_DEV",
                "--expect-datasource-overlay",
                "--repository-layout",
                "tenant_root",
                "--repository-uri-style",
                "org_relative",
                "--import-module-folder-uri",
                IMPORT_FOLDER,
            ],
            f"verify-{target_org}",
        )

        verify_tenant_cmd = [
            sys.executable,
            str(VERIFY_TENANT_SO),
            "--zip",
            str(output_zip),
            "--source-zip",
            str(source_zip),
            "--target-ds",
            target_ds,
            "--forbid-source-ds",
            "Origin_DEV_DS",
            "--output-json",
            str(PREPARED_DIR / f"{target_org}_Standard_Offering_verification.json"),
        ]
        expected_keyalias, expected_encrypted = read_datasource_index_metadata(target_ds)
        if expected_keyalias:
            verify_tenant_cmd.extend(["--expected-keyalias", expected_keyalias])
        if expected_encrypted:
            verify_tenant_cmd.extend(["--expected-encrypted", expected_encrypted])
        run(verify_tenant_cmd, f"verify-so-{target_org}")

    print("\nClient Standard Offering pipeline complete.")
    for target_org, _target_ds in mapping:
        print(f"  {PREPARED_DIR / f'{target_org}_Standard_Offering_import.zip'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
