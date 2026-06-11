#!/usr/bin/env python3
"""
Prepare a Jaspersoft import ZIP for a non-client environment (for example origin_demo).

Environment promotions keep the source organization paths and rewrite only the
datasource alias/endpoints. Output ZIPs are named from the datasource stem
(for example Origin_DEMO_import.zip), not the client org name.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from promotion_environments import (  # noqa: E402
    DEFAULT_PROFILES_PATH,
    EnvironmentProfile,
    ProfileError,
    load_profile,
)

REPO_ROOT = SCRIPT_DIR.parents[1]
DEFAULT_STAGING = REPO_ROOT / "deploy" / "jaspersoft_environment_promotion"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build datasource overlay and prepare an environment import ZIP."
    )
    parser.add_argument(
        "--environment",
        required=True,
        help="Environment profile ID (for example origin_demo).",
    )
    parser.add_argument(
        "--source-zip",
        required=True,
        help="Path to the source Jasper export ZIP from Origin_DEV.",
    )
    parser.add_argument(
        "--profiles",
        default=str(DEFAULT_PROFILES_PATH),
        help="Path to environment_profiles.json.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_STAGING / "prepared_imports"),
        help="Directory where the import-ready ZIP should be written.",
    )
    parser.add_argument(
        "--datasource-export-dir",
        default=str(DEFAULT_STAGING / "incoming_datasources"),
        help="Directory containing generated or hand-exported datasource overlays.",
    )
    parser.add_argument(
        "--archive-dir",
        default=str(DEFAULT_STAGING / "archive"),
        help="Directory where the original source ZIP is moved after success.",
    )
    parser.add_argument(
        "--rebuild-datasource",
        action="store_true",
        help="Regenerate the target datasource export from environment_profiles.json.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and plan without writing output ZIPs or archiving.",
    )
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        help="Do not move the source ZIP to archive after a successful rewrite.",
    )
    return parser.parse_args()


def run_command(command: list[str]) -> int:
    completed = subprocess.run(command, check=False)
    return completed.returncode


def datasource_export_path(export_dir: Path, profile: EnvironmentProfile) -> Path:
    return export_dir / profile.target_ds


def build_datasource_command(args: argparse.Namespace, profile: EnvironmentProfile, export_path: Path) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "build_environment_datasource_export.py"),
        "--environment",
        profile.environment_id,
        "--profiles",
        args.profiles,
        "--out",
        str(export_path),
    ]
    if export_path.exists():
        command.append("--force")
    return command


def build_rewrite_command(
    args: argparse.Namespace,
    profile: EnvironmentProfile,
    mapping_path: Path,
) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "prepare_client_imports.py"),
        "--source-zip",
        os.path.abspath(args.source_zip),
        "--mapping",
        str(mapping_path),
        "--src-org",
        profile.src_org,
        "--src-ds",
        profile.src_ds,
        "--outdir",
        os.path.abspath(args.outdir),
        "--promotion-mode",
        "datasource",
    ]
    if not profile.skip_datasource_import:
        command.extend(
            ["--datasource-export-dir", os.path.abspath(args.datasource_export_dir)]
        )
    if profile.use_org_relative_uris:
        command.extend(["--repository-uri-style", "org_relative"])
    if profile.map_standard_offering_to_workstreams:
        command.append("--map-standard-offering-to-workstreams")
    if profile.import_module_folder_uri:
        command.extend(["--import-module-folder-uri", profile.import_module_folder_uri])
    elif profile.index_module_folder_uri:
        command.extend(["--import-module-folder-uri", profile.index_module_folder_uri])
    if profile.output_zip_stem:
        command.extend(["--output-stem", profile.output_zip_stem])
    if profile.skip_datasource_import:
        command.append("--skip-datasource-import")
    if profile.repository_layout == "tenant_root":
        command.extend(["--repository-layout", "tenant_root"])
        if profile.tenant_id:
            command.extend(["--tenant-id", profile.tenant_id])
    if not profile.import_into_existing_tenant:
        command.append("--no-import-into-existing-tenant")
    if profile.light_touch_tenant_root:
        command.append("--light-touch-tenant-root")
    if profile.use_canonical_index_encryption:
        command.append("--use-canonical-index-encryption")
    if args.dry_run:
        command.append("--dry-run")
    return command


def build_archive_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(SCRIPT_DIR / "archive_processed_export.py"),
        "--source-zip",
        os.path.abspath(args.source_zip),
        "--archive-dir",
        os.path.abspath(args.archive_dir),
    ]
    if args.dry_run:
        command.append("--dry-run")
    return command


def write_mapping_file(path: Path, profile: EnvironmentProfile) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{profile.target_org},{profile.target_ds}\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).resolve()
    outdir = Path(args.outdir).resolve()
    datasource_export_dir = Path(args.datasource_export_dir).resolve()
    output_zip = outdir / load_profile(args.environment, args.profiles).output_zip_name

    if not source_zip.is_file():
        print(f"ERROR: Source ZIP not found: {source_zip}")
        return 2

    try:
        profile = load_profile(args.environment, args.profiles)
    except ProfileError as exc:
        print(f"ERROR: {exc}")
        return 2

    datasource_export_dir.mkdir(parents=True, exist_ok=True)
    outdir.mkdir(parents=True, exist_ok=True)
    Path(args.archive_dir).mkdir(parents=True, exist_ok=True)

    export_path = datasource_export_path(datasource_export_dir, profile)
    if profile.skip_datasource_import:
        print("Step 1/3: skip datasource export (Origin_DEMO_DS must already exist on demo server)")
    elif args.rebuild_datasource or not export_path.exists():
        print("Step 1/3: build datasource export")
        build_code = run_command(build_datasource_command(args, profile, export_path))
        if build_code != 0:
            print("\nPipeline stopped. Datasource export build failed.")
            return build_code
    else:
        print(f"Step 1/3: reuse existing datasource export at {export_path}")

    mapping_path = outdir / "_tmp" / f"{profile.environment_id}_mapping.csv"
    write_mapping_file(mapping_path, profile)

    print("Step 2/3: rewrite package (datasource-only)")
    rewrite_code = run_command(build_rewrite_command(args, profile, mapping_path))
    mapping_path.unlink(missing_ok=True)
    if rewrite_code != 0:
        print("\nPipeline stopped. Source ZIP was not archived because rewrite/validation failed.")
        return rewrite_code

    if not args.dry_run and not output_zip.is_file():
        print(f"\nPipeline stopped. Expected output ZIP is missing: {output_zip}")
        print("Source ZIP was not archived.")
        return 1

    if args.skip_archive:
        print("Step 3/3: skip archive (source ZIP retained)")
    else:
        print("Step 3/3: archive original export")
        archive_code = run_command(build_archive_command(args))
        if archive_code != 0:
            print("\nPipeline completed rewrite, but archive step failed.")
            return archive_code

    if args.dry_run:
        print("\nDry-run complete. No import ZIP or archive changes were written.")
    else:
        print("\nPipeline complete.")
        print(f"output zip: {output_zip}")
        print(f"target org: {profile.target_org}")
        print(f"target datasource: {profile.target_ds}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
