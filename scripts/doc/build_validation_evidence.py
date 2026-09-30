#!/usr/bin/env python3
"""Build per-object QA evidence for a client's DEPLOYED Standard Offering library.

Rows come from the tenant's own repository snapshot (`jaspersoft/inventory/<env>/<Org>/`), not
from `tmp/docs/report_library_catalog.json`: measured 2026-09-22, the catalog's 157 curated names
match only 43 of the 150 views actually deployed to Ellensburg prod, so a catalog-shaped document
would mark real objects absent and omit 94 deployed ones. The snapshot is what the client has.

Execution status comes from a `jrs_run_sweep` results file, matched by URI:

    outcome  -> status  meaning in the document
    ok          PASS    executed and returned rows
    empty       PASS    executed without error, 0 rows for the default filter context
    timeout     NA      invoked, no error, not waited for past the sweep's cap
    error       FAIL    the server or database refused it; the message is the note
    (no result) NA      deployed but outside this execution pass (dashboards, when the
                        sweep ran --types view,report)

Domains and content resources are deployment inventory, not executable rows; they are counted in
the meta block so the document can state what was installed.

    python3 scripts/doc/build_validation_evidence.py --env prod --org Ellensburg \
        --sweep jaspersoft/sweeps/prod_Ellensburg_post_promote_20260921.json --cap 20 \
        --out output/doc/evidence/prod_Ellensburg_evidence.json
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from datetime import datetime

REPO = pathlib.Path(__file__).resolve().parents[2]
SO = "SmartCity/Report/Standard_Offering"

WS_DISPLAY = {
    "Billing_and_Rates": "Billing and Rates",
    "Cashiering": "Cashiering",
    "Common": "Common",
    "Customer_Operations": "Customer Operations",
    "Debt_Management": "Debt Management",
    "Field_Operations": "Field Operations",
    "Finance": "Finance",
    "Meter_Operations": "Meter Operations",
    "New_Services___Planning": "New Services",
}
KIND_DISPLAY = {"adhocDataView": "Ad Hoc View", "reportUnit": "Report", "dashboardModelResource": "Dashboard"}
EXECUTABLE = set(KIND_DISPLAY)


def _rel(p: pathlib.Path) -> str:
    p = p.resolve()
    return str(p.relative_to(REPO)) if p.is_relative_to(REPO) else str(p)


def label(stem: str) -> str:
    """Repository name to reading name: triple underscore was a dash, single underscores spaces."""
    return stem.replace("___", " - ").replace("_", " ").strip()


def resource_kind(path: pathlib.Path) -> str:
    head = path.read_text(errors="ignore")[:400].split("?>", 1)[-1]
    m = re.search(r"<(\w+)[ >]", head)
    return m.group(1) if m else "?"


def inventory(env: str, org: str) -> list[dict]:
    root = REPO / "jaspersoft/inventory" / env / org / "resources" / SO
    if not root.exists():
        raise SystemExit(f"no inventory snapshot at {_rel(root)}; run jrs_inventory.py snapshot first")
    out = []
    for f in sorted(root.rglob("*.xml")):
        if f.name == ".folder.xml":
            continue
        rel = f.relative_to(root).with_suffix("")
        parts = rel.parts
        out.append({
            "uri": f"/{SO}/{rel.as_posix()}",
            "ws": WS_DISPLAY.get(parts[0], label(parts[0])),
            "object": label(parts[1]) if len(parts) > 2 else label(parts[0]),
            "name": label(parts[-1]),
            "kind": resource_kind(f),
        })
    return out


def status_for(r: dict | None, cap: int | None) -> tuple[str, str]:
    if r is None:
        return "NA", "Deployed and present in the library; not included in this execution pass."
    outcome = r.get("outcome")
    secs = r.get("seconds")
    took = f" in {secs:.0f}s" if isinstance(secs, (int, float)) else ""
    if outcome == "ok":
        rows = r.get("rows")
        if isinstance(rows, list):
            rows = rows[-1] if rows else None
        shown = f"; returned {rows:,} rows" if isinstance(rows, int) else ""
        if r.get("bytes"):
            shown = f"; rendered {r['bytes']:,} bytes"
        return "PASS", f"Executed without error{took}{shown}."
    if outcome == "empty":
        return "PASS", (f"Executed without error{took}; 0 rows for the default filter context. "
                        "Confirm against client data before reading this as a gap.")
    if outcome == "timeout":
        capped = f" the {cap}-second" if cap else " the"
        return "NA", (f"Invoked and accepted by the server with no error; still running at{capped} "
                      "sweep cap and not waited for. Re-run with a longer cap to close.")
    return "FAIL", f"{outcome}: {(r.get('detail') or '')[:220]}"


def build(env: str, org: str, sweep_path: pathlib.Path | None, cap: int | None) -> dict:
    sweep = json.loads(sweep_path.read_text()) if sweep_path else {}
    results = {r["uri"]: r for r in sweep.get("results", [])}
    items = inventory(env, org)

    structure: dict[str, dict[str, list[dict]]] = {}
    counts: dict[str, int] = {}
    outcomes: dict[str, int] = {}
    executable = 0
    for it in items:
        if it["kind"] not in EXECUTABLE:
            continue
        executable += 1
        r = results.get(it["uri"])
        status, notes = status_for(r, cap)
        counts[status] = counts.get(status, 0) + 1
        if r:
            outcomes[r["outcome"]] = outcomes.get(r["outcome"], 0) + 1
        else:
            outcomes["not run"] = outcomes.get("not run", 0) + 1
        row = {**it, "kind_label": KIND_DISPLAY[it["kind"]], "status": status, "notes": notes}
        structure.setdefault(it["ws"], {}).setdefault(it["object"], []).append(row)

    supporting: dict[str, int] = {}
    for it in items:
        if it["kind"] not in EXECUTABLE:
            supporting[it["kind"]] = supporting.get(it["kind"], 0) + 1

    swept_not_deployed = sorted(set(results) - {i["uri"] for i in items})
    return {
        "meta": {
            "env": env, "org": org, "folder": f"/{SO}",
            "server": sweep.get("server"), "taken": sweep.get("taken"),
            "sweep_seconds": sweep.get("seconds"), "cap_seconds": cap,
            "sweep_file": _rel(sweep_path) if sweep_path else None,
            "inventory_snapshot": _rel(REPO / "jaspersoft/inventory" / env / org),
            "built": datetime.now().isoformat(timespec="seconds"),
            "deployed_resources": len(items), "executable_objects": executable,
            "counts": counts, "outcomes": outcomes, "supporting": supporting,
            "swept_not_in_snapshot": swept_not_deployed,
        },
        "structure": structure,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True)
    ap.add_argument("--sweep", type=pathlib.Path)
    ap.add_argument("--cap", type=int, help="the sweep's --timeout, quoted in the NA notes")
    ap.add_argument("--out", type=pathlib.Path, required=True)
    a = ap.parse_args()
    ev = build(a.env, a.org, a.sweep, a.cap)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(ev, indent=1))
    m = ev["meta"]
    print(f"{m['org']} {m['env']}: {m['deployed_resources']} deployed resources, "
          f"{m['executable_objects']} executable -> {m['counts']}; outcomes {m['outcomes']}; "
          f"supporting {m['supporting']}; wrote {_rel(a.out)}")
    if m["swept_not_in_snapshot"]:
        print(f"  note: {len(m['swept_not_in_snapshot'])} swept URIs are not in the snapshot (snapshot older than the sweep)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
