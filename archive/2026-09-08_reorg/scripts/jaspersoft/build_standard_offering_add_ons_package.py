#!/usr/bin/env python3
"""
Build a curated "Standard Offering Add-Ons" Jaspersoft import package.

This package is sourced from the existing Standard_Offering import ZIP and
contains high-value Ad Hoc views grouped by analytics use case:
 - billing integrity / estimate / rebill
 - arrears / collections / write-off
 - meter measurement / usage exceptions / aging
 - field activity backlog / overdue / cycle-time
 - customer case/contact workload and durations
 - GL/FT status and distribution diagnostics
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET


ORG_REPORT_ROOT = "/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report"
ORG_ROOT = "/organizations/organization_1/organizations/Origin_DEV"
SOURCE_STANDARD_ROOT = f"{ORG_REPORT_ROOT}/Standard_Offering"
ADD_ONS_ROOT_NAME = "Standard_Offering_Add_Ons"
ADD_ONS_ROOT_URI = f"{ORG_REPORT_ROOT}/{ADD_ONS_ROOT_NAME}"
DOMAINS_FOLDER_NAME = "Domains"
DOMAINS_FOLDER_URI = f"{ADD_ONS_ROOT_URI}/{DOMAINS_FOLDER_NAME}"

DATASOURCE_RESOURCE_URI = f"{ORG_ROOT}/DataSource/Origin_DEV_DS"
DATASOURCE_FOLDER_MEMBER = (
    "resources/organizations/organization_1/organizations/Origin_DEV/DataSource/.folder.xml"
)
DATASOURCE_RESOURCE_MEMBER = (
    "resources/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS.xml"
)


# label -> category folder
SELECTED_REPORTS = {
    # billing integrity / estimate / rebill
    "Billed Amount - Estimated Segment": "Billing_Integrity",
    "Billed Amount - Rebills": "Billing_Integrity",
    "Billed Amount - Canceled Segments": "Billing_Integrity",
    "Billed Usage - Segment Determinant": "Billing_Integrity",
    # arrears / collections / write-off
    "Collection Process - Age of Un-Paid Bills": "Arrears_Collections_Write_Off",
    "Collection Process - Active Collections": "Arrears_Collections_Write_Off",
    "Collection Process - Upcoming Collection Events": "Arrears_Collections_Write_Off",
    "SA Snapshot - Total Amount of Aged Arrears": "Arrears_Collections_Write_Off",
    "Write Off Process - Active Write Off Processes": "Arrears_Collections_Write_Off",
    "Write Offs - Debt Written Off Trend": "Arrears_Collections_Write_Off",
    "Write Offs - Average Process Duration": "Arrears_Collections_Write_Off",
    # meter measurement/usage exceptions/aging
    "Measurements - Estimated": "Meter_Exceptions_And_Aging",
    "Measurement - Measurement Conditions Trend": "Meter_Exceptions_And_Aging",
    "Usage Transaction Exceptions – Incomplete": "Meter_Exceptions_And_Aging",
    "Device - Meters not Recently Read": "Meter_Exceptions_And_Aging",
    "VEE Exception - Exception Severity Distribution": "Meter_Exceptions_And_Aging",
    "VEE Exception - Rules Generating the Most Exceptions": "Meter_Exceptions_And_Aging",
    # field activity backlog/overdue/cycle-time
    "Field Activity – Overdue Work Orders": "Field_Activity_Performance",
    "Field Activity - Average Days per Field Task": "Field_Activity_Performance",
    "Crew - Incomplete Work Orders": "Field_Activity_Performance",
    "Field Activity - Upcoming Field Work": "Field_Activity_Performance",
    # customer case/contact workload and durations
    "Case – Open Cases by Account": "Customer_Workload_And_Durations",
    "Case – Time in Previous State": "Customer_Workload_And_Durations",
    "Case – Average Case Duration": "Customer_Workload_And_Durations",
    "Case - Cases Created by Month": "Customer_Workload_And_Durations",
    "Customer Contact – Contact Breakdown": "Customer_Workload_And_Durations",
    "Customer Contact – Monthly Created Contacts": "Customer_Workload_And_Durations",
    # GL/FT diagnostics
    "Financial Transaction - GL Distribution Status": "GL_FT_Diagnostics",
    "Financial Transaction - Bill Cycle Transactions": "GL_FT_Diagnostics",
    "Financial Transaction - Total Transactions by Type": "GL_FT_Diagnostics",
    "General Ledger - by Batch Number": "GL_FT_Diagnostics",
    "General Ledger - GL Account and Distribution": "GL_FT_Diagnostics",
}

# Some labels vary in punctuation between exports
LABEL_ALIASES = {
    "Usage Transaction Exceptions - Incomplete": "Usage Transaction Exceptions – Incomplete",
    "Case - Open Cases by Account": "Case – Open Cases by Account",
    "Case - Time in Previous State": "Case – Time in Previous State",
    "Case - Average Case Duration": "Case – Average Case Duration",
    "Customer Contact - Contact Breakdown": "Customer Contact – Contact Breakdown",
    "Customer Contact - Monthly Created Contacts": "Customer Contact – Monthly Created Contacts",
    "Field Activity - Overdue Work Orders": "Field Activity – Overdue Work Orders",
}


@dataclass
class Resource:
    rel_path: str
    root_tag: str
    label: str
    name: str
    folder_uri: str
    data_source_uri: str | None

    @property
    def resource_uri(self) -> str:
        return f"{self.folder_uri}/{self.name}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Standard Offering Add-Ons import ZIP.")
    parser.add_argument(
        "--source-zip",
        default="deploy/jaspersoft_standard_offering/Standard_Offering_import.zip",
        help="Path to the existing Standard_Offering import ZIP.",
    )
    parser.add_argument(
        "--outdir",
        default="deploy/jaspersoft_standard_offering_add_ons",
        help="Output directory for add-ons package and audit file.",
    )
    return parser.parse_args()


def decode_bytes(data: bytes) -> str | None:
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def normalize_label(value: str) -> str:
    value = value.strip().lower()
    for dash in ("–", "—", "−"):
        value = value.replace(dash, "-")
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def parse_resource(rel_path: str, text: str) -> Resource | None:
    if not rel_path.endswith(".xml"):
        return None
    if "/resources/" not in f"/{rel_path}":
        return None
    try:
        root = ET.fromstring(text)
    except ET.ParseError:
        return None

    root_tag = strip_ns(root.tag)
    if root_tag not in {"adhocDataView", "semanticLayerDataSource"}:
        return None

    label = (root.findtext("label") or "").strip()
    name = (root.findtext("name") or Path(rel_path).stem).strip()
    folder_uri = (root.findtext("folder") or "").strip()
    data_source_uri = (root.findtext(".//dataSource/uri") or "").strip() or None

    return Resource(
        rel_path=rel_path,
        root_tag=root_tag,
        label=label,
        name=name,
        folder_uri=folder_uri,
        data_source_uri=data_source_uri,
    )


def inventory_resources(zip_path: Path) -> tuple[dict[str, bytes], dict[str, Resource]]:
    files: dict[str, bytes] = {}
    resources: dict[str, Resource] = {}
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            if name.endswith("/"):
                continue
            payload = archive.read(name)
            files[name] = payload
            if name.startswith("resources/") and name.endswith(".xml"):
                text = decode_bytes(payload)
                if text is None:
                    continue
                parsed = parse_resource(name, text)
                if parsed is not None:
                    resources[name] = parsed
    return files, resources


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


def folder_xml(name: str, label: str, parent_uri: str, subfolders: list[str], resources: list[str]) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<folder exportedWithPermissions="true">',
        f"    <parent>{parent_uri}</parent>",
        f"    <name>{name}</name>",
        f"    <label>{label}</label>",
    ]
    for f in sorted(subfolders):
        lines.append(f"    <folder>{f}</folder>")
    for r in sorted(resources):
        lines.append(f"    <resource>{r}</resource>")
    lines.append("</folder>")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).expanduser().resolve()
    outdir = Path(args.outdir).resolve()
    workspace = outdir / "_build"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    files, resources = inventory_resources(source_zip)
    resources_by_uri = {resource.resource_uri: resource for resource in resources.values()}
    adhocs = [r for r in resources.values() if r.root_tag == "adhocDataView"]
    adhoc_by_norm = {normalize_label(a.label): a for a in adhocs}

    selected_reports: list[tuple[Resource, str]] = []
    unmatched: list[str] = []
    for wanted_label, category in SELECTED_REPORTS.items():
        key = normalize_label(wanted_label)
        report = adhoc_by_norm.get(key)
        if report is None:
            unmatched.append(wanted_label)
            continue
        selected_reports.append((report, category))

    if unmatched:
        # fallback with aliases
        still_unmatched = []
        selected_norms = {normalize_label(r.label) for r, _ in selected_reports}
        for missing in unmatched:
            alias = LABEL_ALIASES.get(missing)
            if alias and normalize_label(alias) in adhoc_by_norm:
                report = adhoc_by_norm[normalize_label(alias)]
                if normalize_label(report.label) not in selected_norms:
                    selected_reports.append((report, SELECTED_REPORTS[missing]))
                    selected_norms.add(normalize_label(report.label))
            else:
                still_unmatched.append(missing)
        unmatched = still_unmatched

    if unmatched:
        raise SystemExit(f"Unable to match selected reports: {unmatched}")

    selected_domains: dict[str, Resource] = {}
    domain_category: dict[str, str] = {}
    for report, _ in selected_reports:
        if not report.data_source_uri or report.data_source_uri not in resources_by_uri:
            raise SystemExit(f"Report missing domain reference: {report.label}")
        selected_domains[report.data_source_uri] = resources_by_uri[report.data_source_uri]
    for report, category in selected_reports:
        if report.data_source_uri and report.data_source_uri not in domain_category:
            domain_category[report.data_source_uri] = category

    included_files: dict[str, bytes] = {}
    audit_reports: list[dict[str, str]] = []
    path_remap: list[tuple[str, str]] = []

    # include datasource resource
    for ds_member in (DATASOURCE_FOLDER_MEMBER, DATASOURCE_RESOURCE_MEMBER):
        payload = files.get(ds_member)
        if payload is None:
            raise SystemExit(f"Missing datasource member in source zip: {ds_member}")
        included_files[ds_member] = payload

    # include selected report trees + selected domains trees
    for report, _ in selected_reports:
        included_files.update(collect_tree_members(files, report.rel_path))
    for domain in selected_domains.values():
        included_files.update(collect_tree_members(files, domain.rel_path))

    # rewrite maps
    replace_pairs: list[tuple[str, str]] = []
    # move selected domains into the same category folder as their primary report
    for domain in selected_domains.values():
        old_domain_uri = domain.resource_uri
        dom_uri = domain.resource_uri
        dom_category = domain_category.get(dom_uri, "Shared_Domains")
        new_domain_folder = f"{ADD_ONS_ROOT_URI}/{dom_category}"
        new_domain_uri = f"{new_domain_folder}/{domain.name}"
        replace_pairs.append((old_domain_uri, new_domain_uri))
        old_domain_folder = domain.folder_uri
        replace_pairs.append((old_domain_folder, new_domain_folder))
        replace_pairs.append((f"{old_domain_folder}/{domain.name}_files", f"{new_domain_folder}/{domain.name}_files"))

    # move selected reports into category folders
    for report, category in selected_reports:
        old_report_uri = report.resource_uri
        new_folder = f"{ADD_ONS_ROOT_URI}/{category}"
        new_report_uri = f"{new_folder}/{report.name}"
        replace_pairs.append((old_report_uri, new_report_uri))
        replace_pairs.append((report.folder_uri, new_folder))
        replace_pairs.append((f"{report.folder_uri}/{report.name}_files", f"{new_folder}/{report.name}_files"))
        audit_reports.append(
            {
                "label": report.label,
                "source_resource_uri": old_report_uri,
                "target_resource_uri": new_report_uri,
                "category": category,
                "source_domain_uri": report.data_source_uri or "",
                "target_domain_uri": next(
                    (
                        new
                        for old, new in replace_pairs
                        if old == (report.data_source_uri or "")
                    ),
                    report.data_source_uri or "",
                ),
            }
        )
        # physical member path remap for report XML and its companion _files tree
        old_member_xml = report.rel_path
        old_member_prefix = old_member_xml[:-4] + "_files/"
        new_member_base = (
            "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
            f"{ADD_ONS_ROOT_NAME}/{category}/{report.name}"
        )
        new_member_xml = new_member_base + ".xml"
        new_member_prefix = new_member_base + "_files/"
        path_remap.append((old_member_xml, new_member_xml))
        path_remap.append((old_member_prefix, new_member_prefix))

    # physical member path remap for domains (co-located with category)
    for domain in selected_domains.values():
        dom_uri = domain.resource_uri
        dom_category = domain_category.get(dom_uri, "Shared_Domains")
        old_member_xml = domain.rel_path
        old_member_prefix = old_member_xml[:-4] + "_files/"
        new_member_base = (
            "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
            f"{ADD_ONS_ROOT_NAME}/{dom_category}/{domain.name}"
        )
        new_member_xml = new_member_base + ".xml"
        new_member_prefix = new_member_base + "_files/"
        path_remap.append((old_member_xml, new_member_xml))
        path_remap.append((old_member_prefix, new_member_prefix))

    # ensure root standard offering refs are not retained in moved resources
    replace_pairs = sorted(set(replace_pairs), key=lambda x: len(x[0]), reverse=True)

    # write rewritten files
    path_remap = sorted(set(path_remap), key=lambda x: len(x[0]), reverse=True)

    for rel_path, payload in included_files.items():
        target_rel = rel_path
        for old_pref, new_pref in path_remap:
            if target_rel == old_pref:
                target_rel = new_pref
                break
            if target_rel.startswith(old_pref):
                target_rel = new_pref + target_rel[len(old_pref):]
                break
        target_path = workspace / target_rel
        target_path.parent.mkdir(parents=True, exist_ok=True)
        text = decode_bytes(payload)
        if text is None:
            target_path.write_bytes(payload)
            continue
        for old, new in replace_pairs:
            text = text.replace(old, new)
        target_path.write_text(text, encoding="utf-8")

    # build folder metadata for add-ons structure
    folder_children: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"folders": set(), "resources": set()})
    # categories
    for report, category in selected_reports:
        category_uri = f"{ADD_ONS_ROOT_URI}/{category}"
        folder_children[category_uri]["resources"].add(report.name)
        folder_children[ADD_ONS_ROOT_URI]["folders"].add(category)
    for domain in selected_domains.values():
        dom_uri = domain.resource_uri
        dom_category = domain_category.get(dom_uri, "Shared_Domains")
        category_uri = f"{ADD_ONS_ROOT_URI}/{dom_category}"
        folder_children[ADD_ONS_ROOT_URI]["folders"].add(dom_category)
        folder_children[category_uri]["resources"].add(domain.name)

    # write add-ons root folder
    add_ons_root_rel = (
        "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
        f"{ADD_ONS_ROOT_NAME}/.folder.xml"
    )
    (workspace / add_ons_root_rel).parent.mkdir(parents=True, exist_ok=True)
    (workspace / add_ons_root_rel).write_text(
        folder_xml(
            name=ADD_ONS_ROOT_NAME,
            label="Standard Offering Add Ons",
            parent_uri=ORG_REPORT_ROOT,
            subfolders=list(folder_children[ADD_ONS_ROOT_URI]["folders"]),
            resources=[],
        ),
        encoding="utf-8",
    )

    # write category folders
    all_categories = sorted({c for _, c in selected_reports} | set(domain_category.values()))
    for category in all_categories:
        uri = f"{ADD_ONS_ROOT_URI}/{category}"
        rel = (
            "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
            f"{ADD_ONS_ROOT_NAME}/{category}/.folder.xml"
        )
        (workspace / rel).parent.mkdir(parents=True, exist_ok=True)
        (workspace / rel).write_text(
            folder_xml(
                name=category,
                label=category.replace("_", " "),
                parent_uri=ADD_ONS_ROOT_URI,
                subfolders=[],
                resources=list(folder_children[uri]["resources"]),
            ),
            encoding="utf-8",
        )

    # build index.xml using source index shape
    source_index_text = decode_bytes(files["index.xml"])
    if source_index_text is None:
        raise SystemExit("Unable to decode source index.xml")
    source_index = ET.fromstring(source_index_text)
    for module in list(source_index.findall("module")):
        if module.attrib.get("id") != "repositoryResources":
            source_index.remove(module)
    repo_module = source_index.find("module")
    if repo_module is None:
        repo_module = ET.SubElement(source_index, "module", {"id": "repositoryResources"})
    for node in list(repo_module):
        repo_module.remove(node)
    f_node = ET.SubElement(repo_module, "folder")
    f_node.text = ADD_ONS_ROOT_URI
    r_node = ET.SubElement(repo_module, "resource")
    r_node.text = DATASOURCE_RESOURCE_URI
    (workspace / "index.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(source_index, encoding="unicode"),
        encoding="utf-8",
    )

    outdir.mkdir(parents=True, exist_ok=True)
    out_zip = outdir / "Standard_Offering_Add_Ons_import.zip"
    if out_zip.exists():
        out_zip.unlink()
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(workspace).as_posix())

    audit = {
        "source_zip": str(source_zip),
        "output_zip": str(out_zip),
        "root_folder_uri": ADD_ONS_ROOT_URI,
        "report_count": len(selected_reports),
        "domain_count": len(selected_domains),
        "reports": audit_reports,
        "categories": sorted({c for _, c in selected_reports}),
    }
    audit_path = outdir / "standard_offering_add_ons_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    print(f"Built add-ons package: {out_zip}")
    print(f"Audit JSON: {audit_path}")
    print(f"Selected ad hoc reports: {len(selected_reports)}")
    print(f"Selected domains: {len(selected_domains)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

