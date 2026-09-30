#!/usr/bin/env python3
"""Build Newark REP8 client-tenant report import ZIP."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/jaspersoft/build_client_tenant_report_import.py"
OUT_DIR = REPO_ROOT / "domains/manual_imports/newark_rep8_aged_balance_report"
SOURCE_ZIP = Path("/Users/chase/Downloads/aged debt newark.zip")
SQL_PATCH = REPO_ROOT / "sql/clients/newark/rep8_aged_balance/rep8_vw_jrxml_query.sql"

IMPORT_FOLDER = "/SmartCity/Report/Workstreams/Debt_Management"
JRXML_REL = (
    "resources/SmartCity/Report/Workstreams/Debt_Management/"
    "REP8_Aged_Balance_files/main_jrxml.data"
)
REPORT_XML = (
    "resources/SmartCity/Report/Workstreams/Debt_Management/REP8_Aged_Balance.xml"
)


def main() -> int:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--source-zip",
        str(SOURCE_ZIP),
        "--client-org",
        "Newark1",
        "--target-ds",
        "Newark1_DS",
        "--import-folder-uri",
        IMPORT_FOLDER,
        "--keep-prefix",
        "resources/DataSource/",
        "--keep-prefix",
        "resources/SmartCity/.folder.xml",
        "--keep-prefix",
        "resources/SmartCity/Report/.folder.xml",
        "--keep-prefix",
        "resources/SmartCity/Report/Workstreams/",
        "--keep-prefix",
        "resources/public/",
        "--staging-dir",
        str(OUT_DIR / "_import_client_so"),
        "--output-zip",
        str(OUT_DIR / "REP8_Aged_Balance_staging_client_import.zip"),
        "--patch-jrxml",
        JRXML_REL,
        "--patch-subdataset",
        "REP8_VW",
        "--patch-sql-file",
        str(SQL_PATCH),
        "--report-unit-xml",
        REPORT_XML,
        "--include-report-date",
    ]
    return subprocess.call(cmd)


if __name__ == "__main__":
    raise SystemExit(main())
