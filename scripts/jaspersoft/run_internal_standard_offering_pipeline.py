#!/usr/bin/env python3
"""
Build and prepare Standard Offering import ZIPs for internal environments.

Produces two tenant-root packages:
- standard_offering_Origin_STAGE_import.zip  (Training_DB → ptrndb snapshots)
- standard_offering_Origin_DEV_import.zip    (Origin_DEV_DS)

Each package rewrites Origin_DEV_DS references to the target alias and injects
the canonical datasource export — never the old datasource from the source ZIP.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
BUILD_SCRIPT = SCRIPT_DIR / "build_standard_offering_package.py"
VERIFY_BASE_SCRIPT = SCRIPT_DIR / "verify_standard_offering_package.py"
VERIFY_TENANT_SCRIPT = SCRIPT_DIR / "verify_standard_offering_tenant_import.py"
ENV_PIPELINE = SCRIPT_DIR / "run_environment_import_pipeline.py"
VERIFY_PREPARED = SCRIPT_DIR / "verify_prepared_import.py"

DEFAULT_SOURCE_ZIP = Path("/Users/chase/Downloads/standard offering.zip")
TENANT_EXPORT_MARKER = "resources/SmartCity/Report/Standard_Offering/"
BASE_OUTDIR = REPO_ROOT / "deploy" / "jaspersoft_standard_offering"
CANONICAL_DS_DIR = REPO_ROOT / "deploy" / "jaspersoft_datasources" / "canonical"
PREPARED_DIR = REPO_ROOT / "deploy" / "jaspersoft_environment_promotion" / "prepared_imports"
INTERNAL_ENVIRONMENTS = ("origin_stage", "origin_dev")

# Loaded from environment_profiles.json for verify_prepared_import flags.
INTERNAL_VERIFY = {
    "origin_stage": {
        "target_ds": "Training_DB",
        "tenant_id": None,  # content-only import; omit rootTenantId
        "expected_keyalias": "01b7ed96-d541-491b-a036-b0cd122b0c45",
        "import_module_folder_uri": "/SmartCity/Report/Standard_Offering",
        "forbid_datasource_aliases": ["Origin_DEV_DS", "Origin_STAGE_DS"],
    },
    "origin_dev": {
        "target_ds": "Origin_DEV_DS",
        "tenant_id": None,
        "expected_keyalias": "01b7ed96-d541-491b-a036-b0cd122b0c45",
        "import_module_folder_uri": "/SmartCity/Report/Standard_Offering",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build Standard Offering packages for Origin_STAGE and Origin_DEV."
    )
    parser.add_argument(
        "--source-zip",
        default=str(DEFAULT_SOURCE_ZIP),
        help="Tenant-root Standard Offering export ZIP (preferred) or legacy Workstreams ZIP.",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Reuse existing deploy/jaspersoft_standard_offering/Standard_Offering_import.zip.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate datasource overlays without writing prepared import ZIPs.",
    )
    return parser.parse_args()


def run(cmd: list[str], label: str) -> None:
    print(f"\n[{label}] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def is_tenant_standard_offering_export(zip_path: Path) -> bool:
    if not zip_path.is_file():
        return False
    import zipfile

    with zipfile.ZipFile(zip_path) as archive:
        return any(name.startswith(TENANT_EXPORT_MARKER) for name in archive.namelist())


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).expanduser().resolve()
    base_package = BASE_OUTDIR / "Standard_Offering_import.zip"

    for alias in ("Origin_STAGE_DS", "Origin_DEV_DS", "Training_DB"):
        canonical = CANONICAL_DS_DIR / alias
        if not canonical.is_dir():
            print(f"Missing canonical datasource export: {canonical}", file=sys.stderr)
            return 1

    tenant_export = is_tenant_standard_offering_export(source_zip)
    package_source = source_zip if tenant_export else base_package

    if tenant_export:
        print(f"Using tenant-root Standard Offering export: {source_zip}")
    elif not args.skip_build:
        if not source_zip.is_file():
            print(f"Source ZIP not found: {source_zip}", file=sys.stderr)
            print("Provide --source-zip or --skip-build if the base package already exists.")
            return 1
        run(
            [
                sys.executable,
                str(BUILD_SCRIPT),
                "--source-zip",
                str(source_zip),
                "--outdir",
                str(BASE_OUTDIR),
            ],
            "build-base",
        )
        run(
            [
                sys.executable,
                str(VERIFY_BASE_SCRIPT),
                "--zip",
                str(base_package),
                "--output-json",
                str(BASE_OUTDIR / "standard_offering_verification.json"),
            ],
            "verify-base",
        )
        package_source = base_package
    elif not base_package.is_file():
        print(f"Base package missing: {base_package}", file=sys.stderr)
        return 1

    PREPARED_DIR.mkdir(parents=True, exist_ok=True)

    for environment in INTERNAL_ENVIRONMENTS:
        env_cmd = [
            sys.executable,
            str(ENV_PIPELINE),
            "--environment",
            environment,
            "--source-zip",
            str(package_source),
            "--outdir",
            str(PREPARED_DIR),
            "--datasource-export-dir",
            str(CANONICAL_DS_DIR),
            "--skip-archive",
        ]
        if args.dry_run:
            env_cmd.append("--dry-run")
        run(env_cmd, environment)

        if args.dry_run:
            continue

        verify_cfg = INTERNAL_VERIFY[environment]
        output_stem = "standard_offering_Origin_STAGE" if environment == "origin_stage" else "standard_offering_Origin_DEV"
        output_zip = PREPARED_DIR / f"{output_stem}_import.zip"

        if not output_zip.is_file():
            print(f"Expected output missing: {output_zip}", file=sys.stderr)
            return 1

        verify_cmd = [
            sys.executable,
            str(VERIFY_PREPARED),
            "--zip",
            str(output_zip),
            "--target-org",
            "Origin_DEV",
            "--target-ds",
            verify_cfg["target_ds"],
            "--expect-datasource-overlay",
            "--repository-layout",
            "tenant_root",
            "--repository-uri-style",
            "org_relative",
            "--import-module-folder-uri",
            verify_cfg["import_module_folder_uri"],
        ]
        if verify_cfg.get("forbid_datasource_aliases"):
            for forbidden_ds in verify_cfg["forbid_datasource_aliases"]:
                if forbidden_ds != verify_cfg["target_ds"]:
                    verify_cmd.extend(["--forbid-source-ds", forbidden_ds])
        elif verify_cfg["target_ds"] != "Origin_DEV_DS":
            verify_cmd.extend(["--source-ds", "Origin_DEV_DS"])
        if verify_cfg["tenant_id"]:
            verify_cmd.extend(["--tenant-id", verify_cfg["tenant_id"]])
        run(verify_cmd, f"verify-{environment}")

        tenant_verify = [
            sys.executable,
            str(VERIFY_TENANT_SCRIPT),
            "--zip",
            str(output_zip),
            "--target-ds",
            verify_cfg["target_ds"],
            "--source-zip",
            str(package_source),
            "--output-json",
            str(PREPARED_DIR / f"{output_stem}_verification.json"),
        ]
        if verify_cfg.get("forbid_datasource_aliases"):
            for forbidden_ds in verify_cfg["forbid_datasource_aliases"]:
                tenant_verify.extend(["--forbid-source-ds", forbidden_ds])
        elif verify_cfg["target_ds"] != "Origin_DEV_DS":
            tenant_verify.extend(["--forbid-source-ds", "Origin_DEV_DS"])
        if verify_cfg["tenant_id"]:
            tenant_verify.extend(["--tenant-id", verify_cfg["tenant_id"]])
        if verify_cfg.get("expected_keyalias"):
            tenant_verify.extend(["--expected-keyalias", verify_cfg["expected_keyalias"]])
        run(tenant_verify, f"verify-offering-{environment}")

    print("\nInternal Standard Offering pipeline complete.")
    if not args.dry_run:
        print(f"Stage package: {PREPARED_DIR / 'standard_offering_Origin_STAGE_import.zip'}")
        print(f"Dev package:   {PREPARED_DIR / 'standard_offering_Origin_DEV_import.zip'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
