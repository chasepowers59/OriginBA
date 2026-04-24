#!/usr/bin/env python3
"""
Inventory Jaspersoft artifacts across local files and exported repository ZIPs.

The scanner classifies artifacts such as:
- Domain schema XML
- exported semantic-layer Domains
- Ad Hoc views
- favorites
- repository folders
- JRXML reports and templates
- input-control JSON
- repository export ZIP contents

It also extracts high-value metadata for promotion and report-generation work:
- repository URIs
- datasource aliases
- datasource resource URIs
- package membership
- likely dependencies
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable, Sequence


REPOSITORY_URI_RE = re.compile(r"/organizations/organization_1/organizations/[A-Za-z0-9_./-]+")
DATASOURCE_URI_RE = re.compile(
    r"/organizations/organization_1/organizations/[A-Za-z0-9_./-]+/DataSource/[A-Za-z0-9_.-]+"
)
XML_SUFFIXES = {".xml", ".jrxml"}
JSON_SUFFIXES = {".json"}
ZIP_SUFFIXES = {".zip"}


@dataclass
class ArtifactRecord:
    source_type: str
    container_path: str
    logical_path: str
    artifact_type: str
    artifact_name: str
    root_tag: str | None = None
    repository_uris: list[str] = field(default_factory=list)
    datasource_aliases: list[str] = field(default_factory=list)
    datasource_uris: list[str] = field(default_factory=list)
    file_resources: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inventory Jaspersoft artifacts across local files and export ZIPs."
    )
    parser.add_argument(
        "--roots",
        nargs="+",
        default=[
            "domains",
            "reports",
            "server/input_controls",
            "deploy/jaspersoft_client_promotion",
        ],
        help="Directories or files to scan.",
    )
    parser.add_argument(
        "--output-json",
        help="Optional path to write the full JSON inventory.",
    )
    parser.add_argument(
        "--output-summary-json",
        help="Optional path to write a compact summary JSON.",
    )
    return parser.parse_args()


def strip_namespace(tag: str) -> str:
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def unique_sorted(values: Iterable[str]) -> list[str]:
    return sorted({value for value in values if value})


def safe_read_text(path: Path) -> str | None:
    for encoding in ("utf-8", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
        except OSError:
            return None
    return None


def safe_decode_bytes(data: bytes) -> str | None:
    for encoding in ("utf-8", "latin-1"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def classify_xml_text(text: str, logical_path: str) -> ArtifactRecord:
    root = ET.fromstring(text)
    root_tag = strip_namespace(root.tag)
    record = ArtifactRecord(
        source_type="file",
        container_path="",
        logical_path=logical_path,
        artifact_type="xml_unknown",
        artifact_name=Path(logical_path).stem,
        root_tag=root_tag,
    )

    repository_uris = unique_sorted(REPOSITORY_URI_RE.findall(text))
    datasource_uris = unique_sorted(DATASOURCE_URI_RE.findall(text))
    file_resources: list[str] = []
    datasource_aliases: list[str] = []
    metadata: dict[str, object] = {}

    if root_tag == "schema":
        record.artifact_type = "domain_schema"
        jdbc_sources = root.findall(".//{http://www.jaspersoft.com/2007/SL/XMLSchema}jdbcDataSource")
        datasource_aliases = [
            source.attrib.get("id", "")
            for source in jdbc_sources
            if source.attrib.get("id")
        ]
        item_groups = root.findall(".//{http://www.jaspersoft.com/2007/SL/XMLSchema}itemGroup")
        metadata["item_group_count"] = len(item_groups)
        jdbc_tables = root.findall(".//{http://www.jaspersoft.com/2007/SL/XMLSchema}jdbcTable")
        metadata["jdbc_table_count"] = len(jdbc_tables)

    elif root_tag == "semanticLayerDataSource":
        record.artifact_type = "semantic_layer_domain"
        alias = root.findtext(".//alias")
        if alias:
            datasource_aliases.append(alias.strip())
        metadata["label"] = root.findtext("label")
        metadata["folder"] = root.findtext("folder")

    elif root_tag == "adhocDataView":
        record.artifact_type = "adhoc_view"
        data_source_uri = root.findtext(".//dataSource/uri")
        if data_source_uri:
            datasource_uris.append(data_source_uri.strip())
        metadata["label"] = root.findtext("label")
        metadata["folder"] = root.findtext("folder")

    elif root_tag == "favorite":
        record.artifact_type = "favorite"
        resource_uri = root.findtext("resourceURI")
        if resource_uri:
            repository_uris.append(resource_uri.strip())

    elif root_tag == "folder":
        record.artifact_type = "repository_folder"
        parent = root.findtext("parent")
        name = root.findtext("name")
        metadata["parent"] = parent
        metadata["name"] = name

    elif root_tag == "export":
        record.artifact_type = "export_index"
        metadata["module_ids"] = [module.attrib.get("id", "") for module in root.findall("module")]

    elif root_tag == "favorites":
        record.artifact_type = "favorites_index"

    elif root_tag == "jasperReport":
        record.artifact_type = "jrxml_report"
        query = root.find("queryString")
        if query is not None and "language" in query.attrib:
            metadata["query_language"] = query.attrib["language"]
        properties = {
            prop.attrib.get("name", ""): prop.attrib.get("value", "")
            for prop in root.findall("property")
            if prop.attrib.get("name")
        }
        metadata["properties"] = properties
        for key, value in properties.items():
            if "domainUri" in key or "data.source" in key:
                repository_uris.extend(REPOSITORY_URI_RE.findall(value))
                datasource_uris.extend(DATASOURCE_URI_RE.findall(value))

    else:
        # Generic extraction from repository XML or report-unit-like exports.
        record.artifact_type = {
            "reportUnit": "report_unit",
            "inputControl": "repository_input_control",
            "query": "repository_query",
            "dataType": "repository_data_type",
            "jdbcDataSource": "repository_datasource",
        }.get(root_tag, "xml_unknown")

    for elem in root.iter():
        if strip_namespace(elem.tag) == "localResource":
            data_file = elem.attrib.get("dataFile")
            if data_file:
                file_resources.append(data_file)
        if strip_namespace(elem.tag) == "uri" and elem.text:
            value = elem.text.strip()
            repository_uris.extend(REPOSITORY_URI_RE.findall(value))
            datasource_uris.extend(DATASOURCE_URI_RE.findall(value))
        if strip_namespace(elem.tag) == "name" and record.artifact_name == Path(logical_path).stem and elem.text:
            # prefer explicit repository object name for exported XML
            explicit_name = elem.text.strip()
            if explicit_name:
                record.artifact_name = explicit_name

    record.repository_uris = unique_sorted(repository_uris)
    record.datasource_aliases = unique_sorted(datasource_aliases)
    record.datasource_uris = unique_sorted(datasource_uris)
    record.file_resources = unique_sorted(file_resources)
    record.metadata = metadata
    return record


def classify_json_text(text: str, logical_path: str) -> ArtifactRecord:
    payload = json.loads(text)
    artifact_type = "json_unknown"
    repository_uris: list[str] = []
    datasource_uris: list[str] = []
    datasource_aliases: list[str] = []
    metadata: dict[str, object] = {}

    if isinstance(payload, dict):
        uri = payload.get("uri")
        if isinstance(uri, str):
            repository_uris.extend(REPOSITORY_URI_RE.findall(uri))
            datasource_uris.extend(DATASOURCE_URI_RE.findall(uri))
        label = payload.get("label")
        if isinstance(label, str):
            metadata["label"] = label

        if logical_path.endswith("_input_controls.json") or logical_path.endswith("_input_controls_rest.json"):
            artifact_type = "input_control_json"
            controls = payload.get("controls")
            if isinstance(controls, list):
                metadata["control_count"] = len(controls)
        elif logical_path.endswith(".json"):
            artifact_type = "json_unknown"

    return ArtifactRecord(
        source_type="file",
        container_path="",
        logical_path=logical_path,
        artifact_type=artifact_type,
        artifact_name=Path(logical_path).stem,
        repository_uris=unique_sorted(repository_uris),
        datasource_aliases=unique_sorted(datasource_aliases),
        datasource_uris=unique_sorted(datasource_uris),
        metadata=metadata,
    )


def classify_text_payload(text: str, logical_path: str) -> ArtifactRecord | None:
    suffix = Path(logical_path).suffix.lower()
    if suffix in XML_SUFFIXES:
        try:
            return classify_xml_text(text, logical_path)
        except ET.ParseError:
            return ArtifactRecord(
                source_type="file",
                container_path="",
                logical_path=logical_path,
                artifact_type="xml_parse_error",
                artifact_name=Path(logical_path).stem,
            )
    if suffix in JSON_SUFFIXES:
        try:
            return classify_json_text(text, logical_path)
        except json.JSONDecodeError:
            return ArtifactRecord(
                source_type="file",
                container_path="",
                logical_path=logical_path,
                artifact_type="json_parse_error",
                artifact_name=Path(logical_path).stem,
            )
    return None


def scan_zip(path: Path) -> list[ArtifactRecord]:
    records: list[ArtifactRecord] = []
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        zip_record = ArtifactRecord(
            source_type="zip",
            container_path=str(path),
            logical_path=str(path),
            artifact_type="repository_export_zip",
            artifact_name=path.name,
            metadata={
                "member_count": len(names),
                "xml_member_count": len([name for name in names if name.lower().endswith(".xml")]),
            },
        )
        records.append(zip_record)

        for name in names:
            suffix = Path(name).suffix.lower()
            if suffix not in XML_SUFFIXES | JSON_SUFFIXES:
                continue
            text = safe_decode_bytes(archive.read(name))
            if text is None:
                continue
            record = classify_text_payload(text, name)
            if record is None:
                continue
            record.source_type = "zip_member"
            record.container_path = str(path)
            records.append(record)
    return records


def scan_file(path: Path) -> list[ArtifactRecord]:
    suffix = path.suffix.lower()
    if suffix in ZIP_SUFFIXES:
        return scan_zip(path)

    text = safe_read_text(path)
    if text is None:
        return []
    record = classify_text_payload(text, str(path))
    if record is None:
        return []
    record.container_path = str(path)
    return [record]


def iter_scan_paths(roots: Sequence[str]) -> list[Path]:
    paths: list[Path] = []
    for root_str in roots:
        root = Path(root_str)
        if not root.exists():
            continue
        if root.is_file():
            paths.append(root)
            continue
        for path in root.rglob("*"):
            if path.is_file():
                suffix = path.suffix.lower()
                if suffix in XML_SUFFIXES | JSON_SUFFIXES | ZIP_SUFFIXES:
                    paths.append(path)
    return sorted(set(paths))


def build_summary(records: list[ArtifactRecord]) -> dict[str, object]:
    by_type = Counter(record.artifact_type for record in records)
    by_source = Counter(record.source_type for record in records)
    datasource_aliases = Counter(
        alias for record in records for alias in record.datasource_aliases
    )
    datasource_uris = Counter(
        uri for record in records for uri in record.datasource_uris
    )
    repository_orgs = Counter()
    for record in records:
        for uri in record.repository_uris:
            parts = uri.split("/")
            if len(parts) >= 5:
                repository_orgs[parts[4]] += 1

    zip_membership = defaultdict(int)
    for record in records:
        if record.source_type == "zip_member":
            zip_membership[record.container_path] += 1

    return {
        "artifact_type_counts": dict(sorted(by_type.items())),
        "source_type_counts": dict(sorted(by_source.items())),
        "datasource_alias_counts": dict(sorted(datasource_aliases.items())),
        "datasource_uri_counts": dict(sorted(datasource_uris.items())),
        "repository_org_counts": dict(sorted(repository_orgs.items())),
        "zip_member_counts": dict(sorted(zip_membership.items())),
        "total_records": len(records),
    }


def print_summary(summary: dict[str, object]) -> None:
    print("Artifact Types")
    for key, value in summary["artifact_type_counts"].items():
        print(f"- {key}: {value}")

    print("\nDatasource Aliases")
    for key, value in summary["datasource_alias_counts"].items():
        print(f"- {key}: {value}")

    print("\nRepository Orgs")
    for key, value in summary["repository_org_counts"].items():
        print(f"- {key}: {value}")


def main() -> int:
    args = parse_args()
    scan_paths = iter_scan_paths(args.roots)
    records: list[ArtifactRecord] = []
    for path in scan_paths:
        records.extend(scan_file(path))

    summary = build_summary(records)
    print_summary(summary)

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {
                    "summary": summary,
                    "records": [asdict(record) for record in records],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    if args.output_summary_json:
        output_path = Path(args.output_summary_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
