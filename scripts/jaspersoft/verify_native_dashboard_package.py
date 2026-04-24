#!/usr/bin/env python3
"""
Verify a packaged native Jaspersoft dashboard ZIP.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


DATASOURCE_RESOURCE_URI = "/organizations/organization_1/organizations/Origin_DEV/DataSource/Origin_DEV_DS"
PUBLIC_TEMPLATE_RE = re.compile(r"/public/templates/[A-Za-z0-9_.-]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a packaged native dashboard ZIP.")
    parser.add_argument("--zip", required=True, help="Path to the dashboard import ZIP.")
    parser.add_argument("--output-json", help="Optional JSON output path.")
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


def verify(zip_path: Path) -> dict[str, object]:
    issues: list[str] = []
    warnings: list[str] = []
    dashboards: list[dict[str, object]] = []
    domains: list[dict[str, object]] = []

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        if "index.xml" not in names:
            issues.append("Missing index.xml")
        else:
            index_text = decode_bytes(archive.read("index.xml"))
            if not index_text:
                issues.append("Unreadable index.xml")
            else:
                root = ET.fromstring(index_text)
                repo_module = next(
                    (module for module in root.findall("module") if module.attrib.get("id") == "repositoryResources"),
                    None,
                )
                if repo_module is None:
                    issues.append("Missing repositoryResources module")
                else:
                    folders = [(folder.text or "").strip() for folder in repo_module.findall("folder")]
                    resources = [(resource.text or "").strip() for resource in repo_module.findall("resource")]
                    if len(folders) != 1:
                        warnings.append(f"Expected 1 folder in index.xml, found {len(folders)}")
                    if DATASOURCE_RESOURCE_URI not in resources:
                        issues.append("Datasource resource missing from index.xml")

        for name in sorted(names):
            if not name.endswith(".xml") or name.endswith(".folder.xml"):
                continue
            text = decode_bytes(archive.read(name))
            if text is None:
                issues.append(f"Unreadable XML: {name}")
                continue
            try:
                root = ET.fromstring(text)
            except ET.ParseError:
                issues.append(f"XML parse failure: {name}")
                continue
            tag = strip_namespace(root.tag)

            if PUBLIC_TEMPLATE_RE.search(text):
                issues.append(f"Public template dependency remains: {name}")

            if tag == "dashboardModelResource":
                folder = (root.findtext("folder") or "").strip()
                label = (root.findtext("label") or "").strip()
                dashboards.append(
                    {
                        "member": name,
                        "label": label,
                        "folder": folder,
                        "temp_id_count": text.count("/temp/"),
                    }
                )
            elif tag == "semanticLayerDataSource":
                folder = (root.findtext("folder") or "").strip()
                label = (root.findtext("label") or "").strip()
                ds_uri = (
                    root.findtext(".//dataSource/dataSourceReference/uri")
                    or root.findtext(".//dataSource/uri")
                    or ""
                ).strip()
                if ds_uri != DATASOURCE_RESOURCE_URI:
                    issues.append(f"Domain datasource mismatch in {name}")
                domains.append(
                    {
                        "member": name,
                        "label": label,
                        "folder": folder,
                        "datasource_uri": ds_uri,
                    }
                )

        if len(dashboards) != 1:
            issues.append(f"Expected exactly 1 dashboardModelResource, found {len(dashboards)}")
        if len(domains) != 1:
            issues.append(f"Expected exactly 1 semanticLayerDataSource, found {len(domains)}")

    return {
        "zip": str(zip_path),
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "dashboard_count": len(dashboards),
        "domain_count": len(domains),
        "dashboards": dashboards,
        "domains": domains,
    }


def main() -> int:
    args = parse_args()
    result = verify(Path(args.zip).expanduser().resolve())
    print(f"Passed: {result['passed']}")
    print(f"Dashboards: {result['dashboard_count']}")
    print(f"Domains: {result['domain_count']}")
    if result["issues"]:
        print("Issues:")
        for issue in result["issues"]:
            print(f"- {issue}")
    if result["warnings"]:
        print("Warnings:")
        for warning in result["warnings"]:
            print(f"- {warning}")
    if args.output_json:
        output_path = Path(args.output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
