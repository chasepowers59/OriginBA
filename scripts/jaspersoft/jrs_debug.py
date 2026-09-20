#!/usr/bin/env python3
"""Look at one report, Ad Hoc view or domain in a client's org, run it, find why it is wrong,
and put the fix on the server -- the Fond du Lac asset-domain investigation as a tool.

  inspect URI      what it is and what it depends on: a view's domain, selected fields, every
                   saved filter with its value (and whether it is an "any value" placeholder or
                   names a value the client does not configure); a domain's derived tables and
                   joins; a report's datasource, query and input controls
  run URI          execute it the way the server does (views through queryExecutions with the
                   any-value fix); when it comes back empty, --bisect runs each saved filter alone
                   and names the one that empties it
  domain-copy URI --name NEW [--set-query ID=file.sql]... [--set-join "OLD_EXPR=>NEW_EXPR"]...
                   the domain's schema with those edits, imported as a SECOND domain beside the
                   original (the org's own datasource export listed first), so reports on the
                   original keep working while the fix is proven
  domain-apply URI --schema file.xml
                   replace the ORIGINAL domain's schema (item ids unchanged => bound views survive)
  view-update URI [--drop-filter FIELD]... [--set-filter FIELD=v1,v2]... [--swap-field OLD=NEW]...
                   change a saved Ad Hoc view's query in place
  report-update URI --jrxml file.jrxml
                   replace a report unit's JRXML

Writes need --confirm <Org> (the org the login is scoped to) and, on prod, --i-mean-prod;
--dry-run prints the call and writes the artefact locally instead. Snapshot the org first.

    python3 scripts/jaspersoft/jrs_debug.py --env test --org Fond_Du_Lac inspect /SmartCity/Report/FDL_Asset/FDLWU_Meter_View_ALL_RES_MTRs
    python3 scripts/jaspersoft/jrs_debug.py --env test --org Fond_Du_Lac run /SmartCity/Report/FDL_Asset/FDLWU_Meter_View_ALL_RES_MTRs --bisect
"""
from __future__ import annotations

import argparse
import base64
import copy
import io
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_repository as jrs  # noqa: E402
import jrs_run_sweep as sw  # noqa: E402

DRY = {"on": False}


def get(uri: str, expanded: bool = True) -> dict:
    code, body, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(uri)}" + ("?expanded=true" if expanded else ""))
    if code != 200:
        sys.exit(f"{uri}: {code} {sw._message(body)[:200]}")
    return json.loads(body)


def get_file(uri: str) -> bytes:
    code, body, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(uri)}", accept="application/xml")
    if code != 200:
        sys.exit(f"{uri}: {code} {sw._message(body)[:200]}")
    return body


def put(path: str, body: bytes, ctype: str, what: str) -> int:
    print(f"PUT {path}  ({what}, {len(body)} bytes)")
    if DRY["on"]:
        return 0
    code, out, _ = sw._http(path, "PUT", body, ctype, timeout=300)
    print(code, sw._message(out)[:300] if code >= 300 else "ok")
    return 0 if code < 300 else 1


def kind_of(d: dict) -> str:
    for k in ("adhocDataView", "reportUnit", "semanticLayerDataSource", "domain"):
        if k in d or d.get("resourceType") == k:
            return k
    return d.get("resourceType") or "?"


# ---------------------------------------------------------------- saved filters, read for a person
def filters_of(query: dict) -> list[dict]:
    """Each saved filter: the field, the operator, the value(s) it was saved with."""
    params = {p["name"]: p["expression"]["object"] for p in (query.get("where") or {}).get("parameters", []) if "expression" in p}
    out = []

    def val(node):
        if "variable" in node and node["variable"]["name"] in params:
            return val(params[node["variable"]["name"]])
        if "string" in node: return node["string"]["value"]
        if "number" in node: return node["number"]["value"]
        if "list" in node: return [val(i) for i in node["list"]["items"]]
        if "relativeTimestampRange" in node or "relativeDateRange" in node: return list(node.values())[0]["value"]
        if "timestamp" in node or "date" in node: return list(node.values())[0]["value"]
        if "NULL" in node: return None
        if "variable" in node: return "$" + node["variable"]["name"]
        return json.dumps(node)[:60]

    def walk(node):
        if isinstance(node, dict):
            if "function" in node and node["function"].get("functionName") == "filter":
                ops = node["function"]["operands"]; inner = ops[-1]; op = next(iter(inner)); args = inner[op].get("operands", []) if isinstance(inner[op], dict) else []
                if op == "function":
                    op = inner["function"]["functionName"]; args = inner["function"]["operands"]
                field = next((x["variable"]["name"] for x in args if "variable" in x and x["variable"]["name"] not in params), "?")
                values = [val(x) for x in args if not ("variable" in x and x["variable"]["name"] == field)]
                any_value = op in ("in", "notIn") and values == [[]] or op == "isAnyValue"
                out.append({"id": ops[0]["string"]["value"], "field": field, "op": op, "values": values, "any_value": any_value})
                return
            for v in node.values(): walk(v)
        elif isinstance(node, list):
            for v in node: walk(v)
    walk((query.get("where") or {}).get("filterExpression"))
    return out


