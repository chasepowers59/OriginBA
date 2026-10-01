"""Data-quality findings API — the rules engine served into the portal.

The rules live in the originba_dbt repo (dq_rules/rules.yml -- single source, same
file the CLI runner uses); this route executes them against the requesting tenant's
WAREHOUSE and returns CIS-navigable findings. Rules run on the governed reporting
canvases, so one rule set serves every tenant whose warehouse carries the contract.
An Oracle in-database organization (canvases in ORIGINBA_REPORTING inside its own C2M
instance) runs dq_rules/rules.oracle.yml, GENERATED from rules.yml by originba_dbt's
transpiler, never hand-edited.

Read-only by construction: each rule is a SELECT; the connection is the same
per-tenant warehouse pool (Postgres) or Oracle session pool every canvas query uses.
"""
from __future__ import annotations

import copy
import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, Body, Depends

from api.auth import AuthContext, get_auth_context
from api.data_version import data_version
from api.demo_db import execute_query as oracle_query
from api.executive_dashboard import (DATABASE_UNREACHABLE_NOTE, is_missing_relation_error, is_not_connected_error,
                                     is_transient_error)
from api.freshness import built_at, refresh_marker
from api.org_db import require_org_for_data
from api.snapshot_catalog import org_backend
from api.summary_cache import cached
from api.warehouse_db import warehouse_configured, warehouse_connection
from api.row_security import require_unrestricted

ROOT = Path(__file__).resolve().parent.parent
# Rules resolution order: the sibling originba_dbt checkout is the SOURCE (dev machines),
# and config/ holds the DEPLOY COPIES bundled into the container (Render has no sibling
# repo). Refresh both whenever originba_dbt regenerates its rules:
#   cp ../originba_dbt/dq_rules/rules.yml config/dq_rules.yml
#   cp ../originba_dbt/dq_rules/rules.oracle.yml config/dq_rules.oracle.yml
DEFAULT_RULES = ROOT.parent / "originba_dbt" / "dq_rules" / "rules.yml"
BUNDLED_RULES = ROOT / "config" / "dq_rules.yml"
DEFAULT_ORACLE_RULES = DEFAULT_RULES.with_name("rules.oracle.yml")
BUNDLED_ORACLE_RULES = ROOT / "config" / "dq_rules.oracle.yml"

router = APIRouter(prefix="/dq", tags=["data-quality"])

ROW_CAP = 100
# Oracle rules run side by side: serially the 22 took 101 s on Ellensburg over the VPN
# (2026-09-29). Bounded well under the org's 8-session pool, which serves every page.
ORACLE_RULE_WORKERS = 4
# A rule run is a once-per-build job, not an interactive query: at CityCorp (6.2M charge lines)
# two rules full-scan RPT_BILLED_CHARGE side by side and one crossed the 60 s interactive
# ceiling on every run, so nothing was ever kept (measured 2026-10-01: 16-27 s each alone).
ORACLE_RULE_TIMEOUT_MS = 300_000
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


def _rules_path(engine: str) -> Path:
    if engine == "oracle":
        return DEFAULT_ORACLE_RULES if DEFAULT_ORACLE_RULES.exists() else BUNDLED_ORACLE_RULES
    override = os.environ.get("DQ_RULES_PATH")
    if override:
        return Path(override)
    if DEFAULT_RULES.exists():
        return DEFAULT_RULES
    return BUNDLED_RULES


TOTAL_COL = "_dq_total"


def _run_rule(rule: dict[str, Any], run) -> dict[str, Any]:
    """One rule's finding entry; `run(sql)` returns (columns, rows) or raises.

    A failing rule is reported on its own entry and never stops the others.
    """
    entry: dict[str, Any] = {k: rule.get(k) for k in
                             ("id", "object", "severity", "title", "action", "key_column")}
    try:
        # count(*) OVER () rides along with the capped page, so one query
        # answers both "show me some" and "how many are there". Fetching
        # ROW_CAP + 1 rows could only ever say "at least 101", and the
        # headline was summing that: 200 shown for a real backlog of 1,455.
        # Quoted: Oracle refuses an unquoted name starting with "_" (ORA-00911).
        cols, rows = run(f'select t.*, count(*) over () as "{TOTAL_COL}" '
                         f'from ({rule["sql"].rstrip().rstrip(";")}) t')
        total_at = cols.index(TOTAL_COL)
        entry["columns"] = [c for i, c in enumerate(cols) if i != total_at]
        entry["rows"] = [[None if v is None else str(v)
                          for i, v in enumerate(row) if i != total_at]
                         for row in rows[:ROW_CAP]]
        entry["count"] = len(rows[:ROW_CAP])
        entry["total"] = int(rows[0][total_at]) if rows else 0
        entry["capped"] = entry["total"] > ROW_CAP
    except Exception as e:  # noqa: BLE001
        # an exception with no message has no first line; that must not escape the rule
        entry["error"] = (str(e).splitlines() or [type(e).__name__])[0][:200]
        entry["columns"], entry["rows"] = [], []
        entry["count"] = entry["total"] = 0
    return entry


