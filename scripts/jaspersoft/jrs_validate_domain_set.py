#!/usr/bin/env python3
"""Prove an imported domain set on one org: each domain matches its generated definition, returns its canvas's
own row count, and every field executes. Read-only on the server and on the warehouse.

Three checks per domain under <root>/Domains:
  1. the server's fields (Ad Hoc metadata) equal the generated XML: none missing, extra or relabelled, same folders;
  2. a CountAll on the grain key (the contract's first column; CountAll skips blanks, so any other field can
     under-count) equals select count(*) from the canvas's BI view in the client's warehouse;
  3. every field executes, 40 at a time, one row each; a failing chunk is bisected to the fields that fail;
  4. every client characteristic joined in (domain_extensions) returns a value on exactly as many rows as
     the same derived table joined to the BI view in the warehouse, and on at least one: an all-blank
     characteristic means its join or its code matches nothing.

A dropped link (VPN or server gone) stops the run and names every domain left unchecked, rather than reading a
timeout as a failing domain.

    scripts/jaspersoft/jrs.sh jrs_validate_domain_set.py --env test --org Origin_DEV \\
        --set-dir <generated set> --client ellensburg [--root /SmartCity/Report/Origin_BA_2_0] [--skip-fields]

The warehouse side uses originba_dbt (ORIGINBA_DBT_DIR, default ~/originba_dbt): its reporting contract for the
grain keys and its connect helper for the counts (credentials from ORIGINBA_ENV_FILE, default this repo's .env). Writes backups/jaspersoft/domain_validation/<run>.json.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import time
import urllib.parse
import xml.etree.ElementTree as ET

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]
NS = "{http://www.jaspersoft.com/2007/SL/XMLSchema}"
CHUNK = 40


def generated_items(xml_text: str) -> dict[str, tuple[str, str]]:
    """item id -> (folder label, item label) from a generated domain schema."""
    root = ET.fromstring(xml_text)
    return {it.get("id"): (g.get("label"), it.get("label"))
            for g in root.find(f"{NS}itemGroups").findall(f"{NS}itemGroup") for it in g.iter(f"{NS}item")}


def view_for(file: str) -> str:
    return "RPT_" + file.removeprefix("originba_").removesuffix("_domain.xml").upper() + "_BI"


def differences(want: dict, got: dict) -> dict[str, list[str]]:
    return {"missing": sorted(set(want) - set(got)), "extra": sorted(set(got) - set(want)),
            "relabelled": sorted(k for k in set(want) & set(got) if want[k] != got[k])}


def grain_item(got: dict[str, tuple[str, str]], grain_column: str) -> str | None:
    """The item for the grain key's BI column (ids are <role prefix>_<BI column>)."""
    return next((k for k in got if k.split("_", 1)[-1] == grain_column), None)


def characteristic_checks(xml_text: str) -> list[dict]:
    """Each characteristic item with the derived table it reads and the view column it joins on."""
    root = ET.fromstring(xml_text)
    sql = {q.get("id"): q.find(f"{NS}query").text for q in root.iter(f"{NS}jdbcQuery")}
    joins = {}
    for j in root.iter(f"{NS}join"):
        left, right = (x.strip() for x in j.get("expr").split("=="))
        if right.split(".")[0] in sql:
            joins[right.split(".")[0]] = left.split(".")
    out = []
    for it in root.iter(f"{NS}item"):
        parts = it.get("resourceId").split(".")
        if len(parts) == 3 and parts[1] in joins and parts[2] == "CHAR_VALUE":
            view, col = joins[parts[1]]
            out.append({"item": it.get("id"), "label": it.get("label"), "query": parts[1], "sql": sql[parts[1]],
                        "view": view, "column": col})
    return out


def expected_characteristic_sql(c: dict) -> str:
    return (f"select count(x.CHAR_VALUE) from ORIGINBA_REPORTING.{c['view']} v "
            f"left join ({c['sql']}) x on x.KEY_ID = v.{c['column']}")


def count_from(data: dict) -> int:
    return int(float(data["dataset"]["rows"][0][0]))


def chunks(fields: list[str]):
    for k in range(0, len(fields), CHUNK):
        yield fields[k:k + CHUNK]


class LinkDown(Exception):
    pass


def answer(code: int | None, body: bytes) -> tuple[object, str | None]:
    """(parsed JSON, None) for a usable answer, else (None, why)."""
    text = body.decode(errors="ignore")
    if code is None:
        return None, f"link down: {text}"
    if code != 200 or not text.strip():
        try:
            why = json.loads(text).get("message") or text[:160]
        except ValueError:
            why = text[:160] or "empty response"
        return None, f"HTTP {code}: {why}"
    return json.loads(text), None