def inspect(uri: str, client: str | None) -> int:
    d = get(uri); k = kind_of(d)
    print(f"{k}  {d.get('label')!r}  {uri}\n  updated {d.get('updateDate')}  by-descriptor version {d.get('version')}")
    if k == "adhocDataView":
        ds = d.get("dataSource", {}); dom = next((v.get("uri") for v in ds.values() if isinstance(v, dict) and v.get("uri")), None)
        qk = next(iter(d["query"])); q = d["query"][qk]
        print(f"  domain: {dom}\n  query: {qk}")
        sel = q.get("select", {})
        for key, items in sel.items():
            if key == "distinctFields":
                print(f"  fields: {', '.join(i['field'] for i in items)}")
            elif key == "aggregations":
                print(f"  measures: {', '.join(i.get('fieldRef', '?') + ' ' + i.get('functionName', '') for i in items)}")
        for g in ("groupBy", "orderBy"):
            if q.get(g): print(f"  {g}: {json.dumps(q[g])[:200]}")
        fl = filters_of(q); cfg = None
        if client:
            sys.path.insert(0, str(HERE)); import audit_adhoc_saved_filters as au
            cfg = au.configuration(client)
        print(f"  saved filters: {len(fl)}")
        for f in fl:
            note = "  (any value: ignored by the UI, applied literally by the API)" if f["any_value"] else ""
            if cfg and not f["any_value"]:
                codes, descs, _ = cfg
                flat = [v for v in (f["values"] if isinstance(f["values"], list) else [f["values"]]) for v in (v if isinstance(v, list) else [v])]
                missing = [v for v in flat if isinstance(v, str) and re.search(r"[A-Za-z]", v) and v.upper().strip() not in codes and v.upper().strip() not in descs and not re.match(r"^(DAY|WEEK|MONTH|YEAR)", v)]
                if missing: note += f"  (NOT configured at {client}: {missing})"
            print(f"    {f['id']:10} {f['field']:50} {f['op']:14} {json.dumps(f['values'])[:80]}{note}")
        if dom:
            print("  domain schema (derived tables and joins the view's tables touch):")
            tables = {f.split(".")[0] for f in [i.get("field", "") for i in sel.get("distinctFields", [])] + [x["field"] for x in fl]}
            schema_report(dom, tables)
    elif k in ("semanticLayerDataSource", "domain"):
        schema_report(uri, None)
    elif k == "reportUnit":
        print(f"  datasource: {json.dumps(d.get('dataSource'))[:160]}")
        jr = d.get("jrxml", {}); content = jr.get("jrxmlFile", {}).get("content") or ""
        x = base64.b64decode(content).decode(errors="ignore") if content else ""
        if x:
            m = re.search(r"<query[^>]*>\s*<!\[CDATA\[(.*?)\]\]>", x, re.S) or re.search(r"<queryString[^>]*>\s*<!\[CDATA\[(.*?)\]\]>", x, re.S)
            print("  query:", (m.group(1).strip()[:600] if m else "(none)").replace("\n", "\n         "))
            print("  parameters:", ", ".join(re.findall(r'<parameter name="([^"]+)"', x)))
        code, body, _ = sw._http(f"/rest_v2/reports{urllib.parse.quote(uri)}/inputControls")
        if code == 200:
            print("  input controls:", ", ".join(f"{c['id']}({c.get('type')})" for c in json.loads(body).get("inputControl", [])))
    return 0


def schema_report(domain_uri: str, tables: set[str] | None) -> None:
    xml = get_file(domain_uri + "_files/schema").decode(errors="ignore")
    for m in re.finditer(r'<jdbcQuery id="([^"]+)"[^>]*>(.*?)</jdbcQuery>', xml, re.S):
        qid, body = m.group(1), m.group(2)
        if tables is None or qid in tables:
            sql = re.search(r"<query>(.*?)</query>", body, re.S); sql = (sql.group(1) if sql else "").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
            print(f"    derived {qid}:\n      " + sql.strip().replace("\n", "\n      ")[:900])
    for m in re.finditer(r'<join expr="([^"]+)" left="([^"]+)" right="([^"]+)" type="([^"]+)"', xml):
        if tables is None or m.group(2) in tables or m.group(3) in tables:
            print(f"    join {m.group(4):10} {m.group(1)}")


