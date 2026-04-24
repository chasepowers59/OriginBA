#!/usr/bin/env python3
"""
Archive an original Jasper export ZIP after a successful client-package rewrite.
"""

from __future__ import annotations

import argparse
import os
import shutil
from datetime import datetime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Archive a source Jasper export ZIP after package preparation."
    )
    parser.add_argument(
        "--source-zip",
        required=True,
        help="Path to the original export ZIP to archive.",
    )
    parser.add_argument(
        "--archive-dir",
        default="archive",
        help="Directory where the original export ZIP should be moved.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show the destination path without moving the file.",
    )
    return parser.parse_args()


def choose_destination(source_zip: str, archive_dir: str) -> str:
    base_name = os.path.basename(source_zip)
    destination = os.path.join(archive_dir, base_name)
    if not os.path.exists(destination):
        return destination

    stem, extension = os.path.splitext(base_name)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join(archive_dir, f"{stem}_{timestamp}{extension}")


def main() -> int:
    args = parse_args()
    source_zip = os.path.abspath(args.source_zip)
    archive_dir = os.path.abspath(args.archive_dir)

    if not os.path.isfile(source_zip):
        print(f"ERROR: Source ZIP not found: {source_zip}")
        return 2

    os.makedirs(archive_dir, exist_ok=True)
    destination = choose_destination(source_zip, archive_dir)

    if args.dry_run:
        print(f"Would move: {source_zip}")
        print(f"To: {destination}")
        return 0

    shutil.move(source_zip, destination)
    print(f"Moved: {source_zip}")
    print(f"To: {destination}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
