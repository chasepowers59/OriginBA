"""Data-quality findings API — the rules engine served into the portal.

The rules live in the originba_dbt repo (dq_rules/rules.yml -- single source, same
file the CLI runner uses); this route executes them against the requesting tenant's
WAREHOUSE and returns CIS-navigable findings. Rules run on the governed reporting
canvases, so one rule set serves every tenant whose warehouse carries the contract.

Read-only by construction: each rule is a SELECT; the connection is the same
per-tenant warehouse pool every canvas query uses.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Depends

from api.auth import AuthContext, get_auth_context
from api.warehouse_db import warehouse_configured, warehouse_connection

ROOT = Path(__file__).resolve().parent.parent
# sibling-checkout default, same convention as the comparison suite's env file
DEFAULT_RULES = ROOT.parent / "originba_dbt" / "dq_rules" / "rules.yml"

router = APIRouter(prefix="/dq", tags=["data-quality"])

ROW_CAP = 100


def _rules_path() -> Path:
    return Path(os.environ.get("DQ_RULES_PATH") or DEFAULT_RULES)


@router.get("/findings")
def dq_findings(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    org = ctx.organization_id
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
                                     ("id", "object", "severity", "title", "action")}
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
    sev_rank = {"action": 0, "review": 1, "info": 2}
    out.sort(key=lambda e: (sev_rank.get(e.get("severity"), 9), -e.get("count", 0)))
    return {
        "configured": True,
        "act_now": sum(e["count"] for e in out if e.get("severity") == "action"),
        "review": sum(e["count"] for e in out if e.get("severity") == "review"),
        "rules": out,
    }
