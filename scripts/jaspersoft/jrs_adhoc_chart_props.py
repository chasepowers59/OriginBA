#!/usr/bin/env python3
"""Set Highcharts advanced properties on every Ad Hoc chart state under a folder.

A chart's formatting lives in `<view>_files/stateXML` as `<advancedChartProperty>` name/value
pairs (Highcharts option paths). A dashboard embeds its OWN copies of each chart
(`<Dashboard>_files/tmpAdv_*_files/stateXML` and `.../dashboardReport_files/stateXML`), so a
formatting change has to reach every copy, which is what the recursive folder walk does.

Trap this tool exists for: `plotOptions.series.dataLabels.style.color=contrast` makes labels
drawn OUTSIDE a bar resolve to white on the white plot area (invisible); inside a bar it is the
right choice. Prefer an explicit colour (`#1F2933`) unless the labels are inside the bars.

    python3 scripts/jaspersoft/jrs_adhoc_chart_props.py --env internal --org Origin_DEMO \
        --folder /SmartCity/Report/Standard_Offering/Meter_Operations \
        --only-if plotOptions.series.dataLabels.style.color=contrast \
        --set plotOptions.series.dataLabels.style.color=#1F2933 [--dry-run] [--i-mean-prod]

Every state touched is saved under backups/jaspersoft/adhoc_state/<env>_<org>_<stamp>/ first and
read back after the PUT; a state whose read-back lacks the value is reported, not assumed.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import pathlib
import re
import sys
import time
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_run_sweep as sw  # noqa: E402

REPO = HERE.parents[1]


def _prop_re(name: str) -> re.Pattern:
    return re.compile(r"(<name>" + re.escape(name) + r"</name>\s*<value>)([^<]*)(</value>)")


def matches(state: str, conditions: list[tuple[str, str]]) -> bool:
    for name, value in conditions:
        m = _prop_re(name).search(state)
        if not m or m.group(2) != value:
            return False
    return True


def patch(state: str, sets: list[tuple[str, str]]) -> str:
    """Replace an existing property's value, else add the property to the chart's list."""
    for name, value in sets:
        rx = _prop_re(name)
        if rx.search(state):
            state = rx.sub(lambda m: m.group(1) + value + m.group(3), state, count=1)
            continue
        prop = f"<advancedChartProperty>\n        <name>{name}</name>\n        <value>{value}</value>\n      </advancedChartProperty>\n    "
        if "</advancedProperties>" in state:
            state = state.replace("</advancedProperties>", prop + "</advancedProperties>", 1)
        else:
            m = re.search(r"<intelligentChartState\b[^>]*>\n?", state)
            if not m:
                raise ValueError("no <intelligentChartState> element: not an Ad Hoc chart state")
            state = state[: m.end()] + "    <advancedProperties>\n      " + prop + "</advancedProperties>\n" + state[m.end():]
    return state


def _http(env, org, path, method="GET", body=None, ctype=None, accept="application/octet-stream", timeout=90):
    os.environ["JRS_ENV"] = env; sw._AUTH.header = sw._auth_for(org)
    return sw._http(path, method, body, ctype, accept, timeout)


def list_states(env, org, folder) -> list[str]:
    c, b, _ = _http(env, org, f"/rest_v2/resources?folderUri={urllib.parse.quote(folder)}&recursive=true&type=file&showHiddenItems=true&limit=5000",
                    accept="application/json")
    if c != 200:
        raise SystemExit(f"list {folder}: HTTP {c}: {sw._message(b)[:200]}")
    return sorted(i["uri"] for i in json.loads(b).get("resourceLookup", []) if i["uri"].endswith("/stateXML"))


def put_state(env, org, uri, new: str) -> tuple[int | None, str]:
    c, d, _ = _http(env, org, f"/rest_v2/resources{urllib.parse.quote(uri)}", accept="application/repository.file+json")
    meta = json.loads(d) if c == 200 else {}
    body = json.dumps({"uri": uri, "label": meta.get("label", "stateXML"), "version": meta.get("version", 0),
                       "type": "xml", "content": base64.b64encode(new.encode()).decode()}).encode()
    c2, b2, _ = _http(env, org, f"/rest_v2/resources{urllib.parse.quote(uri)}", "PUT", body, "application/repository.file+json", timeout=120)
    return c2, sw._message(b2)[:160] if c2 is None or c2 >= 300 else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True)
    ap.add_argument("--folder", required=True)
    ap.add_argument("--set", action="append", default=[], metavar="NAME=VALUE", help="property to set (repeatable)")
    ap.add_argument("--only-if", action="append", default=[], metavar="NAME=VALUE", help="touch a state only when it carries this value (repeatable, all must hold)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--i-mean-prod", action="store_true")
    a = ap.parse_args()
    if a.env == "prod" and not a.i_mean_prod and not a.dry_run:
        raise SystemExit("refusing to write to prod without --i-mean-prod")
    sets = [tuple(s.split("=", 1)) for s in a.set]
    conds = [tuple(s.split("=", 1)) for s in a.only_if]
    if not sets:
        raise SystemExit("nothing to --set")

    uris = list_states(a.env, a.org, a.folder)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    out_dir = REPO / "backups" / "jaspersoft" / "adhoc_state" / f"{a.env}_{a.org}_{stamp}"
    touched = skipped = failed = 0
    for uri in uris:
        c, b, _ = _http(a.env, a.org, f"/rest_v2/resources{urllib.parse.quote(uri)}")
        if c != 200:
            print(f"  ? {uri}: GET {c}"); failed += 1; continue
        state = b.decode()
        if "<intelligentChartState" not in state or not matches(state, conds):
            skipped += 1; continue
        new = patch(state, sets)
        if new == state:
            skipped += 1; continue
        if a.dry_run:
            print(f"  would set {uri}"); touched += 1; continue
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / uri.strip("/").replace("/", "__")).write_bytes(b)
        c2, err = put_state(a.env, a.org, uri, new)
        if err:
            print(f"  ! {uri}: PUT {c2}: {err}"); failed += 1; continue
        c3, b3, _ = _http(a.env, a.org, f"/rest_v2/resources{urllib.parse.quote(uri)}")
        if c3 != 200 or not matches(b3.decode(), sets):
            print(f"  ! {uri}: read-back does not carry the new values"); failed += 1; continue
        print(f"  set {uri}"); touched += 1
    print(f"{len(uris)} chart states under {a.folder}: {touched} {'would change' if a.dry_run else 'changed and read back'}, {skipped} skipped, {failed} failed"
          + ("" if a.dry_run or not touched else f"; originals under {out_dir.relative_to(REPO)}"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
