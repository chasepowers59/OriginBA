#!/usr/bin/env python3
"""Which way of running a saved Ad Hoc view by REST agrees with what the UI shows?

The sweep (jrs_run_sweep.py) executes a view's saved query through /rest_v2/queryExecutions with
its filter parameters INLINED. 40 views came back empty at both CityCorp prod and Fond du Lac
test on 2026-09-18, including views that cannot be empty at a live client ("Customers Accounts
with Active Services": SA status 10/20 and a primary name). Suspects: the value-less placeholder
filters the UI ignores (startsWith(x, ''), isAnyValue(x)), the padded CHAR values ('Y   ',
'ACCTENRL  '), or the inlining itself. This runs each suspect view four ways and prints the row
count of each, so the one that matches the UI becomes the sweep's runner:

  inline      parameters substituted into the expression (the sweep today)
  params      parameters passed as the query's own "params" list, untouched
  trimmed     inline, with every string value right-trimmed (the whitespace theory)
  stripped    inline, with value-less filters (startsWith '', isAnyValue, equals '') removed

    python3 scripts/jaspersoft/jrs_view_calibrate.py --env prod --org CityCorp \\
        /SmartCity/Report/Standard_Offering/Customer_Operations/Customer/Customer___Customers_Accounts_with_Active_Services \\
        /SmartCity/Report/Standard_Offering/Billing_and_Rates/Billed_Amount/Billed_Amount___Billing_Activity
Then open the same views in the UI and compare.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import pathlib
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import jrs_repository as jrs  # noqa: E402
import jrs_run_sweep as sw  # noqa: E402

EMPTYISH = ("startsWith", "endsWith", "contains", "equals")


def strip_valueless(node):
    """Drop filter(...) calls whose operand compares to an empty string or is isAnyValue."""
    if isinstance(node, dict):
        if "and" in node or "or" in node:
            key = "and" if "and" in node else "or"
            kept = [strip_valueless(o) for o in node[key].get("operands", [])]
            kept = [k for k in kept if k is not None]
            if not kept:
                return None
            if len(kept) == 1:
                return kept[0]
            return {key: {**node[key], "operands": kept}}
        if "function" in node and node["function"].get("functionName") == "filter":
            inner = node["function"]["operands"][-1] if node["function"].get("operands") else None
            text = json.dumps(inner)
            if inner and ("isAnyValue" in text or ('{"value": ""}' in text and any(f in text for f in EMPTYISH))):
                return None
            return node
        return {k: strip_valueless(v) for k, v in node.items()}
    if isinstance(node, list):
        return [strip_valueless(v) for v in node]
    return node


def trim_strings(node):
    if isinstance(node, dict):
        if "string" in node and isinstance(node["string"], dict) and "value" in node["string"]:
            return {"string": {**node["string"], "value": node["string"]["value"].rstrip()}}
        return {k: trim_strings(v) for k, v in node.items()}
    if isinstance(node, list):
        return [trim_strings(v) for v in node]
    return node


def variants(query: dict) -> dict:
    inline = sw._inline_parameters(query)
    with_params = copy.deepcopy(query)
    if "where" in with_params and "parameters" in with_params["where"]:
        with_params["params"] = with_params["where"].pop("parameters")
    trimmed = trim_strings(inline)
    stripped = copy.deepcopy(inline)
    if stripped.get("where", {}).get("filterExpression"):
        fe = strip_valueless(stripped["where"]["filterExpression"])
        stripped["where"] = {"filterExpression": fe} if fe else {}
    return {"inline": inline, "params": with_params, "trimmed": trimmed, "stripped": stripped}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", default="test"); ap.add_argument("--org", required=True); ap.add_argument("uris", nargs="+")
    a = ap.parse_args()
    os.environ["JRS_ENV"] = a.env; sw._AUTH.header = sw._auth_for(a.org)
    for uri in a.uris:
        code, body, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(uri)}?expanded=true")
        d = json.loads(body); kind = next(iter(d["query"]))
        print(f"\n{uri.rsplit('/', 1)[-1]}  ({kind})")
        for name, q in variants(d["query"][kind]).items():
            payload = json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": q}).encode()
            code, body, dt = sw._http("/rest_v2/queryExecutions?offset=0&pageSize=1", "POST", payload,
                                      f"application/execution.{kind}Query+json", f"application/{kind}Data+json", 120)
            if code == 200:
                res = json.loads(body); rows = res.get("totalCounts")
                if rows is None:
                    ds_ = res.get("dataset") or {}; rows = len(ds_.get("rows") or ds_.get("data") or [])
                print(f"  {name:9} -> rows={rows} ({dt:.0f}s)")
            else:
                print(f"  {name:9} -> {code} {sw._message(body)[:120]} ({dt:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