def _finding_total(entry: dict[str, Any]) -> int:
    """How many findings this rule has, not how many fit in the payload."""
    if entry.get("error"):
        return 0
    total = entry.get("total")
    return int(total if total is not None else entry.get("count") or 0)


def summarise_counts(rules: list[dict[str, Any]]) -> dict[str, int]:
    """The headline numbers, from the true finding counts.

    These used to sum the CAPPED row counts, so two rules pinned at the 100-row cap
    reported "200 act now" against a real backlog of 1,455 on Demo 25.4. A worklist that
    under-reports itself reads as a manageable afternoon.
    """
    return {
        "act_now": sum(_finding_total(e) for e in rules if e.get("severity") == "action"),
        "review": sum(_finding_total(e) for e in rules if e.get("severity") == "review"),
    }


def _run_rules(org: str, engine: str, path: Path) -> list[dict[str, Any]]:
    rules = yaml.safe_load(path.read_text())
    if engine == "oracle":
        def run_oracle(sql: str):
            return oracle_query(sql, organization_id=org, max_rows=ROW_CAP + 1,
                                timeout_ms=ORACLE_RULE_TIMEOUT_MS)

        with ThreadPoolExecutor(max_workers=ORACLE_RULE_WORKERS) as pool:
            return list(pool.map(lambda r: _run_rule(r, run_oracle), rules))
    with warehouse_connection(org) as conn:
        cur = conn.cursor()

        def run(sql: str):
            try:
                cur.execute(sql)
            except Exception:
                conn.rollback()   # an aborted transaction would fail every later rule
                raise
            return [d[0] for d in cur.description], cur.fetchmany(ROW_CAP + 1)

        return [_run_rule(r, run) for r in rules]


def rule_results(org: str, engine: str | None = None, path: Path | None = None) -> list[dict[str, Any]] | None:
    """Every rule's findings, kept until the warehouse is rebuilt (the build stamp, 12 h cap):
    ~40 s on Ellensburg. The parity rules also read CISADM, so they can trail it by up to the
    cap. None when the organization is connected but has no warehouse built (every rule
    ORA-00942): the same answer as no warehouse, not a page of errors. A copy is returned;
    acknowledgements are applied to it per request, never to what is kept."""
    engine = engine or org_backend(org)[0]
    path = path or _rules_path(engine)
    out = cached(("dq", org, engine, str(path)), lambda: _run_rules(org, engine, path),
                 # a rule that fails for good is kept; one cut off by a dropped connection or a
                 # timeout (the parity rules full-scan CISADM right after a rebuild) is not
                 keep=lambda res: (any(not e.get("error") for e in res)
                                   and not any(is_transient_error(e.get("error")) for e in res)),
                 version=data_version(org))
    if out and all(is_missing_relation_error(e.get("error")) for e in out):
        return None
    return copy.deepcopy(out)


def warm(org: str) -> None:
    """The cache warmer's entry: build what /dq/findings serves, where it would run the rules."""
    engine = org_backend(org)[0]
    if (engine == "oracle" or warehouse_configured(org)) and _rules_path(engine).exists():
        rule_results(org, engine)


@router.get("/findings")
def dq_findings(ctx: AuthContext = Depends(get_auth_context)) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    require_unrestricted(ctx)   # the rules run their own SQL over whole canvases
    org = require_org_for_data(ctx)
    engine, _catalog = org_backend(org)
    # An Oracle org reaching here has its Oracle connection (require_org_for_data).
    if engine != "oracle" and not warehouse_configured(org):
        return {"configured": False, "rules": []}
    path = _rules_path(engine)
    if not path.exists():
        return {"configured": True, "rules": [],
                "error": "rules file not found (set DQ_RULES_PATH)"}
    out = rule_results(org, engine, path)
    if out is None:
        return {"configured": False, "rules": []}
    if out and all(is_not_connected_error(e.get("error")) for e in out):   # one sentence, not 22 errors
        return {"configured": True, "rules": [], "error": DATABASE_UNREACHABLE_NOTE}
    # ---- acknowledgements: hidden until the warehouse refreshes -------------
    marker = refresh_marker(org, engine)
    acks = _load_acks(org)
    # a marker change means new data arrived: every ack expires and findings
    # re-surface for the next quality pass. An unreadable marker or a dropped connection
    # says nothing about new data, so acks are neither expired nor rewritten then.
    outage = marker == "none" or any(is_not_connected_error(e.get("error")) for e in out)
    live_acks = acks if outage else {k: v for k, v in acks.items() if v.get("marker") == marker}
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
    # Ordered by how much work each rule represents, so the biggest queue leads.
    out.sort(key=lambda e: (sev_rank.get(e.get("severity"), 9), -_finding_total(e)))
    return {
        "configured": True,
        "refresh_marker": marker,
        "built_at": built_at(marker, engine),
        **summarise_counts(out),
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
    marker = refresh_marker(org, org_backend(org)[0])
    if marker == "none":   # an ack tied to no build could never match one again
        return {"ok": False, "error": "The data's build cannot be read right now; try again shortly."}
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
