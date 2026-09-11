#!/usr/bin/env python3
"""Build a client-tenant JRS report import ZIP (Standard Offering layout).

Validated on Newark REP8 (2026-09-02). Import from inside the client tenant.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from tenant_root_layout import (  # noqa: E402
    finalize_tenant_import_index,
    merge_bundled_public_dashboard_template,
    read_export_index_metadata,
    rewrite_datasource_for_tenant_root,
)

PUBLIC_TEMPLATE_URI = "/public/templates/actual_size.820.jrxml"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", required=True, type=Path)
    parser.add_argument("--client-org", required=True, help="Target org id, e.g. Newark1")
    parser.add_argument("--target-ds", required=True, help="Datasource alias, e.g. Newark1_DS")
    parser.add_argument(
        "--import-folder-uri",
        required=True,
        help="Repository folder URI, e.g. /SmartCity/Report/Workstreams/Debt_Management",
    )
    parser.add_argument(
        "--keep-prefix",
        action="append",
        required=True,
        help="Zip resource prefix to retain (repeatable), e.g. resources/SmartCity/Report/Workstreams/",
    )
    parser.add_argument(
        "--datasource-export-dir",
        type=Path,
        default=REPO_ROOT / "deploy/jaspersoft_datasources/clients",
        help="Root containing per-client datasource export folders",
    )
    parser.add_argument("--staging-dir", required=True, type=Path)
    parser.add_argument("--output-zip", required=True, type=Path)
    parser.add_argument(
        "--patch-jrxml",
        type=Path,
        help="Optional main_jrxml.data path relative to staging root to patch",
    )
    parser.add_argument(
        "--patch-subdataset",
        default="REP8_VW",
        help="Subdataset name whose <queryString> will be replaced",
    )
    parser.add_argument(
        "--patch-sql-file",
        type=Path,
        help="SQL file contents replace subdataset query (no CDATA wrapper)",
    )
    parser.add_argument(
        "--report-unit-xml",
        type=Path,
        help="Report unit XML relative to staging; validated for import-folder-uri",
    )
    parser.add_argument(
        "--include-report-date",
        action="store_true",
        help="Keep SmartCity/Admin/Parameters/Report_Date from source export",
    )
    parser.add_argument(
        "--skip-public-template",
        action="store_true",
        help="Omit public dashboard template (not recommended for client imports)",
    )
    return parser.parse_args()


def patch_subdataset_query(
    jrxml_path: Path,
    subdataset_name: str,
    query_sql: str,
) -> None:
    text = jrxml_path.read_text(encoding="utf-8")
    marker_start = f'\t<subDataset name="{subdataset_name}"'
    marker_end = "\t</subDataset>"
    start = text.index(marker_start)
    sub_end = text.index(marker_end, start)
    block = text[start:sub_end]
    q_start = block.index('\t\t<queryString language="SQL">')
    q_end = block.index("\t\t</queryString>", q_start) + len("\t\t</queryString>")
    new_block = (
        block[:q_start]
        + f'\t\t<queryString language="SQL">\n\t\t\t<![CDATA[{query_sql.strip()}]]>\n\t\t</queryString>'
        + block[q_end:]
    )
    jrxml_path.write_text(text[:start] + new_block + text[sub_end:], encoding="utf-8")


def patch_report_date_input_control(work_root: Path) -> None:
    """Expose Report_Date on the run prompt so users can pick the as-of date."""
    ic_path = work_root / "resources/SmartCity/Admin/Parameters/Report_Date.xml"
    if not ic_path.is_file():
        raise SystemExit(f"Missing Report_Date input control: {ic_path}")
    text = ic_path.read_text(encoding="utf-8")
    replacements = [
        ("<visible>false</visible>", "<visible>true</visible>"),
        ("<mandatory>false</mandatory>", "<mandatory>true</mandatory>"),
        ("<label>Report_Date</label>", "<label>Report Date</label>"),
    ]
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"patch_report_date_input_control: pattern not found: {old}")
        text = text.replace(old, new, 1)
    ic_path.write_text(text, encoding="utf-8")


def patch_report_date_null_safe(jrxml_path: Path) -> None:
    """Avoid NPE when Report_Date input control is hidden and unset."""
    text = jrxml_path.read_text(encoding="utf-8")
    replacements = [
        (
            '\t<parameter name="Report_Date" class="java.sql.Date"/>\n\t<queryString language="SQL">\n\t\t<![CDATA[SELECT 1 FROM CISADM.CI_ACCT WHERE ROWNUM=1]]>',
            '\t<parameter name="Report_Date" class="java.sql.Date">\n\t\t<defaultValueExpression><![CDATA[new java.sql.Date(System.currentTimeMillis())]]></defaultValueExpression>\n\t</parameter>\n\t<queryString language="SQL">\n\t\t<![CDATA[SELECT 1 FROM CISADM.CI_ACCT WHERE ROWNUM=1]]>',
        ),
        (
            '"AGED BALANCE AS OF " + new SimpleDateFormat("yyyy-MM-dd").format($P{Report_Date})',
            '"AGED BALANCE AS OF " + new SimpleDateFormat("yyyy-MM-dd").format($P{Report_Date} != null ? $P{Report_Date} : new java.util.Date())',
        ),
        (
            "<datasetParameterExpression><![CDATA[$P{Report_Date}]]></datasetParameterExpression>",
            "<datasetParameterExpression><![CDATA[$P{Report_Date} != null ? $P{Report_Date} : new java.sql.Date(System.currentTimeMillis())]]></datasetParameterExpression>",
        ),
    ]
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"patch_report_date_null_safe: pattern not found in {jrxml_path}")
        text = text.replace(old, new, 1)
    jrxml_path.write_text(text, encoding="utf-8")


def validate_jrxml_xml(jrxml_path: Path) -> None:
    import xml.etree.ElementTree as ET

    try:
        ET.parse(jrxml_path)
    except ET.ParseError as exc:
        raise SystemExit(f"Invalid JRXML XML after patch ({jrxml_path}): {exc}") from exc


def extract_source(work_root: Path, source_zip: Path) -> None:
    if work_root.exists():
        shutil.rmtree(work_root)
    work_root.mkdir(parents=True)
    with zipfile.ZipFile(source_zip, "r") as zf:
        zf.extractall(work_root)


def prune_package(
    work_root: Path,
    keep_prefixes: tuple[str, ...],
    include_report_date: bool,
) -> None:
    favorites = work_root / "favorites"
    if favorites.exists():
        shutil.rmtree(favorites)

    standard_offering = work_root / "resources" / "SmartCity" / "Report" / "Standard_Offering"
    if standard_offering.exists():
        shutil.rmtree(standard_offering)

    prefixes = list(keep_prefixes)
    if include_report_date and "resources/SmartCity/Admin/Parameters/" not in prefixes:
        prefixes.append("resources/SmartCity/Admin/Parameters/")

    to_remove: list[Path] = []
    for path in work_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(work_root).as_posix()
        if rel == "index.xml":
            continue
        if not any(rel.startswith(prefix) for prefix in prefixes):
            to_remove.append(path)
    for path in to_remove:
        path.unlink()

    for path in sorted(work_root.rglob("*"), reverse=True):
        if path.is_dir() and not any(path.iterdir()):
            path.rmdir()


def resolve_datasource_export(
    ds_export_dir: Path, client_org: str, target_ds: str
) -> Path:
    for name in (client_org, target_ds):
        root = ds_export_dir / name
        if (root / "index.xml").is_file():
            return root
    raise SystemExit(f"Datasource export not found for {client_org} / {target_ds}")


def overlay_datasource(work_root: Path, ds_export_dir: Path, client_org: str, target_ds: str) -> Path:
    ds_root = resolve_datasource_export(ds_export_dir, client_org, target_ds)
    src = ds_root / "resources" / "DataSource"
    if not src.is_dir():
        raise SystemExit(f"Missing DataSource folder in {ds_root}")
    dest = work_root / "resources" / "DataSource"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)
    return ds_root


def write_zip(work_root: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(work_root.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(work_root))


def main() -> int:
    args = parse_args()
    if not args.source_zip.is_file():
        raise SystemExit(f"Missing source zip: {args.source_zip}")

    keep_prefixes = tuple(args.keep_prefix)
    staging = args.staging_dir
    extract_source(staging, args.source_zip)
    prune_package(staging, keep_prefixes, args.include_report_date)

    if args.include_report_date:
        patch_report_date_input_control(staging)

    if args.patch_jrxml and args.patch_sql_file:
        query_sql = "\n".join(
            line
            for line in args.patch_sql_file.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.strip().startswith("--")
        )
        jrxml_path = staging / args.patch_jrxml
        patch_subdataset_query(jrxml_path, args.patch_subdataset, query_sql)
        patch_report_date_null_safe(jrxml_path)
        validate_jrxml_xml(jrxml_path)

    ds_root = overlay_datasource(staging, args.datasource_export_dir, args.client_org, args.target_ds)

    extra_resources: list[str] = []
    if not args.skip_public_template:
        merge_bundled_public_dashboard_template(str(staging))
        extra_resources.append(PUBLIC_TEMPLATE_URI)

    rewrite_datasource_for_tenant_root(str(staging), args.target_ds)

    ds_index = ds_root / "index.xml"
    keyalias, encrypted, js_version = read_export_index_metadata(str(ds_index))
    (staging / "index.xml").write_text(
        f'<?xml version="1.0" encoding="UTF-8"?><export><property name="keyalias" value="{keyalias}"/></export>',
        encoding="utf-8",
    )
    finalize_tenant_import_index(
        str(staging),
        tenant_id="",
        import_folder_uri=args.import_folder_uri,
        import_datasource_resource_uri=f"/DataSource/{args.target_ds}",
        import_repository_resources=extra_resources or None,
        encrypted=encrypted,
        keyalias=keyalias,
        js_version=js_version,
        import_into_existing_tenant=True,
    )

    if args.report_unit_xml:
        report_text = (staging / args.report_unit_xml).read_text(encoding="utf-8")
        folder_tail = args.import_folder_uri.removeprefix("/SmartCity/Report/")
        if folder_tail not in report_text and args.import_folder_uri not in report_text:
            raise SystemExit(
                f"Report unit folder URI does not match import folder: {args.import_folder_uri}"
            )

    write_zip(staging, args.output_zip)

    verify_cmd = [
        sys.executable,
        str(SCRIPT_DIR / "verify_prepared_import.py"),
        "--zip",
        str(args.output_zip),
        "--target-org",
        args.client_org,
        "--target-ds",
        args.target_ds,
        "--repository-uri-style",
        "org_relative",
        "--repository-layout",
        "tenant_root",
        "--expect-datasource-overlay",
        "--import-module-folder-uri",
        args.import_folder_uri,
    ]
    verify = subprocess.run(verify_cmd, capture_output=True, text=True, check=False)
    print(args.output_zip)
    print(verify.stdout)
    if verify.returncode != 0:
        print(verify.stderr, file=sys.stderr)
        return verify.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
