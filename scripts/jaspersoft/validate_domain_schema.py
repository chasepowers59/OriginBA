#!/usr/bin/env python3
"""Validate Jaspersoft Domain schema.data structure before import."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {"sl": "http://www.jaspersoft.com/2007/SL/XMLSchema"}
JOIN_TREE_CHILD_ORDER = ("fieldList", "filterString", "joinInfo", "joinList", "joinOptions", "query", "tableRefList")
DERIVED_CHILD_ORDER = ("fieldList", "filterString", "query")


def tag_name(element: ET.Element) -> str:
    return element.tag.split("}")[-1] if "}" in element.tag else element.tag


def find_children(root: ET.Element, tag: str) -> list[ET.Element]:
    return [child for child in root if tag_name(child) == tag]


def validate_schema(path: Path) -> list[str]:
    issues: list[str] = []
    text = path.read_text(encoding="utf-8")

    if "/>" in text:
        issues.append("schema contains self-closing tags (JRS exports use explicit close tags)")

    if "<parameters>" in text:
        issues.append("schema contains unsupported <parameters> element")

    if "$P{" in text or ":BIND" in text.lower():
        issues.append("schema SQL contains parameter bind syntax ($P{} / :BIND)")

    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        return [f"XML parse failure: {exc}"]

    if root.get("version") != "1.3":
        issues.append(f"unexpected schema version: {root.get('version')!r}")

    child_tags = [tag_name(child) for child in root]
    for required in ("dataIslands", "dataSources", "resources"):
        if required not in child_tags:
            issues.append(f"missing required top-level element: {required}")
    if "itemGroups" not in child_tags and "items" not in child_tags:
        issues.append("schema must contain itemGroups or items")

    islands = find_children(root, "dataIslands")
    if len(islands) != 1:
        issues.append("expected exactly one dataIslands element")
    else:
        island_ids = {group.get("resourceId") for group in find_children(islands[0], "itemGroup")}
    resources_parent = find_children(root, "resources")
    if len(resources_parent) != 1:
        issues.append("expected exactly one resources element")
        return issues

    resources = resources_parent[0]
    resource_ids: set[str] = set()
    join_tree_ids: set[str] = set()
    flat_table_ids: set[str] = set()
    table_fields: dict[str, set[str]] = {}
    for resource in resources:
        rid = resource.get("id")
        if not rid:
            issues.append("resource element missing id")
            continue
        if rid in resource_ids:
            issues.append(f"duplicate resource id: {rid}")
        resource_ids.add(rid)

        children = [tag_name(child) for child in resource]
        if tag_name(resource) == "jdbcQuery":
            if "query" not in children:
                issues.append(f"jdbcQuery {rid} missing query element")
            if rid.startswith("JoinTree_"):
                issues.append(f"join tree {rid} must be jdbcTable, not jdbcQuery")
                join_tree_ids.add(rid)
            for idx, name in enumerate(children):
                if name in DERIVED_CHILD_ORDER and idx > DERIVED_CHILD_ORDER.index(name):
                    pass
        elif tag_name(resource) == "jdbcTable":
            fields = {
                field.get("id")
                for field in resource.iter()
                if tag_name(field) == "field" and field.get("id")
            }
            table_fields[rid] = fields
            if any(tag_name(child) == "joinInfo" for child in resource):
                join_tree_ids.add(rid)
                for idx, name in enumerate(children):
                    if name == "query":
                        issues.append(f"join tree jdbcTable {rid} must not contain query element")
                ordered = [name for name in children if name in JOIN_TREE_CHILD_ORDER]
                expected = [name for name in JOIN_TREE_CHILD_ORDER if name in ordered]
                if ordered != expected:
                    issues.append(
                        f"join tree {rid} child order invalid: got {ordered}, expected {expected}"
                    )
            else:
                flat_table_ids.add(rid)

    island_targets = join_tree_ids | flat_table_ids
    missing_islands = sorted(island_ids - island_targets)
    if missing_islands:
        issues.append(
            "dataIsland resourceId(s) missing table resource: "
            + ", ".join(missing_islands)
        )

    item_resource_ids: list[str] = []
    for items_parent in [*find_children(root, "itemGroups"), *find_children(root, "items")]:
        for item in items_parent.iter():
            if tag_name(item) != "item":
                continue
            rid = item.get("resourceId")
            if rid:
                item_resource_ids.append(rid)

    join_fields: dict[str, set[str]] = {}
    for resource in resources:
        rid = resource.get("id")
        if rid not in join_tree_ids:
            continue
        join_fields[rid] = table_fields.get(rid, set())

    for item_rid in item_resource_ids:
        if "." not in item_rid:
            issues.append(f"item resourceId missing table prefix: {item_rid}")
            continue
        table_id, remainder = item_rid.split(".", 1)
        if table_id in flat_table_ids:
            fields = table_fields.get(table_id, set())
            if remainder not in fields:
                issues.append(f"item references missing flat-table field: {item_rid}")
            continue
        if table_id not in join_tree_ids:
            issues.append(f"item references unknown table {table_id}: {item_rid}")
            continue
        fields = join_fields.get(table_id, set())
        if remainder not in fields:
            issues.append(f"item references missing join-tree field: {item_rid}")

    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("schema", type=Path, help="Path to schema.data")
    args = parser.parse_args()

    issues = validate_schema(args.schema)
    if issues:
        print(f"FAIL {args.schema}")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print(f"OK {args.schema}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
