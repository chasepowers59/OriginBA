#!/usr/bin/env python3
"""Repoint Development/Snapshots domain URIs and remove Development trees from an export."""

from __future__ import annotations

import argparse
import shutil
import tempfile
import zipfile
from pathlib import Path

import sys

_SCRIPT_DIR = Path(__file__).resolve().parent
if str(_SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPT_DIR))

from tenant_root_layout import (  # noqa: E402
    ProcessingError,
    apply_standard_offering_uri_corrections,
    apply_uri_replacements,
    normalize_report_root_uris,
    prefer_standard_offering_tree,
    regenerate_tenant_folder_metadata,
    remove_superseded_development_snapshot_tree,
    rewrite_development_snapshot_domain_uris,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Repoint Development snapshot domains to Standard_Offering and drop Development trees."
    )
    parser.add_argument("--source-zip", required=True, help="Input Jaspersoft export ZIP.")
    parser.add_argument("--output-zip", required=True, help="Sanitized output ZIP path.")
    return parser.parse_args()


def validate_no_development_references(work_root: Path) -> list[str]:
    issues: list[str] = []
    for path in work_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".xml", ".data", ".jrxml"}:
            continue
        if path.name == "index.xml":
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "Development/Snapshots" in text or "/Report/Workstreams/Development" in text:
            issues.append(str(path.relative_to(work_root)))
    return issues


JUNK_FAVORITE_NAMES = {"index.xml", "2441019.xml"}


def validate_no_workstreams_references(work_root: Path) -> list[str]:
    issues: list[str] = []
    for path in work_root.rglob("*"):
        if path.is_file():
            relative = path.relative_to(work_root).as_posix()
            if "/Report/Workstreams/" in relative:
                issues.append(relative)
                continue
            if path.suffix not in {".xml", ".data", ".jrxml"}:
                continue
            if path.name == "index.xml":
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "/SmartCity/Report/Workstreams/" in text:
                issues.append(relative)
    return issues


def validate_folder_resource_references(work_root: Path) -> list[str]:
    issues: list[str] = []
    smartcity_root = work_root / "resources" / "SmartCity"
    if not smartcity_root.is_dir():
        return issues

    for folder_xml in smartcity_root.rglob(".folder.xml"):
        directory = folder_xml.parent
        text = folder_xml.read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped.startswith("<resource>") or not stripped.endswith("</resource>"):
                continue
            resource_name = stripped[len("<resource>") : -len("</resource>")]
            resource_xml = directory / f"{resource_name}.xml"
            if not resource_xml.is_file():
                issues.append(
                    f"{folder_xml.relative_to(work_root)} references missing resource {resource_name}"
                )
    return issues


def remove_junk_artifacts(work_root: Path) -> int:
    removed = 0
    for path in list(work_root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(work_root).as_posix()
        if path.name in JUNK_FAVORITE_NAMES and relative.startswith("favorites/"):
            path.unlink()
            removed += 1
    smartcity_root = work_root / "resources" / "SmartCity"
    if removed and smartcity_root.is_dir():
        regenerate_tenant_folder_metadata(str(smartcity_root))
    return removed


def normalize_workstreams_tree(work_root: Path) -> int:
    smartcity_root = work_root / "resources" / "SmartCity"
    if not smartcity_root.is_dir():
        return 0

    uri_remap = prefer_standard_offering_tree(str(smartcity_root))
    changed = 0
    if uri_remap:
        normalized_remap = {
            old.replace("/SmartCity/Report/Workstreams/", "/SmartCity/Report/Standard_Offering/"): new
            for old, new in uri_remap.items()
        }
        changed += apply_uri_replacements(str(work_root), normalized_remap)

    normalize_report_root_uris(str(work_root), "Standard_Offering")
    changed += apply_standard_offering_uri_corrections(str(work_root))
    return changed


def sanitize_export_tree(work_root: Path) -> int:
    changed = normalize_workstreams_tree(work_root)
    changed += rewrite_development_snapshot_domain_uris(str(work_root), "Standard_Offering")
    remove_superseded_development_snapshot_tree(str(work_root))
    changed += remove_junk_artifacts(work_root)

    development_issues = validate_no_development_references(work_root)
    if development_issues:
        sample = "\n".join(f"  - {item}" for item in development_issues[:10])
        raise ProcessingError(
            "Development references remain after sanitize:\n"
            f"{sample}"
        )

    workstreams_issues = validate_no_workstreams_references(work_root)
    if workstreams_issues:
        sample = "\n".join(f"  - {item}" for item in workstreams_issues[:10])
        raise ProcessingError(
            "Workstreams references remain after sanitize:\n"
            f"{sample}"
        )

    folder_issues = validate_folder_resource_references(work_root)
    if folder_issues:
        sample = "\n".join(f"  - {item}" for item in folder_issues[:10])
        raise ProcessingError(
            "Folder metadata references missing resources:\n"
            f"{sample}"
        )
    return changed


def zip_tree(source_dir: Path, output_zip: Path) -> None:
    from prepare_client_imports import zip_jaspersoft_export

    output_zip.parent.mkdir(parents=True, exist_ok=True)
    if output_zip.exists():
        output_zip.unlink()
    zip_jaspersoft_export(str(source_dir), str(output_zip))


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).resolve()
    output_zip = Path(args.output_zip).resolve()
    if not source_zip.is_file():
        raise SystemExit(f"Source ZIP not found: {source_zip}")

    with tempfile.TemporaryDirectory(prefix="standard_offering_sanitize_") as tmp:
        work_root = Path(tmp) / "export"
        with zipfile.ZipFile(source_zip) as archive:
            archive.extractall(work_root)
        changed = sanitize_export_tree(work_root)
        zip_tree(work_root, output_zip)

    print(f"Sanitized ZIP: {output_zip}")
    print(f"files updated during sanitize: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
