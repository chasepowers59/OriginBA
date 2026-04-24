#!/usr/bin/env python3
"""
Verify an add-on native dashboard package that references existing
Standard_Offering Ad Hoc views.
"""

from __future__ import annotations

import argparse
import json
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path


FT_FOLDER_URI = "/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Standard_Offering/Finance/Financial_Transaction"
PUBLIC_TEMPLATE_RE = re.compile(r"/public/templates/[A-Za-z0-9_.-]+")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify a snapshot dashboard package.")
    parser.add_argument("--zip", required=True, help="Path to the dashboard import ZIP.")
    parser.add_argument("--output-json", help="Optional JSON output path.")
    return parser.parse_args()


def decode_bytes(data: bytes) -> str:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Unable to decode file content.")


def strip_namespace(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def verify(zip_path: Path) -> dict[str, object]:
    issues: list[str] = []
    warnings: list[str] = []
    dashboards: list[dict[str, object]] = []

    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        if "index.xml" not in names:
            issues.append("Missing index.xml")
        else:
            index_text = decode_bytes(archive.read("index.xml"))
            root = ET.fromstring(index_text)
            repo_module = next(
                (module for module in root.findall("module") if module.attrib.get("id") == "repositoryResources"),
                None,
            )
            if repo_module is None:
                issues.append("Missing repositoryResources module")
            else:
                folders = [(folder.text or "").strip() for folder in repo_module.findall("folder")]
                if folders != [FT_FOLDER_URI]:
                    issues.append(f"Unexpected index.xml folders: {folders}")

        dashboard_members = [name for name in names if name.endswith(".xml") and not name.endswith(".folder.xml")]
        for name in sorted(dashboard_members):
            text = decode_bytes(archive.read(name))
            if PUBLIC_TEMPLATE_RE.search(text):
                issues.append(f"Public template dependency remains: {name}")
            root = ET.fromstring(text)
            if strip_namespace(root.tag) != "dashboardModelResource":
                continue
            folder = (root.findtext("folder") or "").strip()
            label = (root.findtext("label") or "").strip()
            resources = [(node.text or "").strip() for node in root.findall("resource/uri")]
            if folder != FT_FOLDER_URI:
                issues.append(f"Dashboard folder mismatch in {name}")
            if any(not resource.startswith(FT_FOLDER_URI + "/") for resource in resources):
                issues.append(f"Dashboard references resources outside Financial_Transaction in {name}")
            temp_count = text.count("/temp/")
            if temp_count:
                issues.append(f"Temp resource references remain in {name}")
            dashboards.append(
                {
                    "member": name,
                    "label": label,
                    "folder": folder,
                    "adhoc_resource_count": len(resources),
                }
            )

        expected_sidecars = {
            "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
            "Standard_Offering/Finance/Financial_Transaction/Financial_Operations___Dashboard_files/components.data",
            "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
            "Standard_Offering/Finance/Financial_Transaction/Financial_Operations___Dashboard_files/wiring.data",
            "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
            "Standard_Offering/Finance/Financial_Transaction/Financial_Operations___Dashboard_files/layout",
        }
        missing = sorted(expected_sidecars - names)
        if missing:
            issues.extend([f"Missing dashboard sidecar: {name}" for name in missing])

        if len(dashboards) != 1:
            issues.append(f"Expected exactly 1 dashboardModelResource, found {len(dashboards)}")

    return {
        "zip": str(zip_path),
        "passed": not issues,
        "issues": issues,
        "warnings": warnings,
        "dashboard_count": len(dashboards),
        "dashboards": dashboards,
        "assumption": "Standard_Offering snapshot Ad Hoc views already exist in Origin_DEV.",
    }


def main() -> int:
    args = parse_args()
    result = verify(Path(args.zip).expanduser().resolve())
    print(f"Passed: {result['passed']}")
    print(f"Dashboards: {result['dashboard_count']}")
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
