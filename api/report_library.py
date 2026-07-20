"""Build curated utility report library from catalog + portal packs."""

from __future__ import annotations

from typing import Any

from api.snapshot_catalog import CatalogError, load_catalog


def build_report_library() -> dict[str, Any]:
    catalog = load_catalog()
    packs_cfg = catalog.get("report_library_packs") or []
    labels = catalog.get("workstream_labels", {})
    snapshots = catalog.get("snapshots", {})
    packs: list[dict[str, Any]] = []

    for pack in packs_cfg:
        entries: list[dict[str, Any]] = []
        for ref in pack.get("reports") or []:
            snap_id = str(ref.get("snapshot_id", "")).upper()
            report_id = ref.get("report_id")
            snap = snapshots.get(snap_id)
            if not snap or not report_id:
                continue
            premade = next(
                (r for r in snap.get("premade_reports") or [] if r.get("id") == report_id),
                None,
            )
            if not premade:
                continue
            entries.append(
                {
                    "snapshot_id": snap_id,
                    "snapshot_label": snap.get("label", snap_id),
                    "workstream": snap.get("workstream"),
                    "workstream_label": labels.get(snap.get("workstream"), ""),
                    "report_id": report_id,
                    "title": premade.get("title", report_id),
                    "description": premade.get("description", ""),
                    "chart_type": premade.get("chart_type", "bar"),
                    "explore_url": f"/explore/{snap_id}?report={report_id}",
                }
            )
        if entries:
            packs.append(
                {
                    "id": pack.get("id"),
                    "title": pack.get("title"),
                    "description": pack.get("description"),
                    "audience": pack.get("audience"),
                    "report_count": len(entries),
                    "reports": entries,
                }
            )

    return {
        "client": catalog.get("client", "demo"),
        "pack_count": len(packs),
        "report_count": sum(p["report_count"] for p in packs),
        "packs": packs,
    }


def get_report_library() -> dict[str, Any]:
    try:
        return build_report_library()
    except CatalogError as exc:
        return {"client": "demo", "pack_count": 0, "report_count": 0, "packs": [], "error": str(exc)}
