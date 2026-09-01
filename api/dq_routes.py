"""Data-quality findings API — the rules engine served into the portal.

The rules live in the originba_dbt repo (dq_rules/rules.yml -- single source, same
file the CLI runner uses); this route executes them against the requesting tenant's
WAREHOUSE and returns CIS-navigable findings. Rules run on the governed reporting
canvases, so one rule set serves every tenant whose warehouse carries the contract.

Read-only by construction: each rule is a SELECT; the connection is the same
per-tenant warehouse pool every canvas query uses.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Body, Depends

from api.auth import AuthContext, get_auth_context
from api.org_db import require_org_for_data
from api.warehouse_db import warehouse_configured, warehouse_connection

ROOT = Path(__file__).resolve().parent.parent
# Rules resolution order: the sibling originba_dbt checkout is the SOURCE (dev machines),
# and config/dq_rules.yml is the DEPLOY COPY bundled into the container (Render has no
# sibling repo). Refresh the bundled copy whenever dq_rules/rules.yml changes:
#   cp ../originba_dbt/dq_rules/rules.yml config/dq_rules.yml
DEFAULT_RULES = ROOT.parent / "originba_dbt" / "dq_rules" / "rules.yml"
BUNDLED_RULES = ROOT / "config" / "dq_rules.yml"

router = APIRouter(prefix="/dq", tags=["data-quality"])

ROW_CAP = 100
ACK_DIR = ROOT / "data" / "dq_acks"


def _ack_path(org: str) -> Path:
    """One ack file per organization. There is no shared bucket: an orgless caller
    is refused upstream by require_org_for_data (audit C3)."""
    if not org:
        raise ValueError("An organization is required to read or write DQ acks")
    return ACK_DIR / f"{org}.json"


def _load_acks(org: str) -> dict[str, Any]:
    try:
        return json.loads(_ack_path(org).read_text())
    except Exception:  # noqa: BLE001
        return {}


def _save_acks(org: str, acks: dict[str, Any]) -> None:
    ACK_DIR.mkdir(parents=True, exist_ok=True)
    _ack_path(org).write_text(json.dumps(acks, indent=1))


def _refresh_marker(cur) -> str:
    """A value that changes when the warehouse is reloaded/rebuilt.

    load_dttm is the CDC/build watermark every staging view carries; its max moves
    on every refresh, which is EXACTLY the acknowledged-until-next-refresh contract:
    mark a finding done and it stays hidden until new data arrives, then the rule
    re-evaluates it fresh.
    """
    try:
        cur.execute("select max(load_dttm)::text from staging.stg_financial_txn")
        row = cur.fetchone()
        return str(row[0]) if row and row[0] else "none"
    except Exception:  # noqa: BLE001
        return "none"


def _rules_path() -> Path:
    override = os.environ.get("DQ_RULES_PATH")
    if override:
        return Path(override)
    if DEFAULT_RULES.exists():
        return DEFAULT_RULES
    return BUNDLED_RULES


@router.get("/findings")
def dq_findings(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org = require_org_for_data(ctx)
    if not warehouse_configured(org):
        return {"configured": False, "rules": []}
    path = _rules_path()
    if not path.exists():
        return {"configured": True, "rules": [],
                "error": "rules file not found (set DQ_RULES_PATH)"}
    rules = yaml.safe_load(path.read_text())
    out = []
    with warehouse_connection(org) as conn:
        cur = conn.cursor()
        for r in rules:
            entry: dict[str, Any] = {k: r.get(k) for k in
                                     ("id", "object", "severity", "title", "action", "key_column")}
            try:
                cur.execute(r["sql"])
                cols = [d[0] for d in cur.description]
                rows = cur.fetchmany(ROW_CAP + 1)
                entry["columns"] = cols
                entry["rows"] = [[None if v is None else str(v) for v in row]
                                 for row in rows[:ROW_CAP]]
                entry["count"] = len(rows[:ROW_CAP])
                entry["capped"] = len(rows) > ROW_CAP
            except Exception as e:  # noqa: BLE001
                conn.rollback()
                entry["error"] = str(e).splitlines()[0][:200]
                entry["columns"], entry["rows"], entry["count"] = [], [], 0
            out.append(entry)
    # ---- acknowledgements: hidden until the warehouse refreshes -------------
    with warehouse_connection(org) as conn:
        marker = _refresh_marker(conn.cursor())
    acks = _load_acks(org)
    # a marker change means new data arrived: every ack expires and findings
    # re-surface for the next quality pass
    live_acks = {k: v for k, v in acks.items() if v.get("marker") == marker}
    if live_acks != acks:
        _save_acks(org, live_acks)
    for e in out:
        if not e.get("rows"):
            e["acked_rows"] = []
            continue
        # The ack ENTITY is the rule's declared key_column, not blindly column 0:
        # sp_no_installed_device leads with Premise ID, which several service points
        # share -- keying on it made one ack hide every SP at that premise (found
        # during the 2026-08-26 triage: 85 rows produced 64 distinct keys).
        cols = e.get("columns") or []
        key_col = e.get("key_column")
        ki = cols.index(key_col) if key_col in cols else 0
        keep, acked, keep_keys, acked_keys = [], [], [], []
        for row in e["rows"]:
            key = f"{e['id']}|{row[ki]}"
            if key in live_acks:
                acked.append(row); acked_keys.append(key)
            else:
                keep.append(row); keep_keys.append(key)
        e["rows"], e["acked_rows"] = keep, acked
        e["row_keys"], e["acked_row_keys"] = keep_keys, acked_keys
        e["count"] = len(keep)

    sev_rank = {"action": 0, "review": 1, "info": 2}
    out.sort(key=lambda e: (sev_rank.get(e.get("severity"), 9), -e.get("count", 0)))
    return {
        "configured": True,
        "refresh_marker": marker,
        "act_now": sum(e["count"] for e in out if e.get("severity") == "action"),
        "review": sum(e["count"] for e in out if e.get("severity") == "review"),
        "acknowledged": sum(len(e.get("acked_rows") or []) for e in out),
        "rules": out,
    }


@router.post("/ack")
def dq_ack(payload: dict[str, Any] = Body(...),
           ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    """Mark one finding done until the next warehouse refresh."""
    ctx.require_permission("portal:read")
    org = require_org_for_data(ctx)
    key = str(payload.get("key") or "")
    if not key:
        return {"ok": False, "error": "key required"}
    with warehouse_connection(org) as conn:
        marker = _refresh_marker(conn.cursor())
    acks = _load_acks(org)
    acks[key] = {"marker": marker, "by": getattr(ctx, "email", None) or "user"}
    _save_acks(org, acks)
    return {"ok": True}


@router.post("/unack")
def dq_unack(payload: dict[str, Any] = Body(...),
             ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org = require_org_for_data(ctx)
    key = str(payload.get("key") or "")
    acks = _load_acks(org)
    acks.pop(key, None)
    _save_acks(org, acks)
    return {"ok": True}
