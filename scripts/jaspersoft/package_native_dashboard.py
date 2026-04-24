#!/usr/bin/env python3
"""
Package a single native Jaspersoft dashboard (dashboardModelResource) into an
importable ZIP with its governed Domain and datasource dependency.

Initial use case:
- promote one dashboard at a time into Standard_Offering
- keep package scope narrow and import-safe
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET


ORG_ROOT = "/organizations/organization_1/organizations/Origin_DEV"
ORG_REPORT_ROOT = f"{ORG_ROOT}/SmartCity/Report"
TARGET_PACK_ROOT = f"{ORG_REPORT_ROOT}/Standard_Offering"
DATASOURCE_FOLDER_URI = f"{ORG_ROOT}/DataSource"
DATASOURCE_RESOURCE_URI = f"{DATASOURCE_FOLDER_URI}/Origin_DEV_DS"
DATASOURCE_FOLDER_MEMBER = (
    "resources/organizations/organization_1/organizations/Origin_DEV/DataSource/.folder.xml"
)
DATASOURCE_RESOURCE_MEMBER = (
    "resources/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS.xml"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Package a single native Jaspersoft dashboard.")
    parser.add_argument(
        "--source-zip",
        default="/Users/chase/Downloads/Workstream folder.zip",
        help="Path to the exported Jaspersoft ZIP.",
    )
    parser.add_argument(
        "--dashboard-member",
        required=True,
        help="Exact ZIP member path for the source dashboard XML.",
    )
    parser.add_argument(
        "--target-subpath",
        required=True,
        help="Subpath under Standard_Offering, for example Finance/Financial_Transaction.",
    )
    parser.add_argument(
        "--outdir",
        default="/Users/chase/OriginBA-3/deploy/native_dashboard_pack_v1",
        help="Output directory for the package.",
    )
    return parser.parse_args()


def decode_bytes(data: bytes) -> str | None:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def build_folder_xml(name: str, label: str, parent_uri: str, subfolders: list[str], resources: list[str]) -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<folder exportedWithPermissions="true">',
        f"    <parent>{parent_uri}</parent>",
        f"    <name>{name}</name>",
        f"    <label>{label}</label>",
    ]
    for subfolder in sorted(subfolders):
        parts.append(f"    <folder>{subfolder}</folder>")
    for resource in sorted(resources):
        parts.append(f"    <resource>{resource}</resource>")
    parts.append("</folder>")
    parts.append("")
    return "\n".join(parts)


def label_from_name(name: str) -> str:
    return name.replace("___", " ").replace("__", " ").replace("_", " ")


def strip_adhoc_report_wrappers(text: str) -> str:
    return re.sub(r"\s*<reports>.*?</reports>\s*", "\n", text, flags=re.DOTALL)


def collect_tree_members(files: dict[str, bytes], root_member: str) -> dict[str, bytes]:
    collected: dict[str, bytes] = {}
    if root_member in files:
        collected[root_member] = files[root_member]
    if root_member.endswith(".xml"):
        prefix = root_member[:-4] + "_files/"
        for name, payload in files.items():
            if name.startswith(prefix):
                collected[name] = payload
    return collected


def find_domain_member(dashboard_text: str, archive_names: list[str]) -> str:
    match = re.search(
        r"<dataSource>\s*<uri>(/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/.+?/([^/<]+))</uri>",
        dashboard_text,
        flags=re.DOTALL,
    )
    if not match:
        raise SystemExit("Could not find dashboard domain URI in dashboard XML.")
    domain_uri = match.group(1)
    domain_name = match.group(2)
    expected_suffix = f"/{domain_name}.xml"
    for name in archive_names:
        if name.endswith(expected_suffix) and "resources/" in name:
            return name
    raise SystemExit(f"Could not resolve domain XML member for {domain_uri}.")


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).expanduser().resolve()
    outdir = Path(args.outdir).expanduser().resolve()
    workspace = outdir / "_single_dashboard_build"

    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(source_zip) as archive:
        files = {
            name: archive.read(name)
            for name in archive.namelist()
            if not name.endswith("/")
        }
        names = list(files.keys())

    dashboard_member = args.dashboard_member
    if dashboard_member not in files:
        raise SystemExit(f"Dashboard member not found in ZIP: {dashboard_member}")

    dashboard_text = decode_bytes(files[dashboard_member])
    if dashboard_text is None:
        raise SystemExit(f"Dashboard XML not readable: {dashboard_member}")

    domain_member = find_domain_member(dashboard_text, names)
    dashboard_members = collect_tree_members(files, dashboard_member)
    domain_members = collect_tree_members(files, domain_member)

    included_files: dict[str, bytes] = {}
    included_files.update(dashboard_members)
    included_files.update(domain_members)
    included_files[DATASOURCE_FOLDER_MEMBER] = files[DATASOURCE_FOLDER_MEMBER]
    included_files[DATASOURCE_RESOURCE_MEMBER] = files[DATASOURCE_RESOURCE_MEMBER]

    source_dashboard_root = dashboard_member.rsplit(".xml", 1)[0]
    source_domain_root = domain_member.rsplit(".xml", 1)[0]
    source_dashboard_text = decode_bytes(files[dashboard_member]) or ""
    source_domain_text = decode_bytes(files[domain_member]) or ""

    dashboard_name = ET.fromstring(source_dashboard_text).findtext("name") or Path(dashboard_member).stem
    domain_name = ET.fromstring(source_domain_text).findtext("name") or Path(domain_member).stem

    target_folder_uri = f"{TARGET_PACK_ROOT}/{args.target_subpath.strip('/')}"
    target_dashboard_uri = f"{target_folder_uri}/{dashboard_name}"
    target_domain_uri = f"{target_folder_uri}/{domain_name}"

    source_dashboard_uri = (
        (ET.fromstring(source_dashboard_text).findtext("folder") or "").strip() + f"/{dashboard_name}"
    )
    source_domain_uri = (
        (ET.fromstring(source_domain_text).findtext("folder") or "").strip() + f"/{domain_name}"
    )

    source_dashboard_path_prefix = source_dashboard_root.rsplit("/", 1)[0]
    target_path_prefix = (
        "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
        f"Standard_Offering/{args.target_subpath.strip('/')}"
    )

    replacement_map = {
        source_dashboard_uri: target_dashboard_uri,
        source_domain_uri: target_domain_uri,
        source_dashboard_uri + "_files": target_dashboard_uri + "_files",
        source_domain_uri + "_files": target_domain_uri + "_files",
        source_dashboard_uri.rsplit("/", 1)[0]: target_folder_uri,
        source_domain_uri.rsplit("/", 1)[0]: target_folder_uri,
        source_dashboard_path_prefix: target_path_prefix,
        DATASOURCE_RESOURCE_URI: DATASOURCE_RESOURCE_URI,
    }
    rewrite_pairs = sorted(replacement_map.items(), key=lambda item: len(item[0]), reverse=True)

    for rel_path, payload in included_files.items():
        if "/dashboardReport_files/" in rel_path:
            continue
        if rel_path == dashboard_member:
            target_rel_path = f"{target_path_prefix}/{dashboard_name}.xml"
        elif rel_path.startswith(source_dashboard_root + "_files/"):
            suffix = rel_path.removeprefix(source_dashboard_root + "_files/")
            target_rel_path = f"{target_path_prefix}/{dashboard_name}_files/{suffix}"
        elif rel_path == domain_member:
            target_rel_path = f"{target_path_prefix}/{domain_name}.xml"
        elif rel_path.startswith(source_domain_root + "_files/"):
            suffix = rel_path.removeprefix(source_domain_root + "_files/")
            target_rel_path = f"{target_path_prefix}/{domain_name}_files/{suffix}"
        else:
            target_rel_path = rel_path

        target_path = workspace / target_rel_path
        ensure_parent(target_path)
        text = decode_bytes(payload)
        if text is None:
            target_path.write_bytes(payload)
            continue
        for old, new in rewrite_pairs:
            text = text.replace(old, new)
        if "<dashboardModelResource" in text or "<adhocDataView" in text:
            text = strip_adhoc_report_wrappers(text)
        target_path.write_text(text, encoding="utf-8")

    # Folder metadata.
    folder_children: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"folders": set(), "resources": set()})
    pack_root_uri = TARGET_PACK_ROOT
    workstream_uri = f"{TARGET_PACK_ROOT}/{args.target_subpath.strip('/').split('/')[0]}"
    folder_children[target_folder_uri]["resources"].update({dashboard_name, domain_name})
    folder_children[workstream_uri]["folders"].add(Path(target_folder_uri).name)
    folder_children[pack_root_uri]["folders"].add(Path(workstream_uri).name)

    for folder_uri, children in list(folder_children.items()):
        if folder_uri == pack_root_uri:
            parent_uri = ORG_REPORT_ROOT
            name = "Standard_Offering"
            label = "Standard Offering"
        else:
            parent_uri = str(Path(folder_uri).parent).replace("\\", "/")
            name = Path(folder_uri).name
            label = label_from_name(name)
        folder_rel_path = (
            "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
            f"{folder_uri.removeprefix(ORG_REPORT_ROOT + '/')}/.folder.xml"
        )
        folder_path = workspace / folder_rel_path
        ensure_parent(folder_path)
        folder_xml = build_folder_xml(
            name=name,
            label=label,
            parent_uri=parent_uri,
            subfolders=list(children["folders"]),
            resources=list(children["resources"]),
        )
        folder_path.write_text(folder_xml, encoding="utf-8")

    # Build index.xml
    export = ET.Element("export")
    ET.SubElement(export, "module", {"id": "repositoryResources"})
    repo_module = export.find("module")
    ET.SubElement(repo_module, "folder").text = target_folder_uri
    ET.SubElement(repo_module, "resource").text = DATASOURCE_RESOURCE_URI
    ET.SubElement(export, "property", {"name": "pathProcessorId", "value": "zip"})
    ET.SubElement(export, "property", {"name": "rootTenantId", "value": "organizations"})
    ET.SubElement(export, "property", {"name": "jsVersion", "value": "8.1.0 PRO"})
    index_path = workspace / "index.xml"
    index_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(export, encoding="unicode"),
        encoding="utf-8",
    )

    outdir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9]+", "_", dashboard_name).strip("_")
    audit = {
        "source_zip": str(source_zip),
        "dashboard_member": dashboard_member,
        "domain_member": domain_member,
        "target_folder_uri": target_folder_uri,
        "target_dashboard_uri": target_dashboard_uri,
        "target_domain_uri": target_domain_uri,
        "datasource_resource_uri": DATASOURCE_RESOURCE_URI,
        "removed_dashboard_report_wrappers": True,
    }
    audit_path = outdir / f"{slug}_package_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    package_zip = outdir / f"{slug}_import.zip"
    if package_zip.exists():
        package_zip.unlink()
    with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(workspace).as_posix())

    print(f"Built package: {package_zip}")
    print(f"Audit JSON: {audit_path}")
    print(f"Target folder: {target_folder_uri}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
