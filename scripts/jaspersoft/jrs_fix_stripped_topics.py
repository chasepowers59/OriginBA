#!/usr/bin/env python3
"""Repair Ad Hoc views whose generated topic JRXML was stripped for a JRS 9 Ad Hoc loader and no
longer parses on JRS 10 ("AdhocDataView state initialization error").

The 9.0 promotion path ran topics through the compat strip (namespace removed, uuid and
nestedType removed, <queryString>). 10.0's legacy loader keys on the JRXML 6 namespace; a
namespace-less topic is read as JRXML 7 and fails. The view's state and its domain are fine.
Fix: give each such view the topic its twin on the TEST org carries (10.0-generated, same domain
schema, same state). Each old topic is saved under backups/ first; each view is opened and run
after. Read-only scan with --scan; writes need --i-mean-prod.

    python3 scripts/jaspersoft/jrs_fix_stripped_topics.py --env prod --org CityCorp --scan
    python3 scripts/jaspersoft/jrs_fix_stripped_topics.py --env prod --org CityCorp --source-env test --i-mean-prod
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import sys
import time
import urllib.parse
import concurrent.futures as cf

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_run_sweep as sw  # noqa: E402

REPO = HERE.parents[1]


def _get(env, org, path, accept="application/xml"):
    os.environ["JRS_ENV"] = env; sw._AUTH.header = sw._auth_for(org)
    c, b, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(path)}", accept=accept, timeout=90)
    return c, b


def is_stripped(topic: bytes) -> bool:
    return b"<jasperReport" in topic and b'xmlns="http://jasperreports' not in topic and b"<queryString" in topic


def scan(env, org, folder):
    c, b = _get(env, org, "")   # warm the auth
    os.environ["JRS_ENV"] = env; sw._AUTH.header = sw._auth_for(org)
    c, b, _ = sw._http(f"/rest_v2/resources?folderUri={urllib.parse.quote(folder)}&recursive=true&type=adhocDataView&limit=3000")
    views = [i["uri"] for i in json.loads(b).get("resourceLookup", [])] if c == 200 else []

    def one(uri):
        c2, t = _get(env, org, uri + "_files/topicJRXML")
        return uri, (c2 == 200 and is_stripped(t))
    with cf.ThreadPoolExecutor(6) as ex:
        return [u for u, s in ex.map(one, views) if s]


def fix(env, org, src_env, uri, out_dir):
    c, old = _get(env, org, uri + "_files/topicJRXML")
    c2, new = _get(src_env, org, uri + "_files/topicJRXML")
    if c2 != 200 or is_stripped(new) or b'xmlns="http://jasperreports' in new:
        return uri, "no 10.0 topic on source org", None
    (out_dir / (uri.strip("/").replace("/", "__") + ".topicJRXML")).write_bytes(old)
    c3, d = _get(env, org, uri + "_files/topicJRXML", accept="application/repository.file+json")
    try:
        meta = json.loads(d) if c3 == 200 else {}
    except ValueError:
        meta = {}
    os.environ["JRS_ENV"] = env; sw._AUTH.header = sw._auth_for(org)
    body = json.dumps({"uri": meta.get("uri", uri + "_files/topicJRXML"), "label": meta.get("label", "topicJRXML"), "version": meta.get("version", 0),
                       "type": "jrxml", "content": base64.b64encode(new).decode()}).encode()
    c4, b4, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(uri)}_files/topicJRXML", "PUT", body, "application/repository.file+json", timeout=120)
    if c4 >= 300:
        return uri, f"PUT {c4}: {sw._message(b4)[:120]}", None
    c5, b5, _ = sw._http(f"/rest_v2/resources{urllib.parse.quote(uri)}?expanded=true")
    if c5 != 200:
        return uri, f"replaced but still does not open: {sw._message(b5)[:120]}", None
    r = sw.run_view(uri, 60)
    return uri, "fixed", r


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", default="prod"); ap.add_argument("--org", required=True); ap.add_argument("--folder", default="/SmartCity")
    ap.add_argument("--source-env", default="test"); ap.add_argument("--scan", action="store_true"); ap.add_argument("--i-mean-prod", action="store_true")
    a = ap.parse_args()
    stripped = scan(a.env, a.org, a.folder)
    print(f"[{a.env}] {a.org}: {len(stripped)} views with a stripped topic")
    if a.scan:
        for u in stripped: print("  ", u)
        return 0
    if a.env == "prod" and not a.i_mean_prod:
        sys.exit("writes to prod need --i-mean-prod")
    out = REPO / "backups/jaspersoft/topics" / f"{a.env}_{a.org}_{time.strftime('%Y%m%d-%H%M%S')}"; out.mkdir(parents=True, exist_ok=True)
    results = []
    for i, u in enumerate(stripped, 1):
        uri, status, r = fix(a.env, a.org, a.source_env, u, out)
        results.append((uri, status, r))
        tail = f"{r['outcome']} rows={r.get('rows')} {r['seconds']:.0f}s" if r else ""
        print(f"  [{i:3}/{len(stripped)}] {status:14} {uri.split('/SmartCity/', 1)[1][:80]}  {tail}", flush=True)
    fixed = [x for x in results if x[1] == "fixed"]; opens = sum(1 for _, _, r in fixed if r and r["outcome"] in ("ok", "empty", "timeout"))
    print(f"\n{len(fixed)} of {len(stripped)} replaced; {opens} open and execute (ok/empty/slow); old topics under {out}")
    for uri, status, r in results:
        if status != "fixed" or (r and r["outcome"] == "error"): print("  ATTENTION", status, uri, (r or {}).get("detail", "")[:120])
    return 0 if len(fixed) == len(stripped) else 1


if __name__ == "__main__":
    raise SystemExit(main())
