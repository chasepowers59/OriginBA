#!/usr/bin/env python3
"""
Build governed snapshot explorer metadata for the analytics portal.

Reads Domain XML from domains/exports/manual_imports/ and emits
output/snapshot_explorer_catalog.json with allowlisted dimensions,
measures, filters, and premade report presets.

Usage:
  python3 scripts/build_snapshot_explorer_catalog.py
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from snapshot_explorer_registry import (
    POC_ENABLED,
    PORTAL_SNAPSHOTS,
    RELATED_SNAPSHOTS,
    REQUIRED_DATE_LABELS,
    SCOPE_FILTERS,
    SNAPSHOT_REFRESH_SQL,
    SNAPSHOT_REGISTRY,
    USAGE_GUIDANCE,
    WORKSTREAM_LABELS,
    WORKSTREAM_ORDER,
)
from business_process_registry import BUSINESS_PROCESSES
from snapshot_portal_config import (
    DEFAULT_DATE_PRESETS,
    LARGE_SNAPSHOTS,
    PORTAL_DEFAULT_DATE,
    REPORT_LIBRARY_PACKS,
    WORKSTREAM_FEATURED,
)

sys.path.insert(0, str(ROOT))
from api.snapshot_catalog import is_protected_column  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]
DOMAIN_DIR = ROOT / "domains" / "exports" / "manual_imports"
SQL_SNAPSHOTS_DIR = ROOT / "sql" / "performance" / "snapshots"
OUTPUT_PATH = ROOT / "output" / "snapshot_explorer_catalog.json"
NS = {"sl": "http://www.jaspersoft.com/2007/SL/XMLSchema"}

JAVA_DATE_TYPES = {"java.sql.Timestamp", "java.sql.Date", "java.util.Date"}
JAVA_NUMERIC_TYPES = {"java.math.BigDecimal", "java.lang.Integer", "java.lang.Long", "java.lang.Double"}


@dataclass
class SnapshotSpec:
    table_name: str
    workstream: str
    label: str
    grain: str
    grain_description: str
    summary: str
    use_case: str
    trusted_measures: list[str]
    required_date_field: str
    premade_reports: list[dict[str, Any]] = field(default_factory=list)
    default_dimensions: list[str] = field(default_factory=list)


def _registry_to_spec(table_name: str, meta: dict[str, Any]) -> SnapshotSpec:
    premade = meta.get("premade_reports")
    if premade is None:
        premade = []
    return SnapshotSpec(
        table_name=table_name,
        workstream=meta["workstream"],
        label=meta["label"],
        grain=meta["grain"],
        grain_description=meta["grain_description"],
        summary=meta["summary"],
        use_case=meta["use_case"],
        trusted_measures=meta.get("trusted_measures", []),
        required_date_field=meta["required_date_field"],
        premade_reports=premade,
        default_dimensions=meta.get("default_dimensions", []),
    )


SNAPSHOT_SPECS: dict[str, SnapshotSpec] = {
    name: _registry_to_spec(name, meta) for name, meta in SNAPSHOT_REGISTRY.items()
}


def parse_domain_xml(path: Path) -> tuple[dict[str, dict[str, str]], list[dict[str, Any]]]:
    tree = ET.parse(path)
    root = tree.getroot()
    fields: dict[str, dict[str, str]] = {}
    for field_el in root.findall(".//sl:resources/sl:jdbcTable/sl:fieldList/sl:field", NS):
        field_id = field_el.get("id")
        if not field_id:
            continue
        fields[field_id.upper()] = {
            "id": field_id.upper(),
            "type": field_el.get("type") or "java.lang.String",
        }
    labels: dict[str, str] = {}
    field_groups: list[dict[str, Any]] = []
    for group_el in root.findall(".//sl:itemGroups/sl:itemGroup", NS):
        group_id = group_el.get("id") or ""
        group_label = group_el.get("label") or group_id.replace("_", " ").title()
        group_fields: list[dict[str, str]] = []
        for item in group_el.findall("sl:items/sl:item", NS):
            item_id = item.get("id")
            label = item.get("label")
            if not item_id:
                continue
            upper = item_id.upper()
            if label:
                labels[upper] = label
            if is_protected_column(upper):
                continue
            group_fields.append({"id": upper, "label": label or upper.replace("_", " ").title()})
        if group_fields:
            field_groups.append({"id": group_id, "label": group_label, "fields": group_fields})
    for field_id, meta in fields.items():
        meta["label"] = labels.get(field_id, field_id.replace("_", " ").title())
    return fields, field_groups


def _classify_source_table(table: str, *, driving: str | None, on_clause: str) -> str:
    upper = table.upper()
    if driving and upper == driving:
        return "driving"
    if upper.endswith("_L") or upper.startswith("CI_LOOKUP_VAL"):
        return "lookup"
    if " IN (" in on_clause.upper() or " ft_type_flg " in on_clause.lower():
        return "optional_child"
    return "context"


def parse_refresh_lineage(sql_path: Path) -> dict[str, Any]:
    if not sql_path.exists():
        return {
            "refresh_sql": str(sql_path.relative_to(ROOT)),
            "driving_table": None,
            "source_tables": [],
            "join_paths": [],
            "population_filter": None,
        }

    raw = sql_path.read_text(encoding="utf-8")
    sql = re.sub(r"--[^\n]*", " ", raw)
    from_match = re.search(r"\bFROM\s+cisadm\.(\w+)\s+(\w+)\b", sql, re.I)
    driving = from_match.group(1).upper() if from_match else None
    driving_alias = from_match.group(2) if from_match else None

    where_match = re.search(r"\bWHERE\b(.+?)(?:\bGROUP\b|\bORDER\b|\);|\bCOMMIT\b|$)", sql, re.I | re.S)
    population_filter = re.sub(r"\s+", " ", where_match.group(1)).strip() if where_match else None

    join_paths: list[dict[str, Any]] = []
    join_pattern = re.compile(
        r"\b(?:(LEFT|RIGHT|INNER|FULL)\s+)?JOIN\s+cisadm\.(\w+)\s+(\w+)\s+ON\s+",
        re.I,
    )
    for match in join_pattern.finditer(sql):
        start = match.end()
        tail = sql[start:]
        end = re.search(
            r"\b(?:(?:LEFT|RIGHT|INNER|FULL)\s+)?JOIN\s+cisadm\.|\bWHERE\b",
            tail,
            re.I,
        )
        on_clause = re.sub(r"\s+", " ", tail[: end.start() if end else len(tail)]).strip()
        join_type = (match.group(1) or "INNER").upper()
        table = match.group(2).upper()
        alias = match.group(3)
        role = _classify_source_table(table, driving=driving, on_clause=on_clause)
        join_paths.append(
            {
                "join_type": join_type,
                "table": table,
                "alias": alias,
                "on": on_clause,
                "role": role,
                "from": f"{driving} ({driving_alias})" if driving and driving_alias else driving,
            }
        )

    tables: dict[str, dict[str, str]] = {}
    if driving:
        tables[driving] = {"table": driving, "role": "driving", "alias": driving_alias or ""}
    for join in join_paths:
        if join["table"] not in tables:
            tables[join["table"]] = {
                "table": join["table"],
                "role": join["role"],
                "alias": join["alias"],
            }

    return {
        "refresh_sql": str(sql_path.relative_to(ROOT)),
        "driving_table": driving,
        "driving_alias": driving_alias,
        "source_tables": sorted(tables.values(), key=lambda row: (row["role"] != "driving", row["table"])),
        "join_paths": join_paths,
        "population_filter": population_filter,
    }


def build_data_model(spec: SnapshotSpec, field_groups: list[dict[str, Any]], lineage: dict[str, Any]) -> dict[str, Any]:
    return {
        "snapshot_table": f"CISADM.{spec.table_name}",
        "domain_table": spec.table_name,
        "grain": spec.grain,
        "grain_description": spec.grain_description,
        "grain_preservation": (
            f"Row count stays at {spec.grain_description.lower()}. "
            "Optional child and lookup joins do not multiply the driving population."
        ),
        "trusted_measures": spec.trusted_measures,
        "driving_table": lineage.get("driving_table"),
        "source_tables": lineage.get("source_tables", []),
        "join_paths": lineage.get("join_paths", []),
        "population_filter": lineage.get("population_filter"),
        "refresh_sql": lineage.get("refresh_sql"),
        "field_groups": field_groups,
    }


def classify_field(field_id: str, java_type: str, trusted: list[str]) -> str:
    upper = field_id.upper()
    if upper in {m.upper() for m in trusted}:
        return "measure"
    if java_type in JAVA_DATE_TYPES or upper.endswith(("_DT", "_DTTM", "_DATE")):
        return "date"
    if java_type in JAVA_NUMERIC_TYPES and any(
        token in upper for token in ("AMT", "SQ", "QTY", "DEBT", "HOURS", "MINS", "BALANCE", "COUNT")
    ):
        return "measure"
    if upper.endswith(("_DESC", "_LBL")) or upper.endswith("_FLG") or upper.endswith("_CD"):
        return "dimension"
    if java_type in JAVA_NUMERIC_TYPES:
        return "measure"
    return "dimension"


def resolve_date_field(requested: str, parsed: dict[str, dict[str, str]]) -> str:
    upper = requested.upper()
    if upper in parsed:
        return upper
    for field_id in parsed:
        if field_id.endswith("_DTTM") or field_id.endswith("_DT"):
            return field_id
    return upper


def build_fallback_premade(
    spec: SnapshotSpec,
    dimension_ids: list[str],
) -> list[dict[str, Any]]:
    if spec.premade_reports:
        return spec.premade_reports

    dim_set = set(dimension_ids)
    chosen = [d for d in spec.default_dimensions if d in dim_set]
    if not chosen:
        chosen = [d for d in dimension_ids if d.endswith("_DESC")][:2]
    if not chosen:
        chosen = dimension_ids[:1]

    reports: list[dict[str, Any]] = []
    if chosen:
        reports.append(
            {
                "id": "volume_by_dimension",
                "title": f"Record Count by {chosen[0].replace('_', ' ').title()}",
                "description": f"Number of rows grouped by {chosen[0].replace('_', ' ').lower()}.",
                "dimensions": [chosen[0]],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [],
                "chart_type": "bar",
            }
        )
    if spec.trusted_measures and chosen:
        measure = spec.trusted_measures[0]
        dim = chosen[1] if len(chosen) > 1 else chosen[0]
        reports.append(
            {
                "id": "measure_by_dimension",
                "title": f"Total {measure.replace('_', ' ').title()} by {dim.replace('_', ' ').title()}",
                "description": f"Sum of {measure} grouped for analysis.",
                "dimensions": [dim],
                "measures": [{"field": measure, "agg": "sum"}],
                "filters": [],
                "chart_type": "bar",
            }
        )
    return reports


def build_snapshot_entry(spec: SnapshotSpec) -> dict[str, Any]:
    xml_path = DOMAIN_DIR / f"{spec.table_name}_End_User_Friendly.xml"
    if not xml_path.exists():
        raise FileNotFoundError(f"Missing domain XML: {xml_path}")
    parsed, field_groups = parse_domain_xml(xml_path)
    date_field = resolve_date_field(spec.required_date_field, parsed)

    group_by_field: dict[str, str] = {}
    for group in field_groups:
        for field in group["fields"]:
            group_by_field[field["id"]] = group["label"]

    fields = []
    dimensions = []
    measures = []
    dates = []
    for field_id, meta in sorted(parsed.items()):
        # A protected column must never enter the catalog: the governed query API
        # allow-lists whatever the catalog declares, so declaring one re-opens the
        # door the SQL fence closes (audit H4). api.snapshot_catalog drops them at
        # the allow-list too — this keeps them out of the artifact in the first place.
        if is_protected_column(field_id):
            continue
        role = classify_field(field_id, meta["type"], spec.trusted_measures)
        entry = {
            "id": field_id,
            "label": meta["label"],
            "type": meta["type"],
            "role": role,
            "group": group_by_field.get(field_id),
        }
        fields.append(entry)
        if role == "dimension":
            dimensions.append({"id": field_id, "label": meta["label"]})
        elif role == "measure":
            measures.append(
                {
                    "id": field_id,
                    "label": meta["label"],
                    "aggs": ["sum"] if field_id in spec.trusted_measures else ["sum", "min", "max"],
                }
            )
        elif role == "date":
            dates.append({"id": field_id, "label": meta["label"]})

    measures.insert(0, {"id": "*", "label": "Number of records", "aggs": ["count"]})
    dimension_ids = [d["id"] for d in dimensions]
    premade_reports = build_fallback_premade(spec, dimension_ids)

    refresh_rel = SNAPSHOT_REFRESH_SQL.get(spec.table_name)
    lineage = parse_refresh_lineage(
        SQL_SNAPSHOTS_DIR / refresh_rel if refresh_rel else Path("__missing__")
    )
    data_model = build_data_model(spec, field_groups, lineage)

    return {
        "table_name": spec.table_name,
        "schema": "CISADM",
        "workstream": spec.workstream,
        "workstream_label": WORKSTREAM_LABELS.get(spec.workstream, spec.workstream),
        "label": spec.label,
        "grain": spec.grain,
        "grain_description": spec.grain_description,
        "summary": spec.summary,
        "use_case": spec.use_case,
        "required_date_label": REQUIRED_DATE_LABELS.get(spec.table_name),
        "trusted_measures": spec.trusted_measures,
        "required_date_field": date_field,
        "fields": fields,
        "dimensions": dimensions,
        "measures": measures,
        "date_fields": dates,
        "default_date_field": date_field,
        "premade_reports": premade_reports,
        "scope_filters": SCOPE_FILTERS.get(spec.table_name, []),
        "usage_guidance": USAGE_GUIDANCE.get(spec.table_name),
        "related_snapshot": RELATED_SNAPSHOTS.get(spec.table_name),
        "max_rows": 500,
        "portal_enabled": spec.table_name in PORTAL_SNAPSHOTS,
        "poc_enabled": spec.table_name in POC_ENABLED,
        "large_domain": spec.table_name in LARGE_SNAPSHOTS,
        "skip_sample_rows": spec.table_name in LARGE_SNAPSHOTS,
        "default_date_preset": DEFAULT_DATE_PRESETS.get(spec.table_name, PORTAL_DEFAULT_DATE),
        "data_model": data_model,
    }


def _field_ids(snapshot: dict[str, Any]) -> set[str]:
    return {field["id"].upper() for field in snapshot.get("fields", [])}


def _filter_allowed(ids: list[str], allowed: set[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for field_id in ids:
        upper = field_id.upper()
        if upper in allowed and upper not in seen:
            seen.add(upper)
            out.append(field_id)
    return out


def compile_business_processes(snapshots: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, list[str]]]:
    """Build navigation tree and per-snapshot process field guides."""
    process_guides_by_snapshot: dict[str, dict[str, dict[str, Any]]] = {
        snap_id: {} for snap_id in snapshots
    }
    compiled: list[dict[str, Any]] = []

    for process in BUSINESS_PROCESSES:
        reports: list[dict[str, Any]] = []
        for entry in process["entries"]:
            snap_id = entry["snapshot_id"]
            if snap_id not in snapshots:
                continue
            snap = snapshots[snap_id]
            allowed = _field_ids(snap)
            report_id = entry.get("report_id")
            title = entry.get("title")
            if report_id:
                premade = next(
                    (r for r in snap.get("premade_reports", []) if r["id"] == report_id),
                    None,
                )
                if not premade:
                    raise KeyError(f"Unknown report {report_id} on {snap_id} for process {process['id']}")
                title = title or premade["title"]
                reports.append(
                    {
                        "snapshot_id": snap_id,
                        "report_id": report_id,
                        "title": title,
                        "snapshot_label": snap["label"],
                    }
                )
            else:
                title = title or snap["label"]
                reports.append(
                    {
                        "snapshot_id": snap_id,
                        "report_id": None,
                        "title": title,
                        "snapshot_label": snap["label"],
                    }
                )

            guide = {
                "label": process["label"],
                "description": process["description"],
                "dimensions": _filter_allowed(entry.get("dimensions", []), allowed),
                "measures": _filter_allowed(entry.get("measures", ["*"]), allowed),
                "scope_fields": _filter_allowed(entry.get("scope_fields", []), allowed),
                "report_ids": [report_id] if report_id else [],
            }
            existing = process_guides_by_snapshot[snap_id].get(process["id"])
            if existing:
                for key in ("dimensions", "measures", "scope_fields", "report_ids"):
                    merged = list(dict.fromkeys([*existing[key], *guide[key]]))
                    existing[key] = merged
            else:
                process_guides_by_snapshot[snap_id][process["id"]] = guide

        if reports:
            compiled.append(
                {
                    "id": process["id"],
                    "workstream": process["workstream"],
                    "label": process["label"],
                    "description": process["description"],
                    "reports": reports,
                }
            )

    processes_by_workstream: dict[str, list[str]] = {}
    for row in compiled:
        processes_by_workstream.setdefault(row["workstream"], []).append(row["id"])

    return compiled, process_guides_by_snapshot


def main() -> None:
    snapshots = {}
    for name in PORTAL_SNAPSHOTS:
        if name not in SNAPSHOT_SPECS:
            raise KeyError(f"Missing registry entry for {name}")
        snapshots[name] = build_snapshot_entry(SNAPSHOT_SPECS[name])

    business_processes, process_guides_by_snapshot = compile_business_processes(snapshots)
    for snap_id, guides in process_guides_by_snapshot.items():
        if guides:
            snapshots[snap_id]["process_guides"] = guides

    payload = {
        "client": "demo",
        "workstream_order": WORKSTREAM_ORDER,
        "workstream_labels": WORKSTREAM_LABELS,
        "portal_snapshots": PORTAL_SNAPSHOTS,
        "poc_enabled": POC_ENABLED,
        "workstream_featured": WORKSTREAM_FEATURED,
        "report_library_packs": REPORT_LIBRARY_PACKS,
        "business_processes": business_processes,
        "snapshots": snapshots,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(
        f"Wrote {OUTPUT_PATH} ({len(snapshots)} snapshots, "
        f"{len(WORKSTREAM_ORDER)} workstreams, {len(business_processes)} business processes, "
        f"{len(POC_ENABLED)} POC-enabled)"
    )


if __name__ == "__main__":
    main()
