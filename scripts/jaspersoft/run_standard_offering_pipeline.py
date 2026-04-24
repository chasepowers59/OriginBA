#!/usr/bin/env python3
"""
Build and verify the curated Jaspersoft Standard Offering package in one command.

This is a thin wrapper around:
- build_standard_offering_package.py
- verify_standard_offering_package.py
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
DEFAULT_SOURCE_ZIP = Path("/Users/chase/Downloads/Workstream folder.zip")
DEFAULT_OUTDIR = REPO_ROOT / "deploy" / "jaspersoft_standard_offering"
DEFAULT_PACKAGE_ZIP = DEFAULT_OUTDIR / "Standard_Offering_import.zip"
DEFAULT_VERIFY_JSON = DEFAULT_OUTDIR / "standard_offering_verification.json"
BUILD_SCRIPT = SCRIPT_DIR / "build_standard_offering_package.py"
VERIFY_SCRIPT = SCRIPT_DIR / "verify_standard_offering_package.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build and verify the curated Standard Offering import package."
    )
    parser.add_argument(
        "--source-zip",
        default=str(DEFAULT_SOURCE_ZIP),
        help="Path to the exported Workstreams ZIP.",
    )
    parser.add_argument(
        "--outdir",
        default=str(DEFAULT_OUTDIR),
        help="Output directory for the rebuilt package, audit, and verification JSON.",
    )
    return parser.parse_args()


def run_step(cmd: list[str], label: str) -> None:
    print(f"[{label}] {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    package_zip = outdir / DEFAULT_PACKAGE_ZIP.name
    verify_json = outdir / DEFAULT_VERIFY_JSON.name

    if not source_zip.exists():
        print(f"Source ZIP not found: {source_zip}", file=sys.stderr)
        return 1

    run_step(
        [
            sys.executable,
            str(BUILD_SCRIPT),
            "--source-zip",
            str(source_zip),
            "--outdir",
            str(outdir),
        ],
        "build",
    )
    run_step(
        [
            sys.executable,
            str(VERIFY_SCRIPT),
            "--zip",
            str(package_zip),
            "--output-json",
            str(verify_json),
        ],
        "verify",
    )

    print("")
    print("Pipeline complete.")
    print(f"Package: {package_zip}")
    print(f"Verification: {verify_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
