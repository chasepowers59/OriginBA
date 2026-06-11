#!/usr/bin/env python3
"""Verify a tenant-root Standard Offering import ZIP against a source export."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


RESOURCE_TAGS = {
    "adhocDataView",
    "reportUnit",
    "dashboardModelResource",
    "semanticLayerDataSource",
    "contentResource",
    "fileResource",
}

PUBLIC_TEMPLATE_XML = "resources/public/templates/actual_size.820.jrxml.xml"
PUBLIC_TEMPLATE_DATA = "resources/public/templates/actual_size.820.jrxml.data"
IMPORT_FOLDER_URI = "/SmartCity/Report/Standard_Offering"


@dataclass
class ArtifactInventory:
    labels_by_tag: dict[str, set[str]] = field(default_factory=dict)
    counts_by_tag: Counter[str] = field(default_factory=Counter)

    def add(self, tag: str, label: str) -> None:
        self.counts_by_tag[tag] += 1
        self.labels_by_tag.setdefault(tag, set()).add(label)


@dataclass
class VerificationReport:
    ok: bool = True
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, object] = field(default_factory=dict)

    def fail(self, message: str) -> None:
        self.ok = False
        self.issues.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a prepared tenant-root Standard Offering import ZIP."
    )
    parser.add_argument("--zip", required=True, help="Prepared import ZIP to verify.")
    parser.add_argument(
        "--source-zip",
        help="Optional source Standard Offering export used as label/content baseline.",
    )
    parser.add_argument("--target-ds", required=True, help="Expected datasource alias.")
    parser.add_argument(
        "--forbid-source-ds",
        help="Source datasource alias that must not remain (for example Origin_DEV_DS on Stage).",
    )
    parser.add_argument(
        "--expected-dashboard-labels",
        nargs="*",
        help="Optional explicit dashboard labels that must be present.",
    )
    parser.add_argument("--output-json", help="Optional JSON output path.")
    parser.add_argument(
        "--tenant-id",
        help="Expected index.xml rootTenantId for server-root imports (omit for in-tenant imports).",
    )
    parser.add_argument(
        "--expected-keyalias",
        help="Expected index.xml keyalias when target server encryption differs from source export.",
    )
    return parser.parse_args()


def decode_bytes(data: bytes) -> str | None:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def inventory_zip(zip_path: Path) -> ArtifactInventory:
    inventory = ArtifactInventory()
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if not name.endswith(".xml") or ".folder.xml" in name or "_files/" in name:
                continue
            payload = archive.read(name)
            try:
                root = ET.fromstring(payload)
            except ET.ParseError:
                continue
            tag = root.tag.split("}", 1)[-1]
            if tag not in RESOURCE_TAGS:
                continue
            label = (root.findtext("label") or root.findtext("name") or "").strip()
            if label:
                inventory.add(tag, label)
    return inventory


def verify_zip_structure(archive: zipfile.ZipFile, report: VerificationReport) -> None:
    names = archive.namelist()
    if "index.xml" not in names:
        report.fail("missing index.xml")
        return
    if names[-1] != "index.xml":
        report.fail("index.xml must be the final ZIP entry (Jaspersoft export contract)")
    if "favorites/" not in names:
        report.fail("missing favorites/ directory required by Jaspersoft export format")
        return
    for entry_name in ("favorites/", "resources/"):
        if entry_name not in names:
            continue
        info = archive.getinfo(entry_name)
        if info.compress_type != zipfile.ZIP_DEFLATED:
            report.fail(
                f"{entry_name} must use ZIP_DEFLATED compression (found compress_type={info.compress_type})"
            )


def read_index_property(root: ET.Element, name: str) -> str | None:
    for prop in root.findall("property"):
        if prop.get("name") == name:
            return (prop.get("value") or "").strip() or None
    return None


def verify_index(
    archive: zipfile.ZipFile,
    target_ds: str,
    report: VerificationReport,
    *,
    expected_tenant_id: str | None = None,
    source_index_root: ET.Element | None = None,
    expected_keyalias: str | None = None,
) -> None:
    verify_zip_structure(archive, report)
    if "index.xml" not in archive.namelist():
        return
    index_text = decode_bytes(archive.read("index.xml"))
    if index_text is None:
        report.fail("unreadable index.xml")
        return
    root = ET.fromstring(index_text)
    children = list(root)
    if not children or children[0].tag != "property" or children[0].get("name") != "keyalias":
        report.fail("index.xml must start with keyalias property (Jaspersoft export contract)")
    child_tags = [child.tag for child in children]
    if child_tags.count("module") < 2:
        report.fail("index.xml must include repositoryResources and favorites modules")
    favorites_index = child_tags.index("module", 1) if child_tags.count("module") > 1 else -1
    if favorites_index == -1:
        report.fail("index.xml missing favorites module in expected position")
    repo_module = next(
        (module for module in root.findall("module") if module.get("id") == "repositoryResources"),
        None,
    )
    if repo_module is None:
        report.fail("index.xml missing repositoryResources module")
        return

    resources = [(node.text or "").strip() for node in repo_module.findall("resource")]
    folders = [(node.text or "").strip() for node in repo_module.findall("folder")]
    if f"/DataSource/{target_ds}" not in resources:
        report.fail(f"index.xml missing datasource resource /DataSource/{target_ds}")
    if "/public/templates/actual_size.820.jrxml" not in resources:
        report.fail("index.xml missing public dashboard template resource")
    if IMPORT_FOLDER_URI not in folders:
        report.fail(f"index.xml missing import folder {IMPORT_FOLDER_URI}")

    actual_tenant_id = read_index_property(root, "rootTenantId")
    if expected_tenant_id:
        if actual_tenant_id != expected_tenant_id:
            report.fail(
                f"index.xml rootTenantId mismatch: expected {expected_tenant_id!r}, "
                f"found {actual_tenant_id!r}"
            )
    elif actual_tenant_id:
        report.fail(
            "index.xml should not set rootTenantId when importing into an existing tenant"
        )

    if expected_keyalias:
        actual_keyalias = read_index_property(root, "keyalias")
        if actual_keyalias != expected_keyalias:
            report.fail(
                f"index.xml keyalias mismatch: expected {expected_keyalias!r}, "
                f"found {actual_keyalias!r}"
            )
    elif source_index_root is not None:
        for property_name in ("keyalias", "encrypted"):
            expected = read_index_property(source_index_root, property_name)
            actual = read_index_property(root, property_name)
            if expected and actual != expected:
                report.fail(
                    f"index.xml {property_name} must match the source export "
                    f"(expected {expected!r}, found {actual!r})"
                )


def verify_datasource(archive: zipfile.ZipFile, target_ds: str, report: VerificationReport) -> None:
    datasource_path = f"resources/DataSource/{target_ds}.xml"
    if datasource_path not in archive.namelist():
        report.fail(f"missing datasource XML: {datasource_path}")
        return
    root = ET.fromstring(archive.read(datasource_path))
    if root.tag.split("}", 1)[-1] != "jdbcDataSource":
        report.fail(f"unexpected datasource root tag in {datasource_path}")
    name = (root.findtext("name") or "").strip()
    folder = (root.findtext("folder") or "").strip()
    if name != target_ds:
        report.fail(f"datasource name mismatch: expected {target_ds}, found {name!r}")
    if folder != "/DataSource":
        report.fail(f"datasource folder mismatch: expected /DataSource, found {folder!r}")


def scan_forbidden_fragments(
    archive: zipfile.ZipFile,
    fragments: Iterable[str],
    report: VerificationReport,
) -> None:
    hits: list[str] = []
    for name in archive.namelist():
        if name.endswith("/"):
            continue
        text = decode_bytes(archive.read(name))
        if text is None:
            continue
        for fragment in fragments:
            if fragment and fragment in text:
                hits.append(f"{fragment} in {name}")
                break
    if hits:
        report.fail(f"forbidden fragment(s) found: {hits[0]}")
    report.details["forbidden_fragment_hits"] = hits


def build_resource_index(archive: zipfile.ZipFile) -> dict[str, dict[str, str]]:
    resources: dict[str, dict[str, str]] = {}
    for name in archive.namelist():
        if not name.endswith(".xml") or ".folder.xml" in name or "_files/" in name:
            continue
        payload = archive.read(name)
        try:
            root = ET.fromstring(payload)
        except ET.ParseError:
            continue
        tag = root.tag.split("}", 1)[-1]
        if tag not in RESOURCE_TAGS:
            continue
        folder = (root.findtext("folder") or "").strip()
        resource_name = (root.findtext("name") or "").strip()
        label = (root.findtext("label") or resource_name).strip()
        uri = f"{folder}/{resource_name}" if folder else resource_name
        resources[uri] = {
            "path": name,
            "tag": tag,
            "label": label,
            "name": resource_name,
        }
    return resources


ALLOWED_NON_OFFERING_SMARTCITY = {
    "resources/SmartCity/.folder.xml",
    "resources/SmartCity/Report/.folder.xml",
}


def verify_resource_placement(archive: zipfile.ZipFile, report: VerificationReport) -> None:
    bad_paths = [
        name
        for name in archive.namelist()
        if not name.endswith("/")
        and name.startswith("resources/SmartCity/")
        and "/Standard_Offering/" not in name
        and "/public/" not in name
        and name not in ALLOWED_NON_OFFERING_SMARTCITY
    ]
    if bad_paths:
        report.fail(
            "SmartCity artifacts exist outside Standard_Offering: "
            f"{bad_paths[0]}"
        )
    report.details["non_offering_smartcity_paths"] = bad_paths


def verify_duplicate_resource_names(
    resources: dict[str, dict[str, str]],
    report: VerificationReport,
) -> None:
    by_name: dict[str, list[str]] = defaultdict(list)
    for uri, meta in resources.items():
        by_name[meta["name"]].append(uri)
    duplicates = {name: uris for name, uris in by_name.items() if len(uris) > 1}
    report.details["duplicate_resource_names"] = duplicates
    if duplicates:
        first_name = next(iter(duplicates))
        report.fail(
            "duplicate repository resource names across folders: "
            f"{first_name} -> {duplicates[first_name]}"
        )


def verify_unresolved_resource_uris(
    archive: zipfile.ZipFile,
    resources: dict[str, dict[str, str]],
    report: VerificationReport,
) -> None:
    resource_uris = set(resources)
    unresolved: dict[str, int] = Counter()
    pattern = re.compile(r"/SmartCity/Report/Standard_Offering/[A-Za-z0-9_./-]+")
    for name in archive.namelist():
        if name.endswith("/"):
            continue
        text = decode_bytes(archive.read(name))
        if text is None:
            continue
        for match in set(pattern.findall(text)):
            if match.endswith("_files") or "_files/" in match or match.startswith("/temp/"):
                continue
            if match in resource_uris:
                continue
            if any(uri.startswith(match + "/") for uri in resource_uris):
                continue
            unresolved[match] += 1
    report.details["unresolved_resource_uris"] = dict(unresolved)
    if unresolved:
        uri = next(iter(unresolved))
        report.fail(f"unresolved Standard_Offering resource URI: {uri}")


def verify_domain_datasource_bindings(
    archive: zipfile.ZipFile,
    resources: dict[str, dict[str, str]],
    target_ds: str,
    report: VerificationReport,
) -> None:
    bad_domains: list[str] = []
    for uri, meta in resources.items():
        if meta["tag"] != "semanticLayerDataSource":
            continue
        text = decode_bytes(archive.read(meta["path"]))
        if text is None:
            continue
        ds_uri_match = re.search(r"<uri>(/DataSource/[^<]+)</uri>", text)
        if ds_uri_match and ds_uri_match.group(1) != f"/DataSource/{target_ds}":
            bad_domains.append(f"{meta['label']}: {ds_uri_match.group(1)}")
    report.details["domain_datasource_mismatches"] = bad_domains
    if bad_domains:
        report.fail(f"domain datasource mismatch: {bad_domains[0]}")


def compare_label_sets(
    source: ArtifactInventory,
    prepared: ArtifactInventory,
    report: VerificationReport,
) -> None:
    for tag in ("adhocDataView", "dashboardModelResource", "semanticLayerDataSource"):
        missing = sorted(source.labels_by_tag.get(tag, set()) - prepared.labels_by_tag.get(tag, set()))
        if missing:
            report.fail(f"missing {tag} labels: {missing[:5]}" + (" ..." if len(missing) > 5 else ""))


def verify_zip(
    zip_path: Path,
    *,
    source_zip: Path | None,
    target_ds: str,
    forbid_source_ds: str | None,
    expected_dashboard_labels: list[str] | None,
    tenant_id: str | None = None,
    expected_keyalias: str | None = None,
) -> VerificationReport:
    report = VerificationReport()
    prepared = inventory_zip(zip_path)
    report.details["artifact_counts"] = dict(prepared.counts_by_tag)
    report.details["dashboard_labels"] = sorted(
        prepared.labels_by_tag.get("dashboardModelResource", set())
    )

    source_index_root: ET.Element | None = None
    if source_zip and source_zip.is_file():
        with zipfile.ZipFile(source_zip) as source_archive:
            source_index_text = decode_bytes(source_archive.read("index.xml"))
            if source_index_text:
                source_index_root = ET.fromstring(source_index_text)

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        if not any(name.startswith("resources/SmartCity/Report/Standard_Offering/") for name in names):
            report.fail("missing tenant-root Standard_Offering tree")
        if PUBLIC_TEMPLATE_XML not in names or PUBLIC_TEMPLATE_DATA not in names:
            report.fail("missing bundled public dashboard template files")
        if any("resources/organizations/organization_1/" in name for name in names):
            report.fail("package still contains org-tree repository paths")
        if any("/SmartCity/Report/Workstreams/" in name for name in names):
            report.fail("package still contains Workstreams repository paths")
        if any("/Standard_Offering/Development/" in name for name in names):
            report.fail("package still contains superseded Development/Snapshots tree")

        resources = build_resource_index(archive)
        report.details["resource_uri_count"] = len(resources)

        verify_index(
            archive,
            target_ds,
            report,
            expected_tenant_id=tenant_id,
            source_index_root=source_index_root,
            expected_keyalias=expected_keyalias,
        )
        verify_datasource(archive, target_ds, report)
        verify_resource_placement(archive, report)
        verify_duplicate_resource_names(resources, report)
        verify_unresolved_resource_uris(archive, resources, report)
        verify_domain_datasource_bindings(archive, resources, target_ds, report)

        forbidden = [
            "/organizations/organization_1/",
            "/SmartCity/Report/Workstreams/",
            "/SmartCity/Report/Standard_Offering/Cashiering/Payment_Tender/Cashiering_Dashboard",
        ]
        if forbid_source_ds:
            forbidden.append(forbid_source_ds)
        scan_forbidden_fragments(archive, forbidden, report)

    if expected_dashboard_labels:
        present = prepared.labels_by_tag.get("dashboardModelResource", set())
        missing = [label for label in expected_dashboard_labels if label not in present]
        if missing:
            report.fail(f"missing expected dashboards: {missing}")

    if source_zip and source_zip.is_file():
        source = inventory_zip(source_zip)
        compare_label_sets(source, prepared, report)
        report.details["source_artifact_counts"] = dict(source.counts_by_tag)

    return report


def main() -> int:
    args = parse_args()
    zip_path = Path(args.zip).resolve()
    source_zip = Path(args.source_zip).resolve() if args.source_zip else None
    if not zip_path.is_file():
        print(f"ERROR: ZIP not found: {zip_path}", file=sys.stderr)
        return 2

    report = verify_zip(
        zip_path,
        source_zip=source_zip,
        target_ds=args.target_ds,
        forbid_source_ds=args.forbid_source_ds,
        expected_dashboard_labels=args.expected_dashboard_labels,
        tenant_id=args.tenant_id,
        expected_keyalias=args.expected_keyalias,
    )

    print(f"ZIP: {zip_path}")
    print(f"status: {'PASS' if report.ok else 'FAIL'}")
    print(f"artifact counts: {report.details.get('artifact_counts')}")
    print(f"dashboards: {report.details.get('dashboard_labels')}")
    for message in report.issues:
        print(f"- {message}")
    for message in report.warnings:
        print(f"! {message}")

    if args.output_json:
        Path(args.output_json).write_text(
            json.dumps(
                {
                    "zip": str(zip_path),
                    "ok": report.ok,
                    "issues": report.issues,
                    "warnings": report.warnings,
                    "details": report.details,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
