#!/usr/bin/env python3
"""Import a Jaspersoft datasource export ZIP into the canonical internal store."""

from __future__ import annotations

import argparse
import shutil
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_ROOT = REPO_ROOT / "deploy" / "jaspersoft_datasources" / "canonical"
ALLOWED_ALIASES = {"Origin_STAGE_DS", "Origin_DEV_DS", "Training_DB", "Origin_INT_DEV_DS"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Store a canonical internal datasource export.")
    parser.add_argument("--alias", required=True, choices=sorted(ALLOWED_ALIASES))
    parser.add_argument("--zip", required=True, help="Path to the Jaspersoft datasource export ZIP.")
    parser.add_argument("--force", action="store_true", help="Replace an existing canonical export.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    zip_path = Path(args.zip).expanduser().resolve()
    if not zip_path.is_file():
        print(f"ZIP not found: {zip_path}")
        return 1

    target_dir = CANONICAL_ROOT / args.alias
    backup_zip = CANONICAL_ROOT / f"{args.alias}_export.zip"

    if target_dir.exists() and not args.force:
        print(f"Canonical export already exists: {target_dir}")
        print("Re-run with --force to replace.")
        return 1

    if target_dir.exists():
        shutil.rmtree(target_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(zip_path) as archive:
        archive.extractall(target_dir)

    datasource_xml = target_dir / "resources" / "DataSource" / f"{args.alias}.xml"
    if not datasource_xml.is_file():
        print(f"Invalid datasource export — missing {datasource_xml}")
        return 1

    shutil.copy2(zip_path, backup_zip)
    print(f"Stored canonical datasource: {target_dir}")
    print(f"Backup ZIP: {backup_zip}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