# ---------------------------------------------------------------- run and bisect
def run(uri: str, bisect: bool, timeout: int) -> int:
    d = get(uri); k = kind_of(d)
    if k == "reportUnit":
        r = sw.run_report(uri, timeout); print(json.dumps(r)); return 0 if r["outcome"] == "ok" else 1
    if k != "adhocDataView":
        sys.exit(f"run: {k} is not executable here (use jrs_repository.py run for reports)")
    r = sw.run_view(uri, timeout); print("as saved (any-value filters dropped):", json.dumps(r))
    if not bisect or r["outcome"] not in ("empty", "ok"):
        return 0 if r["outcome"] == "ok" else 1
    qk = next(iter(d["query"])); q = sw._inline_parameters(d["query"][qk]); fl = filters_of(d["query"][qk])
    nodes = []

    def collect(n):
        if isinstance(n, dict):
            if "function" in n and n["function"].get("functionName") == "filter": nodes.append(n); return
            for v in n.values(): collect(v)
        elif isinstance(n, list):
            for v in n: collect(v)
    collect((q.get("where") or {}).get("filterExpression"))
    sel = {"distinctFields": q["select"].get("distinctFields", [])[:1]} if "distinctFields" in q.get("select", {}) else q["select"]
    print("each saved filter alone:")
    for n in nodes:
        fid = n["function"]["operands"][0]["string"]["value"]; meta = next((f for f in fl if f["id"] == fid), {})
        qq = {"select": sel, "where": {"filterExpression": {"object": n}}}
        code, body, dt = sw._http("/rest_v2/queryExecutions?offset=0&pageSize=1", "POST", json.dumps({"dataSource": {"reference": {"uri": uri}}, "query": qq}).encode(),
                                  f"application/execution.{qk}Query+json", f"application/{qk}Data+json", timeout)
        rows = json.loads(body).get("totalCounts") if code == 200 else f"{code} {sw._message(body)[:80]}"
        print(f"  {fid:10} {meta.get('field', '?'):50} {meta.get('op', ''):12} {json.dumps(meta.get('values'))[:50]:52} -> {rows}")
    return 0


# ---------------------------------------------------------------- fixes
def patch_schema(xml: str, set_query: list[str], set_join: list[str]) -> str:
    for sq in set_query:
        qid, path = sq.split("=", 1); sql = pathlib.Path(path).read_text().strip()
        esc = sql.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        pat = re.compile(rf'(<jdbcQuery id="{re.escape(qid)}"[^>]*>.*?<query>)(.*?)(</query>)', re.S)
        if not pat.search(xml):
            sys.exit(f"no derived table {qid} in the schema")
        xml = pat.sub(lambda m: m.group(1) + esc + m.group(3), xml, count=1)
    for sj in set_join:
        old, new = sj.split("=>", 1)
        if f'expr="{old.strip()}"' not in xml:
            sys.exit(f"no join with expr {old.strip()!r}")
        left, right = [s.strip() for s in re.split(r"==", new, 1)]
        xml = re.sub(rf'<join expr="{re.escape(old.strip())}" left="[^"]+" right="[^"]+"',
                     f'<join expr="{new.strip()}" left="{left.split(".")[0]}" right="{right.split(".")[0]}"', xml, count=1)
    return xml


