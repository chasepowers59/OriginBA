#!/usr/bin/env python3
"""
Audit native Jaspersoft dashboards (dashboardModelResource) inside an export ZIP.

The audit focuses on promotion and packaging risks:
- temp dashlet ids
- public template dependencies
- development snapshot path references
- datasource and domain dependencies
- nested local Ad Hoc / report resources
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from pathlib import Path


REPOSITORY_URI_RE = re.compile(r"/organizations/organization_1/organizations/[A-Za-z0-9_./-]+")
DATASOURCE_URI_RE = re.compile(
    r"/organizations/organization_1/organizations/[A-Za-z0-9_./-]+/DataSource/[A-Za-z0-9_.-]+"
)
PUBLIC_TEMPLATE_RE = re.compile(r"/public/templates/[A-Za-z0-9_.-]+")
TEMP_ID_RE = re.compile(r"/temp/[A-Za-z0-9_./-]+")
DEVELOPMENT_SNAPSHOT_RE = re.compile(r"/Workstreams/Development/Snapshots/[A-Za-z0-9_./-]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit native Jaspersoft dashboards from an export ZIP.")
    parser.add_argument(
        "--source-zip",
        default="/Users/chase/Downloads/Workstream folder.zip",
        help="Path to the exported Jaspersoft ZIP.",
    )
    parser.add_argument(
        "--dashboard-label",
        action="append",
        default=[],
        help="Optional dashboard label filter. Repeat for multiple labels.",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path to write the full audit JSON.",
    )
    return parser.parse_args()


def strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def decode_bytes(data: bytes) -> str | None:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def unique_sorted(values: list[str]) -> list[str]:
    return sorted({value for value in values if value})


def local_resource_type(elem: ET.Element) -> str:
    xsi_type = elem.attrib.get("{http://www.w3.org/2001/XMLSchema-instance}type", "")
    return xsi_type or strip_namespace(elem.tag)


def audit_dashboard(member: str, text: str) -> dict[str, object]:
    root = ET.fromstring(text)
    label = (root.findtext("label") or "").strip()
    name = (root.findtext("name") or Path(member).stem).strip()
    folder = (root.findtext("folder") or "").strip()

    descriptor_types: Counter[str] = Counter()
    descriptor_ids: list[str] = []
    for desc in root.findall("resourceDescriptor"):
        descriptor_types[(desc.findtext("type") or "").strip()] += 1
        descriptor_id = (desc.findtext("id") or "").strip()
        if descriptor_id:
            descriptor_ids.append(descriptor_id)

    local_resources: list[dict[str, str]] = []
    nested_adhoc_resources: list[dict[str, object]] = []
    nested_report_units: list[dict[str, object]] = []
    file_resources: list[str] = []
    domain_uris: list[str] = []
    datasource_uris: list[str] = []

    for local in root.iter():
        if strip_namespace(local.tag) != "localResource":
            continue
        resource_type = local_resource_type(local)
        local_name = (local.findtext("name") or "").strip()
        local_folder = (local.findtext("folder") or "").strip()
        data_file = local.attrib.get("dataFile", "")
        if data_file:
            file_resources.append(data_file)
        local_resources.append(
            {
                "type": resource_type,
                "name": local_name,
                "folder": local_folder,
                "data_file": data_file,
            }
        )

        if resource_type == "adhocDataView":
            adhoc_text = ET.tostring(local, encoding="unicode")
            adhoc_domain_uris = unique_sorted(REPOSITORY_URI_RE.findall(adhoc_text))
            adhoc_datasource_uris = unique_sorted(DATASOURCE_URI_RE.findall(adhoc_text))
            nested_adhoc_resources.append(
                {
                    "name": local_name,
                    "folder": local_folder,
                    "repository_uris": adhoc_domain_uris,
                    "datasource_uris": adhoc_datasource_uris,
                    "input_control_count": len(local.findall(".//inputControl")),
                    "public_template_refs": unique_sorted(PUBLIC_TEMPLATE_RE.findall(adhoc_text)),
                }
            )

        if resource_type == "reportUnit":
            report_text = ET.tostring(local, encoding="unicode")
            nested_report_units.append(
                {
                    "name": local_name,
                    "folder": local_folder,
                    "repository_uris": unique_sorted(REPOSITORY_URI_RE.findall(report_text)),
                    "datasource_uris": unique_sorted(DATASOURCE_URI_RE.findall(report_text)),
                    "public_template_refs": unique_sorted(PUBLIC_TEMPLATE_RE.findall(report_text)),
                }
            )

    domain_uris = unique_sorted(REPOSITORY_URI_RE.findall(text))
    datasource_uris = unique_sorted(DATASOURCE_URI_RE.findall(text))
    public_templates = unique_sorted(PUBLIC_TEMPLATE_RE.findall(text))
    temp_ids = unique_sorted(TEMP_ID_RE.findall(text))
    development_paths = unique_sorted(DEVELOPMENT_SNAPSHOT_RE.findall(text))

    warnings: list[str] = []
    issues: list[str] = []

    if public_templates:
        issues.append("References shared public templates")
    if development_paths:
        warnings.append("References Development/Snapshots paths")
    if temp_ids:
        warnings.append("Contains temp dashlet ids that may need rewrite")
    if not nested_adhoc_resources:
        warnings.append("No nested Ad Hoc dashlets found")

    return {
        "label": label,
        "name": name,
        "folder": folder,
        "member": member,
        "descriptor_type_counts": dict(sorted(descriptor_types.items())),
        "descriptor_id_count": len(descriptor_ids),
        "temp_ids": temp_ids,
        "public_template_refs": public_templates,
        "development_snapshot_refs": development_paths,
        "repository_uris": domain_uris,
        "datasource_uris": datasource_uris,
        "file_resources": unique_sorted(file_resources),
        "local_resource_type_counts": dict(sorted(Counter(item["type"] for item in local_resources).items())),
        "nested_adhoc_count": len(nested_adhoc_resources),
        "nested_report_unit_count": len(nested_report_units),
        "nested_adhoc_resources": nested_adhoc_resources,
        "nested_report_units": nested_report_units,
        "warnings": warnings,
        "issues": issues,
        "package_safe": not issues,
    }


def main() -> int:
    args = parse_args()
    source_zip = Path(args.source_zip).expanduser().resolve()
    if not source_zip.exists():
        print(f"Source ZIP not found: {source_zip}", file=sys.stderr)
        return 1

    filter_labels = {label.strip() for label in args.dashboard_label if label.strip()}
    dashboards: list[dict[str, object]] = []

    with zipfile.ZipFile(source_zip) as archive:
        for member in sorted(archive.namelist()):
            if not member.endswith(".xml"):
                continue
            text = decode_bytes(archive.read(member))
            if text is None:
                continue
            try:
                root = ET.fromstring(text)
            except ET.ParseError:
                continue
            if strip_namespace(root.tag) != "dashboardModelResource":
                continue
            label = (root.findtext("label") or "").strip()
            if filter_labels and label not in filter_labels:
                continue
            dashboards.append(audit_dashboard(member, text))

    result = {
        "source_zip": str(source_zip),
        "dashboard_count": len(dashboards),
        "package_safe_count": sum(1 for item in dashboards if item["package_safe"]),
        "dashboards": dashboards,
    }

    print(f"Dashboards audited: {result['dashboard_count']}")
    for item in dashboards:
        print(
            f"- {item['label']}: safe={item['package_safe']} "
            f"adhoc={item['nested_adhoc_count']} "
            f"temps={len(item['temp_ids'])} "
            f"public_templates={len(item['public_template_refs'])}"
        )

    if args.output_json:
        output_path = Path(args.output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
