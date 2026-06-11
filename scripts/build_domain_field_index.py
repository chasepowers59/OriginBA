#!/usr/bin/env python3
"""
Flatten Jaspersoft Domain schema.data exports into a searchable field index.

Usage:
  python3 scripts/build_domain_field_index.py
"""

from __future__ import annotations

import argparse
import json
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "output" / "domain_field_index.json"
NS = {"sl": "http://www.jaspersoft.com/2007/SL/XMLSchema"}


def _domain_name_from_path(path: Path) -> str:
    parent = path.parent.name
    if parent.endswith("_files"):
        return parent[: -len("_files")]
    return parent


def _parse_schema_data(path: Path) -> List[dict]:
    tree = ET.parse(path)
    root = tree.getroot()
    domain_name = _domain_name_from_path(path)
    domain_uri_hint = str(path).split("SmartCity/Report/")[-1].split("_files/")[0]
    fields: List[dict] = []

    for group in root.findall(".//sl:itemGroup", NS):
        group_id = group.get("id") or ""
        group_label = group.get("label") or group_id
        for item in group.findall("sl:items/sl:item", NS):
            item_id = item.get("id") or ""
            resource_id = item.get("resourceId") or ""
            table_name = group_id
            if "." in resource_id:
                parts = resource_id.split(".")
                if len(parts) >= 2:
                    table_name = parts[-2] if parts[-1] == item_id else parts[1]
            fields.append(
                {
                    "domain_name": domain_name,
                    "domain_uri_hint": domain_uri_hint,
                    "schema_data_path": str(path.relative_to(ROOT)),
                    "item_group_id": group_id,
                    "item_group_label": group_label,
                    "item_id": item_id,
                    "item_label": item.get("label") or item_id,
                    "resource_id": resource_id,
                    "source_table": table_name,
                    "dimension_or_measure": item.get("dimensionOrMeasure"),
                    "default_agg": item.get("defaultAgg"),
                }
            )
    return fields


def build_index(search_roots: List[Path]) -> dict:
    schema_files: List[Path] = []
    for root in search_roots:
        if root.is_file() and root.name == "schema.data":
            schema_files.append(root)
        elif root.is_dir():
            schema_files.extend(sorted(root.rglob("schema.data")))

    seen_paths = set()
    all_fields: List[dict] = []
    domains: Dict[str, dict] = {}

    for path in schema_files:
        key = str(path.resolve())
        if key in seen_paths:
            continue
        seen_paths.add(key)
        try:
            parsed = _parse_schema_data(path)
        except ET.ParseError as exc:
            print(f"[WARN] Skipping unparsable schema.data: {path} ({exc})")
            continue
        domain_name = _domain_name_from_path(path)
        domains[domain_name] = {
            "schema_data_path": str(path.relative_to(ROOT)),
            "field_count": len(parsed),
        }
        all_fields.extend(parsed)

    by_item_id: Dict[str, List[dict]] = {}
    for field in all_fields:
        by_item_id.setdefault(field["item_id"], []).append(field)

    return {
        "domain_count": len(domains),
        "field_count": len(all_fields),
        "domains": domains,
        "fields": all_fields,
        "fields_by_item_id": by_item_id,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out",
        default=str(DEFAULT_OUT),
        help="Output JSON path",
    )
    parser.add_argument(
        "--root",
        action="append",
        default=[
            "domains",
            "deploy/jaspersoft_standard_offering",
            "deploy/standard_offering_add_ons",
        ],
        help="Root directory or schema.data file to scan (repeatable)",
    )
    args = parser.parse_args()

    search_roots = [(ROOT / r).resolve() for r in args.root]
    payload = build_index(search_roots)
    out_path = Path(args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[PASS] Domain field index written: {out_path}")
    print(f"       Domains: {payload['domain_count']} | Fields: {payload['field_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
