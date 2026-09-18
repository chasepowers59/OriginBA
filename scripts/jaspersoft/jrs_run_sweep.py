#!/usr/bin/env python3
"""Run everything in a folder and say what loads, what is empty, and what errors.

For an organization (org-scoped login) and a folder, every resource is executed the way the
server itself executes it, and the outcome recorded:

  adhocDataView   the view's own saved query, run through /rest_v2/queryExecutions with the view
                  as the datasource (pageSize=1): ok with a row count, EMPTY (0 rows), or the
                  server's error
  reportUnit      /rest_v2/reports/<uri>.html with the report's defaults: ok, or the error
  dashboard       /rest_v2/dashboardExecutions (the server renders it headless to PDF): ok, or
                  the error; ERR_CONNECTION_REFUSED means the server's own export engine is
                  not reachable, not that the dashboard is broken (test server, 2026-09-18)

Two uses: the smoke test after a promotion, and the before/after of a server upgrade -- run it
on prod today, run it again after the 10.0 upgrade, and diff the two JSON files.

    python3 scripts/jaspersoft/jrs_run_sweep.py --env test --org Fond_Du_Lac \\
        [--folder /SmartCity/Report/Standard_Offering] [--workers 3] [--timeout 240] \\
        [--types view,report,dashboard] --out jaspersoft/sweeps/test_Fond_Du_Lac_<date>.json
    python3 scripts/jaspersoft/jrs_run_sweep.py compare <before.json> <after.json>

For an upgrade, sweep the whole tenant (--folder /SmartCity), every prod org, as close to the
upgrade window as possible and after the same snapshot-refresh wave, so the row counts that
drift are the refresh's and not the upgrade's.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import jrs_repository as jrs  # noqa: E402


def _http(path, method="GET", body=None, ctype=None, accept="application/json", timeout=240):
    url, auth = jrs._cfg()
    req = urllib.request.Request(url + path, data=body, method=method)
    req.add_header("Authorization", auth); req.add_header("Accept", accept)
    if ctype:
        req.add_header("Content-Type", ctype)
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=jrs._ssl_context()) as r:
            return r.status, r.read(), time.time() - t0
    except urllib.error.HTTPError as e:
        return e.code, e.read(), time.time() - t0
    except Exception as e:  # noqa: BLE001 -- a timeout or a dropped connection is an outcome
        return None, repr(e).encode(), time.time() - t0


def _message(body: bytes) -> str:
    t = body.decode(errors="ignore")
    m = re.search(r"<message>(.*?)</message>", t, re.S) or re.search(r'"message"\s*:\s*"((?:[^"\\]|\\.)*)"', t)
    return (m.group(1) if m else t[:300]).strip()[:400]


def _inline_parameters(query: dict) -> dict:
    """The saved query keeps filter values as named parameters (DESCR_1 = ['Error','Complete'])
    that the UI binds at run time; the query-executions service rejects some of those names
    ("conflicts with metadata field"). Substituting each parameter's own expression for its
    reference runs the identical filter without the binding."""
    where = query.get("where") or {}
    params = {p["name"]: p["expression"]["object"] for p in where.get("parameters", []) if "expression" in p}
    if not params:
        return query

    def walk(node):
        if isinstance(node, dict):
            if "variable" in node and node["variable"].get("name") in params:
                return params[node["variable"]["name"]]
            return {k: walk(v) for k, v in node.items()}
        if isinstance(node, list):
            return [walk(v) for v in node]
        return node
    out = json.loads(json.dumps(query))
    out["where"] = {"filterExpression": walk(where["filterExpression"])} if "filterExpression" in where else {}
    return out


def run_view(uri: str, timeout: int) -> dict:
    code, body, dt = _http(f"/rest_v2/resources{urllib.parse.quote(uri)}?expanded=true", timeout=timeout)
    if code != 200:
        return {"outcome": "error", "detail": f"descriptor {code}: {_message(body)}", "seconds": dt}
    d = json.loads(body)
    ds = d.get("dataSource") or {}
    ds_uri = next((v.get("uri") for v in ds.values() if isinstance(v, dict) and v.get("uri")), None)
    if not ds_uri or not d.get("query"):
        return {"outcome": "error", "detail": "no datasource or query in descriptor", "seconds": dt}
    kind = next(iter(d["query"]))
    # the VIEW is the datasource reference, not its domain: the view's own schema carries the
    # calculated fields (DaysOld, DaysSinceLastMeterRead) the query selects; against the domain
    # alone those fields "do not exist in the data source"
    payload = json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": _inline_parameters(d["query"][kind])}).encode()
    code, body, dt2 = _http("/rest_v2/queryExecutions?offset=0&pageSize=1", "POST", payload,
                            f"application/execution.{kind}Query+json", f"application/{kind}Data+json", timeout)
    if code is None:
        return {"outcome": "timeout" if "timed out" in body.decode(errors="ignore") else "error", "detail": _message(body), "seconds": dt + dt2}
    if code != 200:
        return {"outcome": "error", "detail": f"{code}: {_message(body)}", "seconds": dt + dt2, "domain": ds_uri}
    res = json.loads(body)
    rows = res.get("totalCounts")
    if rows is None:  # multiAxis answers differently; count what came back
        ds_ = res.get("dataset") or {}
        rows = len(ds_.get("rows") or ds_.get("data") or []) or (1 if ds_ else 0)
    return {"outcome": "empty" if rows == 0 else "ok", "rows": rows, "seconds": dt + dt2, "domain": ds_uri, "query": kind}


def run_report(uri: str, timeout: int) -> dict:
    code, body, dt = _http(f"/rest_v2/reports{urllib.parse.quote(uri)}.html", accept="text/html", timeout=timeout)
    if code is None:
        return {"outcome": "timeout" if "timed out" in body.decode(errors="ignore") else "error", "detail": _message(body), "seconds": dt}
    if code != 200:
        return {"outcome": "error", "detail": f"{code}: {_message(body)}", "seconds": dt}
    return {"outcome": "ok", "bytes": len(body), "seconds": dt}


def run_dashboard(uri: str, timeout: int) -> dict:
    payload = json.dumps({"uri": uri, "format": "pdf", "width": 1280, "height": 900}).encode()
    code, body, dt = _http("/rest_v2/dashboardExecutions", "POST", payload, "application/json", timeout=timeout)
    if code not in (200, 201, 202):
        return {"outcome": "error", "detail": f"{code}: {_message(body)}", "seconds": dt}
    eid = json.loads(body)["id"]; t0 = time.time()
    while time.time() - t0 < timeout:
        code, body, _ = _http(f"/rest_v2/dashboardExecutions/{eid}/status", timeout=60)
        st = json.loads(body) if body.startswith(b"{") else {}
        if st.get("status") in ("ready", "failed", "error", "cancelled") or code != 200:
            break
        time.sleep(3)
    else:
        return {"outcome": "timeout", "detail": f"still {st.get('status')} after {timeout}s", "seconds": dt + timeout}
    code, out, _ = _http(f"/rest_v2/dashboardExecutions/{eid}/outputResource", accept="application/pdf", timeout=60)
    if out[:4] == b"%PDF":
        return {"outcome": "ok", "bytes": len(out), "seconds": time.time() - t0 + dt}
    msg = _message(out)
    kind = "export-engine" if "ERR_CONNECTION_REFUSED" in msg else "error"
    return {"outcome": kind, "detail": msg, "seconds": time.time() - t0 + dt}


RUNNERS = {"adhocDataView": ("view", run_view), "reportUnit": ("report", run_report), "dashboard": ("dashboard", run_dashboard)}


def sweep(folder: str, types: set[str], workers: int, timeout: int, limit: int | None) -> list[dict]:
    code, text = jrs._call(f"/rest_v2/resources?folderUri={urllib.parse.quote(folder)}&recursive=true&limit=5000")
    if code != 200:
        sys.exit(f"list {folder}: {code} {text[:200]}")
    items = [i for i in json.loads(text).get("resourceLookup", []) if i["resourceType"] in RUNNERS and RUNNERS[i["resourceType"]][0] in types]
    items = items[:limit] if limit else items
    print(f"{len(items)} resources under {folder}: " + ", ".join(f"{sum(1 for i in items if i['resourceType'] == t)} {n}s" for t, (n, _) in RUNNERS.items()))
    results = []

    def one(i):
        name, fn = RUNNERS[i["resourceType"]]
        r = fn(i["uri"], timeout); r.update({"uri": i["uri"], "type": name, "label": i.get("label", "")})
        flag = {"ok": " ", "empty": "0", "error": "X", "timeout": "T", "export-engine": "E"}[r["outcome"]]
        print(f"  [{flag}] {name:9} {r['seconds']:5.0f}s {i['uri'].split('/Standard_Offering/')[-1][:70]}" + (f"  {r.get('detail', '')[:100]}" if r["outcome"] not in ("ok", "empty") else (f"  rows={r['rows']}" if "rows" in r else "")), flush=True)
        return r
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(one, items):
            results.append(r)
    return results


def compare(before_path: str, after_path: str) -> int:
    """Two sweeps of the same org, before and after a change (an upgrade, a promotion): what
    broke, what healed, what went empty or filled, and what got much slower. Row counts drift
    between refreshes, so a count change alone is reported, never treated as a failure."""
    before, after = json.load(open(before_path)), json.load(open(after_path))
    b = {r["uri"]: r for r in before["results"]}; a = {r["uri"]: r for r in after["results"]}
    print(f"before: {before['server']} {before['taken']} {before['counts']}\nafter:  {after['server']} {after['taken']} {after['counts']}")
    broke = [u for u in a if u in b and b[u]["outcome"] in ("ok", "empty") and a[u]["outcome"] in ("error", "timeout")]
    healed = [u for u in a if u in b and b[u]["outcome"] in ("error", "timeout") and a[u]["outcome"] in ("ok", "empty")]
    emptied = [u for u in a if u in b and b[u]["outcome"] == "ok" and a[u]["outcome"] == "empty"]
    filled = [u for u in a if u in b and b[u]["outcome"] == "empty" and a[u]["outcome"] == "ok"]
    gone, new = sorted(set(b) - set(a)), sorted(set(a) - set(b))
    slower = [u for u in a if u in b and a[u]["seconds"] > max(30, 3 * b[u]["seconds"])]
    counts = [(u, b[u].get("rows"), a[u].get("rows")) for u in a if u in b and "rows" in b[u] and "rows" in a[u] and b[u]["rows"] != a[u]["rows"]]
    for title, items in (("BROKE (ran before, errors or times out now)", broke), ("healed", healed), ("went EMPTY", emptied), ("filled", filled),
                         ("missing after", gone), ("new after", new), ("3x slower (and over 30 s)", slower)):
        print(f"\n{title}: {len(items)}")
        for u in items:
            r = a.get(u) or b.get(u); print(f"  {u}" + (f"  -- {r.get('detail', '')[:140]}" if r.get("detail") else "") + (f"  ({b[u]['seconds']:.0f}s -> {a[u]['seconds']:.0f}s)" if u in slower and u in b else ""))
    print(f"\nrow counts changed: {len(counts)} (data drift between refreshes is expected; read these, do not fail on them)")
    for u, x, y in counts[:25]:
        print(f"  {u.rsplit('/', 1)[-1][:60]:60} {x} -> {y}")
    return 1 if broke or gone else 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "compare":
        return compare(sys.argv[2], sys.argv[3])
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", default="test"); ap.add_argument("--org", required=True, help="org-scoped login: the JRS user is re-scoped as user|Org")
    ap.add_argument("--folder", default="/SmartCity/Report/Standard_Offering")
    ap.add_argument("--types", default="view,report,dashboard"); ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--timeout", type=int, default=240); ap.add_argument("--limit", type=int)
    ap.add_argument("--out", required=True, help="JSON results file (a before/after pair diffs by uri)")
    a = ap.parse_args()
    os.environ["JRS_ENV"] = a.env
    base = jrs._env_var("USER").split("|")[0]
    os.environ[f"JRS_{a.env.upper()}_USER"] = f"{base}|{a.org}"
    t0 = time.time()
    results = sweep(a.folder, set(a.types.split(",")), a.workers, a.timeout, a.limit)
    counts = {}
    for r in results:
        counts[r["outcome"]] = counts.get(r["outcome"], 0) + 1
    info = json.loads(jrs._call("/rest_v2/serverInfo")[1])
    out = {"env": a.env, "org": a.org, "folder": a.folder, "server": f"{info.get('version')} {info.get('edition')}",
           "taken": time.strftime("%Y-%m-%dT%H:%M:%S"), "seconds": round(time.time() - t0), "counts": counts, "results": sorted(results, key=lambda r: r["uri"])}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True); pathlib.Path(a.out).write_text(json.dumps(out, indent=1))
    print(f"\n{a.env}/{a.org} {a.folder}: {counts} in {out['seconds']}s -> {a.out}")
    return 0 if not counts.get("error") and not counts.get("timeout") else 1


if __name__ == "__main__":
    raise SystemExit(main())
