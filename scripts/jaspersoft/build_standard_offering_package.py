#!/usr/bin/env python3
"""
Build a Jaspersoft import ZIP containing the SmartCity Standard Offering folder.

The builder:
- reads a full Workstreams export ZIP
- selects the standard-offering report objects by outer report label
- carries the assigned Domain resource for each selected report
- rewrites repository URIs from /Workstreams/... to /Standard_Offering/...
- emits a clean import ZIP plus an audit JSON

The source-of-truth report list below comes from the user's latest 103-report
standard offering document. One meter-operations row count in that document is
internally inconsistent (18 total, but 19 lines listed). This builder excludes
`Measurement - SP Type`. It also excludes `Billed Usage and Amount Charged`
because that item is a dashboard carrying a public-template dependency that is
not wanted in the Standard Offering package. The final packaged count is 102.
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
from typing import Iterable
import xml.etree.ElementTree as ET


ORG_REPORT_ROOT = "/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report"
ORG_ROOT = "/organizations/organization_1/organizations/Origin_DEV"
WORKSTREAMS_ROOT = f"{ORG_REPORT_ROOT}/Workstreams"
STANDARD_ROOT_NAME = "Standard_Offering"
STANDARD_ROOT_URI = f"{ORG_REPORT_ROOT}/{STANDARD_ROOT_NAME}"
DATASOURCE_FOLDER_URI = f"{ORG_ROOT}/DataSource"
DATASOURCE_RESOURCE_URI = f"{DATASOURCE_FOLDER_URI}/Origin_DEV_DS"
DATASOURCE_FOLDER_MEMBER = (
    "resources/organizations/organization_1/organizations/Origin_DEV/DataSource/.folder.xml"
)
DATASOURCE_RESOURCE_MEMBER = (
    "resources/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS.xml"
)

CANONICAL_REPORTS = [
    "General Ledger - Accounts Receivable",
    "General Ledger - Adjustments Review",
    "General Ledger - GL Account and Distribution",
    "General Ledger - Revenue Totals",
    "General Ledger - Write Off Amounts",
    "General Ledger - By Batch Number",
    "Financial Transaction - Bill Cycle Transactions",
    "Financial Transaction - Billed Revenue Trend",
    "Financial Transaction - GL Distribution Status",
    "Financial Transaction - Revenue by Customer Class",
    "Financial Transaction - Total Transactions by Type",
    "Financial Transactions - Service Type FT Summary",
    "Financial Transaction - Payment Account Detail",
    "Billed Amount - by Customer Class",
    "Billed Amount - Amount Billed by Budget Plan",
    "Billed Amount - By Utility Type",
    "Billed Amount - Canceled Segments",
    "Billed Amount - Estimated Segment",
    "Billed Amount - Rebills",
    "Billed Amount - Revenue by Rate Schedule",
    "Billed Usage - Account Level View",
    "Billed Usage - Across Customer Class & UOM",
    "Billed Usage - By SA Type & Class",
    "Billed Usage - Segment Determinant",
    "Billed Usage - Tiered Billed Usage",
    "Measurement - IMD Summary",
    "Measurement - Measurement Conditions",
    "Measurement - Reads and Totals by Cycle",
    "Measurements - Estimated",
    "Measurements - by Service Point ID",
    "Meter Reads - Counts by Component Type",
    "Usage - Account View",
    "Usage - Customer Class and UOM",
    "Usage - Highest Usage Customers",
    "Usage - Premise Consumption",
    "Usage - by Measuring Component ID",
    "Usage Transaction - By SA Type",
    "Usage Transaction - by Subscription Type",
    "Device - Daily Installations",
    "Device - Disconnected Devices / Service Points",
    "Device - Meters Not Recently Read",
    "Asset - In Storage",
    "Asset - Distribution of Installed Assets",
    "Deposit Control - Ending Balances",
    "Deposit Control - Unbalanced Deposit Controls",
    "Tender Control - Unbalanced",
    "Tender Control - Ending Balances",
    "Pay Plan - Health Status",
    "Pay Plan - Recently Canceled Pay Plans",
    "Pay Plan - Active Pay Plans",
    "Pay Plan - Cancel Reason Distribution Trend",
    "Tender - Payment Tender Distribution by Status",
    "Tender - Tender Type Distribution",
    "Payment - Cancel Reasons",
    "Payment - Creation Trends",
    "Payment - Lost Revenue Overview",
    "Payment - Unfrozen Payments",
    "Batch Process - Incomplete Batch Runs",
    "Batch Process - Recent Batches",
    "Bill Segment Exception - Open Bill Segments",
    "To Do - Incomplete Entries",
    "To Do - Unassigned Duration Trend",
    "Usage Transaction Exceptions - Incomplete",
    "VEE Exception - Exception Severity Distribution",
    "VEE Exception - Rules Generating the Most Exceptions",
    "Account Alert - Collections Risk",
    "Customer Contact - Contact Breakdown",
    "Customer Contact - Distribution of Letters Printed",
    "Customer Contact - Monthly Created Contacts",
    "Case - Open Cases by Account",
    "Case - Open Cases by Customer Class",
    "Case - Time in Previous State",
    "Case - Closed Case Outcomes",
    "Case - Average Case Duration",
    "Case - Cases Created by Month",
    "Customer - Critical Care & Safety Report",
    "Premise - Canceled SA by Type",
    "Premise - Not Linked to Service Agreements",
    "Customer - Accounts on Life Support",
    "New Services - Number of New Premises",
    "New Services - New Service Counts",
    "New Services - Premise Growth",
    "New Services - Pending Service Agreements",
    "Collection Process - Arrears by Customer Class",
    "Collection Process - Arrears by Debt Class",
    "Write Offs - Debt Written Off Trend",
    "Write Offs - Average Process Duration",
    "Collection Process - Active Collections",
    "Collection Process - Age of Unpaid Bills",
    "Collection Process - Upcoming Collection Events",
    "SA Snapshot - Aged Debt by Customer Class",
    "SA Snapshot - Arrear Buckets (By Class)",
    "SA Snapshot - Total Amount of Aged Arrears",
    "Severance Process - Active Processes by Class",
    "Write Off Process - Active Write Off Processes",
    "Field Activity - Average Days per Field Task",
    "Field Activity - Cancellations",
    "Field Activity - Upcoming Field Work",
    "Field Activity - Overdue Work Orders",
    "Field Activity - Trends by Task Type",
    "Crew - Incomplete Work Orders",
    "Crew - Completed and Discarded",
]


LABEL_OVERRIDES = {
    "General Ledger - Adjustments Review": "General Ledger - Adjustments Review",
    "General Ledger - By Batch Number": "General Ledger - by Batch Number",
    "Billed Usage and Amount Charged": "Billed Usage and Amount Charged",
    "Measurement - Measurement Conditions": "Measurement - Measurement Conditions Trend",
    "Device - Disconnected Devices / Service Points": "Device - Disconnected Service Points",
    "Bill Segment Exception - Open Bill Segments": "Bill Segment Exceptions - Open Bill Segments",
    "To Do - Unassigned Duration Trend": "To Do - Unassigned Duration Trends",
    "Collection Process - Age of Unpaid Bills": "Collection Process - Age of Un-Paid Bills",
    "Severance Process - Active Processes by Class": "Severance Process - Active Severance Process by Class",
    "Field Activity - Cancellations": "Field Activity - Cancelations",
    "Crew - Completed and Discarded": "Crew - Completed and Discarded Work Orders",
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


@dataclass
class DomainPlacement:
    source: Resource

    @property
    def source_uri(self) -> str:
        return self.source.resource_uri

    @property
    def target_folder_uri(self) -> str:
        return old_to_new_folder_uri(self.source.folder_uri)

    @property
    def target_uri(self) -> str:
        return f"{self.target_folder_uri}/{self.source.name}"

    @property
    def source_rel_path(self) -> str:
        return self.source.rel_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Standard Offering Jaspersoft import ZIP.")
    parser.add_argument("--source-zip", required=True, help="Path to the exported Workstreams ZIP.")
    parser.add_argument(
        "--outdir",
        default="deploy/jaspersoft_standard_offering",
        help="Output directory for the package and audit artifacts.",
    )
    return parser.parse_args()


def normalize_label(value: str) -> str:
    value = value.strip().lower()
    for dash in ("–", "—", "−"):
        value = value.replace(dash, "-")
    value = value.replace("&", " and ")
    value = value.replace("/", " / ")
    value = value.replace("_", " ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def decode_bytes(data: bytes) -> str | None:
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


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
    if root_tag not in {"adhocDataView", "reportUnit", "dashboardModelResource", "semanticLayerDataSource"}:
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


def build_label_index(resources: Iterable[Resource]) -> dict[str, list[Resource]]:
    index: dict[str, list[Resource]] = defaultdict(list)
    for resource in resources:
        if resource.root_tag == "semanticLayerDataSource":
            continue
        key = normalize_label(resource.label or resource.name)
        index[key].append(resource)
    return index


def target_subpath(source_folder_suffix: str) -> str:
    prefix_map = [
        ("Development/Snapshots/Financial_Transaction", "Finance"),
        ("Development/Snapshots/Billed_Usage/Amount_Billed", "Billing_and_Rates/Billed_Amount"),
        ("Development/Snapshots/Billed_Usage/Billed_Usage", "Billing_and_Rates/Billed_Usage"),
        ("Development/Snapshots/Meter_Operations/Measurements", "Meter_Operations/Measurements"),
        ("Development/Snapshots/Meter_Operations/Scalar_Usage", "Meter_Operations/Usage"),
        ("Development/Snapshots/Meter_Operations/Usage_Transactions", "Meter_Operations/Usage_Transactions"),
    ]
    for source_prefix, target_prefix in prefix_map:
        if source_folder_suffix == source_prefix:
            return target_prefix
        if source_folder_suffix.startswith(source_prefix + "/"):
            return target_prefix + "/" + source_folder_suffix.removeprefix(source_prefix + "/")
    if source_folder_suffix == "Development/Snapshots":
        return ""
    if source_folder_suffix.startswith("Development/Snapshots/"):
        return source_folder_suffix.removeprefix("Development/Snapshots/")
    return source_folder_suffix


def old_to_new_folder_uri(folder_uri: str) -> str:
    suffix = folder_uri.removeprefix(f"{WORKSTREAMS_ROOT}/")
    return f"{STANDARD_ROOT_URI}/{target_subpath(suffix)}"


def old_to_new_resource_uri(resource_uri: str) -> str:
    folder_uri, name = resource_uri.rsplit("/", 1)
    return f"{old_to_new_folder_uri(folder_uri)}/{name}"


def old_to_new_resource_path(rel_path: str) -> str:
    prefix = "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/"
    if not rel_path.startswith(prefix):
        return rel_path
    suffix = rel_path.removeprefix(prefix)
    return (
        "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
        f"{STANDARD_ROOT_NAME}/"
        f"{target_subpath(suffix)}"
    )


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


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
    """Remove nested reportUnit wrappers from saved Ad Hoc views.

    These wrappers are used for dashboard/print rendering and often point to
    shared public templates like `/public/templates/actual_size.820.jrxml`.
    The Standard Offering package only needs the Ad Hoc view itself.
    """
    return re.sub(r"\s*<reports>.*?</reports>\s*", "\n", text, flags=re.DOTALL)


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).expanduser().resolve()
    outdir = Path(args.outdir).resolve()
    workspace = outdir / "_build"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)

    files, resources = inventory_resources(source_zip)
    label_index = build_label_index(resources.values())
    resources_by_uri = {resource.resource_uri: resource for resource in resources.values()}

    selected: list[Resource] = []
    unmatched: list[str] = []
    for canonical in CANONICAL_REPORTS:
        desired_label = LABEL_OVERRIDES.get(canonical, canonical)
        hits = label_index.get(normalize_label(desired_label), [])
        if not hits:
            unmatched.append(canonical)
            continue
        if canonical == "General Ledger - By Batch Number":
            chosen = next((hit for hit in hits if hit.root_tag == "adhocDataView"), hits[0])
        else:
            chosen = hits[0]
        selected.append(chosen)

    if unmatched:
        raise SystemExit(f"Unable to match canonical reports: {unmatched}")

    if len(selected) != len(CANONICAL_REPORTS):
        raise SystemExit(f"Expected {len(CANONICAL_REPORTS)} selected reports, got {len(selected)}")

    included_files: dict[str, bytes] = {}
    selected_domain_placements: dict[str, DomainPlacement] = {}
    selected_report_uris: set[str] = set()
    report_audit: list[dict[str, str]] = []
    report_package_data_sources: dict[str, tuple[str, str, str]] = {}
    datasource_included = False

    for report in selected:
        selected_report_uris.add(report.resource_uri)
        report_members = collect_tree_members(files, report.rel_path)
        included_files.update(report_members)
        target_report_folder = old_to_new_folder_uri(report.folder_uri)
        target_data_source_uri = ""
        if report.data_source_uri and report.data_source_uri in resources_by_uri:
            domain = resources_by_uri[report.data_source_uri]
            placement_key = domain.resource_uri
            if placement_key not in selected_domain_placements:
                selected_domain_placements[placement_key] = DomainPlacement(source=domain)
            included_files.update(collect_tree_members(files, domain.rel_path))
            target_data_source_uri = selected_domain_placements[placement_key].target_uri
            for member_name in report_members:
                report_package_data_sources[member_name] = (
                    report.data_source_uri,
                    old_to_new_resource_uri(report.data_source_uri),
                    target_data_source_uri,
                )
        report_audit.append(
            {
                "label": report.label,
                "root_tag": report.root_tag,
                "source_resource_uri": report.resource_uri,
                "source_member": report.rel_path,
                "target_resource_uri": old_to_new_resource_uri(report.resource_uri),
                "target_member": old_to_new_resource_path(report.rel_path),
                "data_source_uri": report.data_source_uri or "",
                "target_data_source_uri": target_data_source_uri,
            }
        )

    datasource_members = {
        DATASOURCE_FOLDER_MEMBER: files.get(DATASOURCE_FOLDER_MEMBER),
        DATASOURCE_RESOURCE_MEMBER: files.get(DATASOURCE_RESOURCE_MEMBER),
    }
    missing_datasource_members = [name for name, payload in datasource_members.items() if payload is None]
    if missing_datasource_members:
        raise SystemExit(
            "Source export is missing required datasource members: "
            f"{missing_datasource_members}"
        )
    for name, payload in datasource_members.items():
        included_files[name] = payload
    datasource_included = True

    # Rewrite and place included files.
    replacement_map: dict[str, str] = {}
    for uri in selected_report_uris:
        replacement_map[uri] = old_to_new_resource_uri(uri)
    for placement in selected_domain_placements.values():
        replacement_map[placement.source_uri] = placement.target_uri
    old_folders: set[str] = set()
    for resource in selected:
        old_folders.add(resource.folder_uri)
        old_folders.add(f"{resource.folder_uri}/{resource.name}_files")
    for placement in selected_domain_placements.values():
        old_folders.add(placement.source.folder_uri)
        old_folders.add(f"{placement.source.folder_uri}/{placement.source.name}_files")
    for folder_uri in old_folders:
        replacement_map[folder_uri] = old_to_new_folder_uri(folder_uri)

    # Also rewrite the Workstreams root into Standard_Offering.
    replacement_map[WORKSTREAMS_ROOT] = STANDARD_ROOT_URI

    rewrite_pairs = sorted(replacement_map.items(), key=lambda item: len(item[0]), reverse=True)
    for rel_path, payload in included_files.items():
        target_rel_path = old_to_new_resource_path(rel_path)
        for placement in selected_domain_placements.values():
            if rel_path == placement.source_rel_path:
                target_rel_path = old_to_new_resource_path(rel_path)
                break
        target_path = workspace / target_rel_path
        ensure_parent(target_path)
        text = decode_bytes(payload)
        if text is None:
            target_path.write_bytes(payload)
            continue
        for old, new in rewrite_pairs:
            text = text.replace(old, new)
        if rel_path in report_package_data_sources:
            source_uri, generic_target_uri, package_target_uri = report_package_data_sources[rel_path]
            text = text.replace(source_uri, package_target_uri)
            text = text.replace(generic_target_uri, package_target_uri)
        if "<adhocDataView" in text and "<reports>" in text:
            text = strip_adhoc_report_wrappers(text)
        target_path.write_text(text, encoding="utf-8")

    # Build folder metadata from selected resources/domains.
    folder_children: dict[str, dict[str, set[str]]] = defaultdict(lambda: {"folders": set(), "resources": set()})
    for resource in selected:
        target_folder = old_to_new_folder_uri(resource.folder_uri)
        folder_children[target_folder]["resources"].add(resource.name)
        parent = str(Path(target_folder).parent).replace("\\", "/")
        folder_children[parent]["folders"].add(Path(target_folder).name)
    for placement in selected_domain_placements.values():
        target_folder = placement.target_folder_uri
        folder_children[target_folder]["resources"].add(placement.source.name)
        parent = str(Path(target_folder).parent).replace("\\", "/")
        folder_children[parent]["folders"].add(Path(target_folder).name)

    # Ensure workstream parents exist.
    for folder_uri in list(folder_children.keys()):
        if folder_uri == STANDARD_ROOT_URI:
            continue
        current = folder_uri
        while current.startswith(STANDARD_ROOT_URI) and current != STANDARD_ROOT_URI:
            parent = str(Path(current).parent).replace("\\", "/")
            folder_children[parent]["folders"].add(Path(current).name)
            current = parent

    for folder_uri, children in folder_children.items():
        if not folder_uri.startswith(STANDARD_ROOT_URI):
            continue
        if folder_uri == STANDARD_ROOT_URI:
            parent_uri = ORG_REPORT_ROOT
            name = STANDARD_ROOT_NAME
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

    # Build root index.xml with repository resources only.
    source_index = ET.fromstring(files["index.xml"].decode("utf-8"))
    for module in list(source_index.findall("module")):
        if module.attrib.get("id") != "repositoryResources":
            source_index.remove(module)
    repo_module = source_index.find("module")
    if repo_module is None:
        repo_module = ET.SubElement(source_index, "module", {"id": "repositoryResources"})
    for folder_elem in list(repo_module.findall("folder")):
        repo_module.remove(folder_elem)
    folder_elem = ET.SubElement(repo_module, "folder")
    folder_elem.text = STANDARD_ROOT_URI
    resource_elem = ET.SubElement(repo_module, "resource")
    resource_elem.text = DATASOURCE_RESOURCE_URI
    index_path = workspace / "index.xml"
    ensure_parent(index_path)
    index_path.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(source_index, encoding="unicode"),
        encoding="utf-8",
    )

    outdir.mkdir(parents=True, exist_ok=True)
    audit = {
        "source_zip": str(source_zip),
        "report_count": len(selected),
        "domain_count": len(selected_domain_placements),
        "datasource_included": datasource_included,
        "datasource_resource_uri": DATASOURCE_RESOURCE_URI,
        "standard_root_uri": STANDARD_ROOT_URI,
        "excluded_from_package": [
            "Measurement - SP Type",
            "Billed Usage and Amount Charged",
        ],
        "reports": report_audit,
    }
    audit_path = outdir / "standard_offering_package_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")

    package_zip = outdir / "Standard_Offering_import.zip"
    if package_zip.exists():
        package_zip.unlink()
    with zipfile.ZipFile(package_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(workspace.rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(workspace).as_posix())

    print(f"Built package: {package_zip}")
    print(f"Audit JSON: {audit_path}")
    print(f"Selected reports: {len(selected)}")
    print(f"Selected domains: {len(selected_domain_placements)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
