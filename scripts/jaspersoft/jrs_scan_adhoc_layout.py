#!/usr/bin/env python3
"""Find Ad Hoc chart states whose saved crosstab layout matches the one that would not open.

Ellensburg prod's Bill Cycle Transactions view (2026-09-23) executed through the API and failed in
the Ad Hoc editor. The one structural difference from the working copy: inside <columnGroups>, a
REAL field dimension carried <expandedLevels> alongside the Measures entry. Two signatures:

  strict  Measures AND a real field, both with <expandedLevels>, inside <columnGroups>
          (the exact shape of the broken state; nothing else in that folder had it)
  loose   any real field with <expandedLevels> inside <columnGroups>
          (candidates: needs a person to open one and confirm)

    python3 scripts/jaspersoft/jrs_scan_adhoc_layout.py --env prod --org Ellensburg [--folder F]
"""
from __future__ import annotations
import argparse, json, os, pathlib, re, sys, urllib.parse
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_run_sweep as sw  # noqa: E402
import jrs_adhoc_chart_props as cp  # noqa: E402


def column_expanded(state: str) -> list[str]:
    out = []
    for m in re.finditer(r"<columnGroups>(.*?)</columnGroups>", state, re.S):
        for qd in re.finditer(r'<queryDimension\b[^>]*fieldName="([^"]+)"[^>]*>(.*?)</queryDimension>', m.group(1), re.S):
            if "<expandedLevels>" in qd.group(2):
                out.append(qd.group(1))
    return out


def classify(state: str) -> tuple[str, list[str]]:
    dims = column_expanded(state)
    real = [d for d in dims if d != "Measures"]
    if real and "Measures" in dims:
        return "strict", dims
    if real:
        return "loose", dims
    return "", dims


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True)
    ap.add_argument("--folder", default="/SmartCity/Report/Standard_Offering")
    ap.add_argument("--json", type=pathlib.Path, help="write the hits here as well")
    a = ap.parse_args()
    uris = cp.list_states(a.env, a.org, a.folder)
    hits = []
    for uri in uris:
        c, b, _ = cp._http(a.env, a.org, f"/rest_v2/resources{urllib.parse.quote(uri)}")
        if c != 200:
            continue
        kind, dims = classify(b.decode("utf-8", "replace"))
        if kind:
            view = uri.rsplit("_files/", 1)[0]
            embedded = "_files/tmpAdv_" in uri or "dashboardReport" in uri
            hits.append({"kind": kind, "view": view, "state": uri, "dims": dims, "embedded": embedded})
            print(f"  {kind:6s} {'(dashboard copy) ' if embedded else ''}{view.split('/Standard_Offering/')[-1]}  {dims}")
    strict = sum(h["kind"] == "strict" for h in hits); loose = sum(h["kind"] == "loose" for h in hits)
    print(f"{a.env}/{a.org}: {len(uris)} chart states under {a.folder}: {strict} strict, {loose} loose")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"env": a.env, "org": a.org, "folder": a.folder, "hits": hits}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
