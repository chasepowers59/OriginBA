"""Data-integrity evidence per canvas: the QA the dbt repo runs against the client's own
database, read here so a figure in the portal can say when it was last proven and against what.

Two proofs, both produced in originba_dbt and read as files (never recomputed here):
  qa_reports/parity_<client>_latest.json           run_source_parity.py -- canvas vs RAW CISADM
                                                    (counts, money totals, flags, labels)
  qa_reports/snapshot_parity_<client>_latest.json  run_snapshot_parity.py -- canvas vs the legacy
                                                    snapshot tables the client's CURRENT Jaspersoft
                                                    views read (CMS_SA_SNAPSHOT, *_RPT_CURR), key by
                                                    key, over rows unchanged since the canvas build
Resolution: ORIGINBA_QA_REPORTS, else the sibling checkout (the dq_routes idiom). A deployment
without the files answers available=False; nothing is inferred from the data itself.

The one judgement made here: a source-parity difference where the source exceeds the canvas
by under 0.2% AND the source run happened after the canvas build is labelled "the source has
changed since the canvas build". Measured 2026-09-15 at Ellensburg: 63 of 63 differences after
six skipped nightlies had exactly that shape, and every exception the snapshot check found was
a row modified after the build (ORA_ROWSCN). A larger gap is reported bare, never excused.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REPORTS = ROOT.parent / "originba_dbt" / "qa_reports"
CLIENTS_EXPORT = ROOT / "config" / "clients.export.json"
STALE_BAND = 0.002
_CANVAS = re.compile(r'\brpt_[a-z0-9_]+', re.IGNORECASE)


def client_for_org(org_id: str) -> str | None:
    """The dbt client id behind a portal organization, from the registry export."""
    if not CLIENTS_EXPORT.exists():
        return None
    for entry in json.loads(CLIENTS_EXPORT.read_text()).get("entries", []):
        if entry.get("portal_org_id") == org_id:
            return entry.get("client_id") or entry.get("id")
    return None


def _reports_dir() -> Path:
    return Path(os.environ.get("ORIGINBA_QA_REPORTS") or DEFAULT_REPORTS)


_cache: dict[Path, tuple[float, dict[str, Any]]] = {}


def _load(name: str) -> dict[str, Any] | None:
    """Read once per file version: every assistant query asks, the files change nightly."""
    path = _reports_dir() / name
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    hit = _cache.get(path)
    if hit and hit[0] == mtime:
        return hit[1]
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    _cache[path] = (mtime, doc)
    return doc


def _reports(org_id: str) -> tuple[dict | None, dict | None]:
    client = client_for_org(org_id)
    if not client:
        return None, None
    return _load(f"parity_{client}_latest.json"), _load(f"snapshot_parity_{client}_latest.json")


def _moved_on(check: dict[str, Any], canvas_as_of: str | None, run_at: str | None) -> bool:
    w, s = check.get("warehouse"), check.get("source")
    if not isinstance(w, (int, float)) or not isinstance(s, (int, float)) or s <= w:
        return False
    if (s - w) / max(abs(s), 1.0) >= STALE_BAND:
        return False
    return bool(canvas_as_of and run_at and run_at > canvas_as_of)


def _source_part(source: dict | None, canvas: str, canvas_as_of: str | None) -> dict[str, Any] | None:
    if not source:
        return None
    rows = [c for c in source.get("checks", []) if c.get("table") == canvas]
    if not rows:
        return None
    run_at = source.get("run_at")
    diffs = []
    for c in rows:
        if c.get("status") == "pass":
            continue
        d = {"check": c["check"], "warehouse": c.get("warehouse"), "source": c.get("source")}
        if _moved_on(c, canvas_as_of, run_at):
            d["likely_cause"] = "the source has changed since the canvas build (rows added after it)"
        diffs.append(d)
    return {"run_at": run_at, "checks": len(rows), "green": len(rows) - len(diffs), "differences": diffs}


def _snapshot_part(snapshot: dict | None, canvas: str) -> dict[str, Any] | None:
    if not snapshot:
        return None
    rows = [c for c in snapshot.get("checks", []) if c.get("canvas", "").split(".")[-1].lower() == canvas]
    if not rows:
        return None
    # a canvas can have two snapshot twins (billed usage at two grains); the tighter one leads
    c = rows[0]
    values = c.get("values", {})
    return {
        "run_at": snapshot.get("run_at"),
        "against": c["snapshot"].split(".")[-1],
        "compared": c.get("compared", 0),
        "newer": c.get("newer", 0),
        "missing": c.get("missing_stable", 0),
        "strict_mismatches": sum(v["mismatch"] for v in values.values() if not v.get("soft")),
        "soft_differences": [{"name": k, "mismatch": v["mismatch"]} for k, v in values.items()
                             if v.get("soft") and v["mismatch"]],
        "ok": bool(c.get("ok")),
        "others": [r["snapshot"].split(".")[-1] for r in rows[1:]],
    }


def _verdict(src: dict | None, snap: dict | None) -> str:
    if src is None and snap is None:
        return "not covered"
    if (src and src["differences"]) or (snap and not snap["ok"]):
        return "differences"
    return "proven"


def canvas_summary(org_id: str, canvas_id: str) -> dict[str, Any]:
    canvas = canvas_id.lower()
    source, snapshot = _reports(org_id)
    if source is None and snapshot is None:
        return {"canvas": canvas, "available": False, "verdict": "unavailable",
                "canvas_as_of": None, "source": None, "snapshot": None}
    as_of = (snapshot or {}).get("canvas_as_of")
    src = _source_part(source, canvas, as_of)
    snap = _snapshot_part(snapshot, canvas)
    return {"canvas": canvas, "available": True, "verdict": _verdict(src, snap),
            "canvas_as_of": as_of, "canvas_age_hours": _age_hours(as_of),
            "source": src, "snapshot": snap}


def _age_hours(as_of: str | None) -> int | None:
    if not as_of:
        return None
    try:
        return int((datetime.now() - datetime.fromisoformat(as_of)).total_seconds() // 3600)
    except ValueError:
        return None


def overview(org_id: str) -> dict[str, Any]:
    source, snapshot = _reports(org_id)
    if source is None and snapshot is None:
        return {"available": False, "client": client_for_org(org_id), "canvases": []}
    names = sorted({c["table"] for c in (source or {}).get("checks", [])}
                   | {c["canvas"].split(".")[-1].lower() for c in (snapshot or {}).get("checks", [])})
    as_of = (snapshot or {}).get("canvas_as_of")
    out = []
    for n in names:
        s = canvas_summary(org_id, n)
        out.append({"canvas": n, "verdict": s["verdict"],
                    "source_green": s["source"]["green"] if s["source"] else None,
                    "source_checks": s["source"]["checks"] if s["source"] else None,
                    "snapshot_against": s["snapshot"]["against"] if s["snapshot"] else None,
                    "snapshot_ok": s["snapshot"]["ok"] if s["snapshot"] else None})
    return {"available": True, "client": client_for_org(org_id), "canvas_as_of": as_of,
            "canvas_age_hours": _age_hours(as_of),
            "source_run_at": (source or {}).get("run_at"), "snapshot_run_at": (snapshot or {}).get("run_at"),
            "canvases": out}


def canvases_read(sql: str) -> list[str]:
    """The canvases a validated statement reads, in order of first mention. The assistant's
    fence already guarantees every table is rpt_*, so the token is the canvas."""
    seen: list[str] = []
    for m in _CANVAS.findall(sql):
        n = m.lower()
        if n not in seen:
            seen.append(n)
    return seen


def for_query(org_id: str, sql: str) -> list[dict[str, Any]]:
    """The compact form a query card shows: one line per canvas the query read."""
    out = []
    for canvas in canvases_read(sql):
        s = canvas_summary(org_id, canvas)
        if not s["available"]:
            return []
        parts = []
        if s["source"]:
            parts.append(f"{s['source']['green']}/{s['source']['checks']} checks vs CISADM")
        if s["snapshot"]:
            sn = s["snapshot"]
            parts.append(f"{sn['compared']:,} rows vs {sn['against']}, "
                         f"{sn['strict_mismatches']:,} differ" + (f", {sn['missing']:,} missing" if sn["missing"] else ""))
        if not parts:
            parts.append("no parity check covers this canvas")
        out.append({"canvas": canvas, "verdict": s["verdict"], "canvas_as_of": s["canvas_as_of"],
                    "summary": "; ".join(parts)})
    return out