def failing_fields(fields: list[str], run) -> list[str]:
    """The fields that fail on their own, by bisection: run(fields) is True when they execute together."""
    if run(fields):
        return []
    if len(fields) == 1:
        return fields
    half = len(fields) // 2
    return failing_fields(fields[:half], run) + failing_fields(fields[half:], run)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True)
    ap.add_argument("--set-dir", type=pathlib.Path, required=True); ap.add_argument("--client", required=True)
    ap.add_argument("--root", default="/SmartCity/Report/Origin_BA_2_0"); ap.add_argument("--skip-fields", action="store_true")
    a = ap.parse_args()
    import jrs_import_domain as one
    import jrs_import_domain_set as ids
    import jrs_promote
    import jrs_run_sweep as sw
    dbt = pathlib.Path(os.environ.get("ORIGINBA_DBT_DIR", pathlib.Path.home() / "originba_dbt"))
    sys.path.insert(0, str(dbt / "scripts"))
    from build_portal_catalog import load_contracts
    from oracle_source_drift import connect
    from bi_names import safe_columns
    contracts = load_contracts(dbt)
    con = connect(os.environ.get("ORIGINBA_ENV_FILE", str(REPO / ".env")), a.client)
    con.call_timeout = 900_000
    cur = con.cursor()
    one._scope(a.env, a.org)

    def call(path, *args, **kw):
        data, why = answer(*sw._http(path, *args, **kw)[:2])
        if why and why.startswith("link down"):
            raise LinkDown(why)
        return data, why

    rows = ids.parse_manifest((a.set_dir / "README.md").read_text())
    by_name = {ids.resource_name(r["label"]): r for r in rows}

    def check(name: str) -> dict:
        r, uri = by_name.get(name), on_server.get(name)
        if not r or not uri:
            print(f"FAIL {name}: {'not on the server' if r else 'on the server, not in the set'}")
            return {"domain": name, "ok": False, "why": "missing" if r else "extra"}
        want = generated_items((a.set_dir / r["file"]).read_text(encoding="utf-8"))
        meta, why = call(f"/rest_v2/domains{urllib.parse.quote(uri)}/metadata", timeout=180)
        if why:
            print(f"FAIL {name}: metadata {why}")
            return {"domain": name, "ok": False, "why": f"metadata {why}"}
        levels = jrs_promote.domain_levels(meta)
        level_of = {i["id"]: lv["id"] for lv in levels for i in lv.get("items", [])}
        got = {i["id"]: (lv.get("label") or lv["id"], i.get("label")) for lv in levels for i in lv.get("items", [])}
        diff = differences(want, got)
        canvas = view_for(r["file"]).removesuffix("_BI").lower()
        cols = [c["name"] for c in contracts[canvas]["columns"]]
        key = grain_item(got, safe_columns(cols)[cols[0]])
        q = {"select": {"aggregations": [{"id": "n", "fieldRef": f"{level_of[key]}.{key}", "aggregateFunction": "CountAll"}]}}
        data, why = call("/rest_v2/queryExecutions", "POST",
                         json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": q}).encode(),
                         "application/execution.multiLevelQuery+json", "application/flatData+json", 600)
        jrs_rows = count_from(data) if data else None
        cur.execute(f"select count(*) from ORIGINBA_REPORTING.{view_for(r['file'])}")
        ora_rows = cur.fetchone()[0]

        def run(fields):
            payload = json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": {"select": {
                "fields": [{"id": f"f{i}", "field": f} for i, f in enumerate(fields)]}}}).encode()
            return not call("/rest_v2/queryExecutions?offset=0&pageSize=1", "POST", payload,
                            "application/execution.multiLevelQuery+json", "application/flatData+json", 300)[1]
        bad = [] if a.skip_fields else [f for chunk in chunks([f"{level_of[k]}.{k}" for k in got])
                                         for f in failing_fields(chunk, run)]
        chars = []
        for c in characteristic_checks((a.set_dir / r["file"]).read_text(encoding="utf-8")):
            if c["item"] not in level_of:   # missing on the server: the definition diff already says so
                continue
            q = {"select": {"aggregations": [{"id": "n", "fieldRef": f"{level_of[c['item']]}.{c['item']}",
                                              "aggregateFunction": "CountAll"}]}}
            data, why = call("/rest_v2/queryExecutions", "POST",
                             json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": q}).encode(),
                             "application/execution.multiLevelQuery+json", "application/flatData+json", 600)
            cur.execute(expected_characteristic_sql(c))
            want = cur.fetchone()[0]
            got = count_from(data) if data else None
            chars.append({"label": c["label"], "jaspersoft": got, "warehouse": want, "ok": got == want and want > 0})
        bad_chars = [c for c in chars if not c["ok"]]
        ok = not any(diff.values()) and jrs_rows == ora_rows and not bad and not bad_chars
        print(f"{'ok  ' if ok else 'FAIL'} {name}: {len(got)} fields ({', '.join(f'{k} {len(v)}' for k, v in diff.items())}); "
              f"rows {jrs_rows} / {ora_rows:,}{'; failing fields ' + ', '.join(bad) if bad else ''}"
              + "".join(f"; {c['label']} {c['jaspersoft']} / {c['warehouse']:,}{'' if c['ok'] else ' FAIL'}" for c in chars),
              flush=True)
        return {"domain": name, "ok": ok, "fields": len(got), **diff, "jaspersoft_rows": jrs_rows,
                "warehouse_rows": ora_rows, "failing_fields": bad, "characteristics": chars}

    try:
        listing, why = call("/rest_v2/resources?folderUri=" + urllib.parse.quote(f"{a.root}/Domains")
                            + "&type=semanticLayerDataSource&recursive=true&limit=500")
    except LinkDown as e:
        why = str(e)
    if why:
        print(f"STOP before any domain: the domain listing failed ({why})")
        return 2
    on_server = {r["uri"].rsplit("/", 1)[-1]: r["uri"] for r in (listing or {}).get("resourceLookup", [])}
    results, problems, stopped = [], 0, None
    names = sorted(set(by_name) | set(on_server))
    for n, name in enumerate(names):
        try:
            res = check(name)
        except LinkDown as e:
            stopped = f"{e}; not checked: {', '.join(names[n:])}"
            print(f"STOP {stopped}")
            break
        results.append(res)
        problems += not res["ok"]
    out = REPO / "backups" / "jaspersoft" / "domain_validation" / f"{a.env}_{a.org}_{time.strftime('%Y%m%d-%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"results": results, "stopped": stopped}, indent=1, default=str))
    print(f"{len(results)} of {len(names)} domains checked, {problems} problem(s) -> {out.relative_to(REPO)}")
    return 2 if stopped else (1 if problems else 0)


if __name__ == "__main__":
    sys.exit(main())
