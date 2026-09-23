#!/usr/bin/env python3
"""Ad Hoc views whose saved state aggregates a field their topic does not call a MEASURE.

The Ellensburg prod "Bill Cycle Transactions" case (2026-09-23): the view counts
FT_CORE.FT_ID; its topic (`<view>_files/topicJRXML`, generated per org) declared that field
kind=DIMENSION. The editor builds its measures list from the topic, hits a field that is not a
measure, and dies (`fetchFieldsList` null rootNode, then `hardEscape(...).join`). The same view in
Newark1 and CityCorp, identical state, topic kind=MEASURE, opens fine. Execution through the
API reads the state and never notices; a re-save regenerates the topic from itself and keeps the
bad kind. So this checks the one thing that separated broken from working across four samples.

    python3 scripts/jaspersoft/jrs_check_topic_kinds.py --env prod --org Ellensburg [--folder F] [--json out]
    python3 scripts/jaspersoft/jrs_check_topic_kinds.py --offline state.xml topic.jrxml   # one pair, no server
"""
from __future__ import annotations
import argparse, json, pathlib, re, sys, urllib.parse
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_adhoc_chart_props as cp  # noqa: E402


def aggregated_fields(state: str) -> set[str]:
    """Fields the saved state truly aggregates. Every column of a TABLE view is also a <measure>
    element with a function attribute; only real measures carry measure="true" (the first cut of
    this rule flagged 64 of Ellensburg's 150 views for that reason -- all table columns)."""
    return {m.group(1) for m in re.finditer(r'<measure\b[^>]*\bfieldName="([^"]+)"[^>]*\bmeasure="true"', state)
            if not m.group(1).startswith("_")}


def topic_kinds(topic: str) -> dict[str, str]:
    out = {}
    for m in re.finditer(r'<field name="([^"]+)"[^>]*>(.*?)</field>', topic, re.S):
        k = re.search(r'name="kind" value="([^"]+)"', m.group(2))
        out[m.group(1)] = k.group(1) if k else "?"
    return out


def mismatches(state: str, topic: str) -> list[tuple[str, str]]:
    kinds = topic_kinds(topic)
    return sorted((f, kinds.get(f, "absent")) for f in aggregated_fields(state) if kinds.get(f) != "MEASURE")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env"); ap.add_argument("--org"); ap.add_argument("--folder", default="/SmartCity/Report/Standard_Offering")
    ap.add_argument("--json", type=pathlib.Path)
    ap.add_argument("--offline", nargs=2, metavar=("STATE", "TOPIC"))
    a = ap.parse_args()
    if a.offline:
        mm = mismatches(pathlib.Path(a.offline[0]).read_text(errors="replace"), pathlib.Path(a.offline[1]).read_text(errors="replace"))
        print("MISMATCH " + ", ".join(f"{f} is {k}" for f, k in mm) if mm else "ok: every aggregated field is a MEASURE in the topic")
        return 1 if mm else 0
    if not (a.env and a.org):
        ap.error("--env and --org, or --offline STATE TOPIC")
    states = [u for u in cp.list_states(a.env, a.org, a.folder) if "_files/tmpAdv_" not in u and "dashboardReport" not in u]
    hits, checked = [], 0
    for su in states:
        tu = su[: -len("stateXML")] + "topicJRXML"
        c1, s, _ = cp._http(a.env, a.org, f"/rest_v2/resources{urllib.parse.quote(su)}")
        c2, t, _ = cp._http(a.env, a.org, f"/rest_v2/resources{urllib.parse.quote(tu)}")
        if c1 != 200 or c2 != 200:
            continue
        checked += 1
        mm = mismatches(s.decode("utf-8", "replace"), t.decode("utf-8", "replace"))
        if mm:
            view = su.rsplit("_files/", 1)[0]
            hits.append({"view": view, "mismatches": mm})
            print(f"  MISMATCH  {view.split('/Standard_Offering/')[-1]}  " + ", ".join(f"{f} is {k}" for f, k in mm))
    print(f"{a.env}/{a.org}: {checked} views checked under {a.folder}: {len(hits)} with a measure the topic does not call MEASURE")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"env": a.env, "org": a.org, "folder": a.folder, "hits": hits}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