def _org_export_package(org: str, folder: str, name: str, label: str, description: str, schema_xml: str, ds_zip: bytes, ds: str) -> bytes:
    dsz = zipfile.ZipFile(io.BytesIO(ds_zip)); idx = dsz.read("index.xml").decode()
    keyalias = re.search(r'name="keyalias" value="([^"]+)"', idx).group(1); enc = re.search(r'name="encrypted" value="([^"]+)"', idx).group(1); jsv = re.search(r'name="jsVersion" value="([^"]+)"', idx).group(1)
    now = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    def folder_xml(parent, nm, lbl, kids=()):
        k = "".join(f"\n    <resource>{c}</resource>" for c in kids)
        return f'<?xml version="1.0" encoding="UTF-8"?>\n<folder exportedWithPermissions="false">\n    <parent>{parent}</parent>\n    <name>{nm}</name>\n    <label>{lbl}</label>\n    <creationDate>{now}</creationDate>\n    <updateDate>{now}</updateDate>{k}\n</folder>\n'.encode()
    dom = f'''<?xml version="1.0" encoding="UTF-8"?>
<semanticLayerDataSource exportedWithPermissions="false">
    <folder>{folder}</folder>
    <name>{name}</name>
    <version>0</version>
    <label>{label}</label>
    <description>{description[:240]}</description>
    <creationDate>{now}</creationDate>
    <updateDate>{now}</updateDate>
    <schema>
        <localResource
            xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            exportedWithPermissions="false" dataFile="schema.data" xsi:type="fileResource">
            <folder>{folder}/{name}_files</folder>
            <name>schema</name>
            <version>0</version>
            <label>schema</label>
            <description>schema</description>
            <creationDate>{now}</creationDate>
            <updateDate>{now}</updateDate>
            <fileType>xml</fileType>
        </localResource>
    </schema>
    <dataSource>
        <alias>{ds}</alias>
        <dataSourceReference>
            <uri>/DataSource/{ds}</uri>
        </dataSourceReference>
    </dataSource>
</semanticLayerDataSource>
'''.encode()
    out = io.BytesIO(); parts = folder.strip("/").split("/")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n in dsz.namelist():
            if n.startswith("resources/DataSource/") and not n.endswith("/"): z.writestr(n, dsz.read(n))
        for i in range(1, len(parts)):
            z.writestr("resources/" + "/".join(parts[:i]) + "/.folder.xml", folder_xml("/" + "/".join(parts[:i-1]) if i > 1 else "/", parts[i-1], parts[i-1]))
        z.writestr(f"resources{folder}/.folder.xml", folder_xml("/" + "/".join(parts[:-1]), parts[-1], parts[-1].replace("_", " "), [name]))
        z.writestr(f"resources{folder}/{name}.xml", dom); z.writestr(f"resources{folder}/{name}_files/schema.data", schema_xml.encode())
        z.writestr("index.xml", (f'<?xml version="1.0" encoding="UTF-8"?>\n<export><property name="keyalias" value="{keyalias}"/><module id="repositoryResources"><resource>/DataSource/{ds}</resource><resource>{folder}/{name}</resource></module>'
                                 f'<module id="favorites"/><property name="pathProcessorId" value="zip"/><property name="rootTenantId" value="{org}"/><property name="jsVersion" value="{jsv}"/><property name="encrypted" value="{enc}"/></export>').encode())
    return out.getvalue()


def domain_copy(uri: str, name: str, set_query: list[str], set_join: list[str], org: str, out_dir: pathlib.Path) -> int:
    d = get(uri, expanded=False); ds_uri = d["dataSource"]["dataSourceReference"]["uri"]; ds = ds_uri.rsplit("/", 1)[-1]
    xml = patch_schema(get_file(uri + "_files/schema").decode(errors="ignore"), set_query, set_join)
    folder = uri.rsplit("/", 1)[0]
    import jrs_inventory as inv
    ds_zip = inv.export_zip([ds_uri])   # the org's OWN datasource, so the reference resolves and nothing is repointed
    pkg = _org_export_package(org, folder, name, f"{d.get('label')} (Fixed)", f"Copy of {d.get('label')} with edits {set_query + set_join}", xml, ds_zip, ds)
    out_dir.mkdir(parents=True, exist_ok=True); p = out_dir / f"{name}_import.zip"; p.write_bytes(pkg); (out_dir / f"{name}_schema.xml").write_text(xml)
    print(f"package {p} ({len(pkg)} bytes); schema {out_dir / (name + '_schema.xml')}")
    if DRY["on"]:
        return 0
    code, body, _ = sw._http("/rest_v2/import?update=true&skipUserUpdate=true", "POST", pkg, "application/zip"); tid = json.loads(body)["id"]
    while True:
        code, body, _ = sw._http(f"/rest_v2/import/{tid}/state"); st = json.loads(body)
        if st.get("phase") in ("finished", "failed"): break
        time.sleep(2)
    print(json.dumps(st)[:300]); print(f"copy at {folder}/{name}; prove it with: run/inspect on views saved onto it, then domain-apply --schema {out_dir / (name + '_schema.xml')} on the original")
    return 0 if st.get("phase") == "finished" and not st.get("warnings") else 1


def domain_apply(uri: str, schema_path: str) -> int:
    xml = pathlib.Path(schema_path).read_bytes()
    body = json.dumps({"type": "xml", "label": "schema", "content": base64.b64encode(xml).decode()}).encode()
    return put(f"/rest_v2/resources{urllib.parse.quote(uri)}_files/schema", body, "application/repository.file+json", "domain schema replaced in place")


