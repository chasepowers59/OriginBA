#!/usr/bin/env python3
"""
Build a datasource-only Jaspersoft export folder for an environment profile.

The output is suitable for prepare_client_imports.py datasource overlay mode.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
import zipfile
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

ORG_ROOT_PARTS = (
    "resources",
    "organizations",
    "organization_1",
    "organizations",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a datasource export folder or ZIP for an environment profile."
    )
    parser.add_argument(
        "--environment",
        required=True,
        help="Environment profile ID (for example origin_demo).",
    )
    parser.add_argument(
        "--profiles",
        default=str(DEFAULT_PROFILES_PATH),
        help="Path to environment_profiles.json.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Output directory or .zip path for the datasource export.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace an existing output directory or ZIP.",
    )
    return parser.parse_args()


def datasource_folder_uri(profile: EnvironmentProfile) -> str:
    return f"/organizations/organization_1/organizations/{profile.target_org}/DataSource"


def datasource_xml(profile: EnvironmentProfile) -> str:
    ds = profile.datasource
    folder_uri = datasource_folder_uri(profile)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<jdbcDataSource exportedWithPermissions="true">
    <folder>{folder_uri}</folder>
    <name>{profile.target_ds}</name>
    <version>1</version>
    <label>{ds.label}</label>
    <description>{ds.description}</description>
    <creationDate>2026-05-20T00:00:00.000Z</creationDate>
    <updateDate>2026-05-20T00:00:00.000Z</updateDate>
    <driver>{ds.driver}</driver>
    <connectionUrl>{ds.connection_url}</connectionUrl>
    <connectionUser>{ds.connection_user}</connectionUser>
    <connectionPassword>{ds.connection_password}</connectionPassword>
</jdbcDataSource>
"""


def folder_xml(profile: EnvironmentProfile) -> str:
    parent_uri = f"/organizations/organization_1/organizations/{profile.target_org}"
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<folder exportedWithPermissions="true">
    <parent>{parent_uri}</parent>
    <name>DataSource</name>
    <label>DataSource</label>
    <creationDate>2026-05-20T00:00:00.000Z</creationDate>
    <updateDate>2026-05-20T00:00:00.000Z</updateDate>
    <permission>
        <permissionMask>32</permissionMask>
        <recipient recipientType="role">ROLE_USER</recipient>
    </permission>
    <permission>
        <permissionMask>32</permissionMask>
        <recipient recipientType="role">ROLE_DESIGNER</recipient>
    </permission>
</folder>
"""


def write_export_tree(root: Path, profile: EnvironmentProfile) -> None:
    datasource_dir = root.joinpath(*ORG_ROOT_PARTS, profile.target_org, "DataSource")
    datasource_dir.mkdir(parents=True, exist_ok=True)

    (datasource_dir / ".folder.xml").write_text(folder_xml(profile), encoding="utf-8")
    (datasource_dir / f"{profile.target_ds}.xml").write_text(
        datasource_xml(profile),
        encoding="utf-8",
    )


def zip_directory(root: Path, output_zip: Path) -> None:
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for current_root, dirs, files in os.walk(root):
            dirs.sort()
            files.sort()
            for filename in files:
                full_path = Path(current_root) / filename
                relative_path = full_path.relative_to(root)
                archive.write(full_path, relative_path.as_posix())


def main() -> int:
    args = parse_args()
    out_path = Path(args.out).resolve()

    try:
        profile = load_profile(args.environment, args.profiles)
    except ProfileError as exc:
        print(f"ERROR: {exc}")
        return 2

    if out_path.suffix.lower() == ".zip":
        if out_path.exists() and not args.force:
            print(f"ERROR: Output ZIP already exists: {out_path}")
            return 2
        build_root = out_path.with_suffix("")
        if build_root.exists():
            if args.force:
                shutil.rmtree(build_root)
            else:
                print(f"ERROR: Build directory already exists: {build_root}")
                return 2
        write_export_tree(build_root, profile)
        zip_directory(build_root, out_path)
        shutil.rmtree(build_root)
        print(f"Built datasource export ZIP: {out_path}")
        return 0

    if out_path.exists():
        if not args.force:
            print(f"ERROR: Output directory already exists: {out_path}")
            return 2
        shutil.rmtree(out_path)
    write_export_tree(out_path, profile)
    print(f"Built datasource export folder: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
