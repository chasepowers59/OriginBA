#!/usr/bin/env python3
"""
Verify a built Jaspersoft Standard Offering import ZIP.

Checks:
- exact report count and canonical label coverage
- expected workstream distribution
- every report under Standard_Offering
- every report points to a Standard_Offering datasource URI when applicable
- no duplicate Domain XML resource names
- no leftover Workstreams datasource/report URIs inside selected report XMLs
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
from build_standard_offering_package import CANONICAL_REPORTS, STANDARD_ROOT_URI  # noqa: E402
from build_standard_offering_package import LABEL_OVERRIDES, normalize_label  # noqa: E402
from build_standard_offering_package import DATASOURCE_FOLDER_MEMBER, DATASOURCE_RESOURCE_MEMBER  # noqa: E402
from build_standard_offering_package import DATASOURCE_RESOURCE_URI, ORG_ROOT  # noqa: E402


EXPECTED_WORKSTREAM_COUNTS = {
    "Finance": 13,
    "Billing_and_Rates": 12,
    "Meter_Operations": 18,
    "Cashiering": 14,
    "Common": 8,
    "Customer_Operations": 14,
    "New_Services___Planning": 4,
    "Debt_Management": 12,
    "Field_Operations": 7,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Standard Offering import ZIP.")
    parser.add_argument("--zip", required=True, help="Path to Standard_Offering import zip.")
    parser.add_argument(
        "--output-json",
        help="Optional path to write verification details as JSON.",
    )
    return parser.parse_args()


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def decode_bytes(data: bytes) -> str | None:
    for enc in ("utf-8", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return None


def verify(zip_path: Path) -> dict[str, object]:
    with zipfile.ZipFile(zip_path) as archive:
        names = set(archive.namelist())
        issues: list[str] = []
        warnings: list[str] = []
        report_records: list[dict[str, str]] = []
        domain_names: Counter[str] = Counter()
        domain_paths: defaultdict[str, list[str]] = defaultdict(list)
        workstream_counts: Counter[str] = Counter()

        if "index.xml" not in names:
            issues.append("Missing root index.xml")
        if DATASOURCE_FOLDER_MEMBER not in names:
            issues.append("Missing datasource folder .folder.xml")
        if DATASOURCE_RESOURCE_MEMBER not in names:
            issues.append("Missing datasource resource XML")
        root_folder_path = (
            "resources/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
            "Standard_Offering/.folder.xml"
        )
        if root_folder_path not in names:
            issues.append("Missing Standard_Offering root .folder.xml")

        if "index.xml" in names:
            index_text = decode_bytes(archive.read("index.xml"))
            if index_text is None:
                issues.append("Unreadable index.xml")
            else:
                try:
                    index_root = ET.fromstring(index_text)
                except ET.ParseError:
                    issues.append("index.xml parse failure")
                else:
                    repo_module = next(
                        (module for module in index_root.findall("module") if module.attrib.get("id") == "repositoryResources"),
                        None,
                    )
                    if repo_module is None:
                        issues.append("Missing repositoryResources module in index.xml")
                    else:
                        repo_folders = [(folder.text or "").strip() for folder in repo_module.findall("folder")]
                        repo_resources = [(resource.text or "").strip() for resource in repo_module.findall("resource")]
                        if STANDARD_ROOT_URI not in repo_folders:
                            issues.append(
                                f"index.xml repository resources does not include folder {STANDARD_ROOT_URI}"
                            )
                        if DATASOURCE_RESOURCE_URI not in repo_resources:
                            issues.append(
                                f"index.xml repository resources does not include datasource {DATASOURCE_RESOURCE_URI}"
                            )

        for name in sorted(names):
            if not name.endswith(".xml") or name.endswith(".folder.xml"):
                continue
            text = decode_bytes(archive.read(name))
            if text is None:
                issues.append(f"Unreadable XML payload: {name}")
                continue
            try:
                root = ET.fromstring(text)
            except ET.ParseError:
                issues.append(f"XML parse failure: {name}")
                continue

            root_tag = strip_ns(root.tag)
            folder_uri = (root.findtext("folder") or "").strip()
            label = (root.findtext("label") or "").strip()
            resource_name = (root.findtext("name") or Path(name).stem).strip()

            if root_tag == "semanticLayerDataSource":
                domain_names[resource_name] += 1
                domain_paths[resource_name].append(name)
                if not folder_uri.startswith(STANDARD_ROOT_URI):
                    issues.append(f"Domain folder not under Standard_Offering: {name}")
                domain_ds_uri = (
                    root.findtext(".//dataSource/dataSourceReference/uri")
                    or root.findtext(".//dataSource/uri")
                    or ""
                ).strip()
                if domain_ds_uri != DATASOURCE_RESOURCE_URI:
                    issues.append(
                        f"Domain datasource URI mismatch in {name}: expected {DATASOURCE_RESOURCE_URI}, found {domain_ds_uri or '<empty>'}"
                    )
                continue

            if root_tag not in {"adhocDataView", "reportUnit", "dashboardModelResource"}:
                continue

            if not folder_uri.startswith(STANDARD_ROOT_URI):
                issues.append(f"Report folder not under Standard_Offering: {name}")
                continue

            remainder = folder_uri.removeprefix(STANDARD_ROOT_URI + "/")
            workstream = remainder.split("/", 1)[0] if remainder else ""
            workstream_counts[workstream] += 1
            data_source_uri = (root.findtext(".//dataSource/uri") or "").strip()
            if data_source_uri and not data_source_uri.startswith(STANDARD_ROOT_URI):
                issues.append(f"Report datasource not under Standard_Offering: {name}")

            if "/Workstreams/" in text:
                issues.append(f"Leftover Workstreams reference inside report payload: {name}")

            report_records.append(
                {
                    "label": label,
                    "resource_name": resource_name,
                    "member": name,
                    "root_tag": root_tag,
                    "folder_uri": folder_uri,
                    "data_source_uri": data_source_uri,
                    "workstream": workstream,
                }
            )

        labels = [record["label"] for record in report_records]
        normalized_actual = Counter(normalize_label(label) for label in labels)
        duplicate_report_labels = sorted(
            label for label, count in normalized_actual.items() if count > 1
        )
        if duplicate_report_labels:
            issues.append(f"Duplicate normalized report labels found: {duplicate_report_labels}")

        normalized_expected_map = {
            normalize_label(LABEL_OVERRIDES.get(label, label)): label for label in CANONICAL_REPORTS
        }
        normalized_actual_map = {normalize_label(label): label for label in labels}
        missing_reports = sorted(
            normalized_expected_map[key]
            for key in set(normalized_expected_map) - set(normalized_actual_map)
        )
        extra_reports = sorted(
            normalized_actual_map[key]
            for key in set(normalized_actual_map) - set(normalized_expected_map)
        )
        if missing_reports:
            issues.append(f"Missing canonical reports: {missing_reports}")
        if extra_reports:
            issues.append(f"Unexpected extra reports: {extra_reports}")

        if len(report_records) != len(CANONICAL_REPORTS):
            issues.append(
                f"Report count mismatch: expected {len(CANONICAL_REPORTS)}, found {len(report_records)}"
            )

        for workstream, expected in EXPECTED_WORKSTREAM_COUNTS.items():
            actual = workstream_counts.get(workstream, 0)
            if actual != expected:
                issues.append(
                    f"Workstream count mismatch for {workstream}: expected {expected}, found {actual}"
                )

        duplicate_domain_names = sorted(name for name, count in domain_names.items() if count > 1)
        if duplicate_domain_names:
            issues.append(
                "Duplicate Domain XML names found: "
                + json.dumps({name: domain_paths[name] for name in duplicate_domain_names})
            )

        return {
            "zip": str(zip_path),
            "passed": not issues,
            "issues": issues,
            "warnings": warnings,
            "report_count": len(report_records),
            "domain_count": sum(domain_names.values()),
            "canonical_report_count": len(CANONICAL_REPORTS),
            "workstream_counts": dict(sorted(workstream_counts.items())),
            "reports": report_records,
        }


def main() -> int:
    args = parse_args()
    result = verify(Path(args.zip).expanduser().resolve())

    print(f"Passed: {result['passed']}")
    print(f"Reports: {result['report_count']}")
    print(f"Domains: {result['domain_count']}")
    print("Workstreams:")
    for workstream, count in result["workstream_counts"].items():
        print(f"- {workstream}: {count}")
    if result["issues"]:
        print("Issues:")
        for issue in result["issues"]:
            print(f"- {issue}")

    if args.output_json:
        output_path = Path(args.output_json).expanduser().resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")

    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