def view_update(uri: str, drop: list[str], setf: list[str], swap: list[str]) -> int:
    d = get(uri); qk = next(iter(d["query"])); q = d["query"][qk]
    params = {p["name"]: p for p in (q.get("where") or {}).get("parameters", [])}

    def prune(node):
        if isinstance(node, dict):
            if "function" in node and node["function"].get("functionName") == "filter":
                text = json.dumps(node); return None if any(f'"name": "{f}"' in text for f in drop) else node
            for key in ("and", "or"):
                if key in node:
                    kept = [k for k in (prune(o) for o in node[key]["operands"]) if k is not None]
                    return None if not kept else (kept[0] if len(kept) == 1 else {key: {**node[key], "operands": kept}})
            return {k: prune(v) for k, v in node.items()}
        return node
    if drop:
        fe = prune((q.get("where") or {}).get("filterExpression"))
        q["where"] = {**q.get("where", {}), "filterExpression": fe} if fe else {k: v for k, v in q.get("where", {}).items() if k != "filterExpression"}
    for s in setf:
        field, vals = s.split("=", 1); items = [{"string": {"value": v}} for v in vals.split(",")]
        hit = [p for p in params.values() if p["name"].startswith(field.split(".")[-1])]
        if not hit: sys.exit(f"no saved parameter for {field}; parameters: {sorted(params)}")
        hit[0]["expression"] = {"object": {"list": {"items": items}}}
    for s in swap:
        old, new = s.split("=", 1); t = json.dumps(d).replace(f'"{old}"', f'"{new}"'); d = json.loads(t); q = d["query"][qk]
    body = json.dumps(d).encode()
    return put(f"/rest_v2/resources{urllib.parse.quote(uri)}", body, "application/repository.adhocDataView+json", f"view query updated: drop={drop} set={setf} swap={swap}")


def report_update(uri: str, jrxml_path: str) -> int:
    content = base64.b64encode(pathlib.Path(jrxml_path).read_bytes()).decode()
    body = json.dumps({"type": "jrxml", "label": "main_jrxml", "content": content}).encode()
    return put(f"/rest_v2/resources{urllib.parse.quote(uri)}_files/main_jrxml", body, "application/repository.file+json", "report JRXML replaced")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", choices=jrs.ENVS, default="test"); ap.add_argument("--org", required=True)
    ap.add_argument("--client", help="config id for filter checks (fonddulac, citycorp, ...)")
    ap.add_argument("--confirm"); ap.add_argument("--i-mean-prod", action="store_true"); ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--timeout", type=int, default=120)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect").add_argument("uri")
    r = sub.add_parser("run"); r.add_argument("uri"); r.add_argument("--bisect", action="store_true")
    c = sub.add_parser("domain-copy"); c.add_argument("uri"); c.add_argument("--name", required=True); c.add_argument("--set-query", action="append", default=[]); c.add_argument("--set-join", action="append", default=[])
    c.add_argument("--out", default=str(jrs.__file__ and pathlib.Path(HERE.parents[1], "backups/jaspersoft/promotion")))
    da = sub.add_parser("domain-apply"); da.add_argument("uri"); da.add_argument("--schema", required=True)
    v = sub.add_parser("view-update"); v.add_argument("uri"); v.add_argument("--drop-filter", action="append", default=[]); v.add_argument("--set-filter", action="append", default=[]); v.add_argument("--swap-field", action="append", default=[])
    ru = sub.add_parser("report-update"); ru.add_argument("uri"); ru.add_argument("--jrxml", required=True)
    a = ap.parse_args()
    os.environ["JRS_ENV"] = a.env; DRY["on"] = a.dry_run
    e = a.env.upper(); base = jrs._env_var("USER").split("|")[0]; os.environ[f"JRS_{e}_USER"] = f"{base}|{a.org}"
    sw._AUTH.header = sw._auth_for(a.org)
    if a.cmd in ("domain-copy", "domain-apply", "view-update", "report-update"):
        jrs.guard_write(a.cmd, a)
    if a.cmd == "inspect": return inspect(a.uri, a.client)
    if a.cmd == "run": return run(a.uri, a.bisect, a.timeout)
    if a.cmd == "domain-copy": return domain_copy(a.uri, a.name, a.set_query, a.set_join, a.org, pathlib.Path(a.out))
    if a.cmd == "domain-apply": return domain_apply(a.uri, a.schema)
    if a.cmd == "view-update": return view_update(a.uri, a.drop_filter, a.set_filter, a.swap_field)
    return report_update(a.uri, a.jrxml)


if __name__ == "__main__":
    raise SystemExit(main())
