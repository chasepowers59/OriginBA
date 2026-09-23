#!/usr/bin/env python3
"""Find Ad Hoc chart states that ARE a known-broken saved state, org by org.

History, so nobody re-derives it: Ellensburg prod's "Bill Cycle Transactions" view executed
through the API and would not open in the 10.0 Ad Hoc editor (2026-09-23). The first version of
this scanner flagged a layout SIGNATURE read off that state (a field and the Measures entry both
expanded inside <columnGroups>). Calibration killed it the same morning: "Meter Operations -
Daily Installations" in Ellensburg prod carries the identical shape and opens fine. The trigger
inside that saved state is still not isolated; what is certain is that the state itself is bad
and that a copy of it elsewhere is bad too (Newark1 carried the same state, two run-mode flags
apart).

So this scanner does the one thing that has held up: it compares every chart state in a folder
with a known-broken state, ignoring the fields that vary between copies (temp report ids,
version stamps, the sample/full data-size flags), and reports the ones that are the same state.

    python3 scripts/jaspersoft/jrs_scan_adhoc_layout.py --env prod --org Newark1 \
        --like backups/jaspersoft/copy/<...>/target_before.zip::<stateXML entry> [--folder F]
    python3 scripts/jaspersoft/jrs_scan_adhoc_layout.py --env prod --org Newark1 --like path/to/stateXML.data

--like takes a file, or zip::entry. A hit is fixed the way Ellensburg was: jrs_copy_resources.py
--view from an org whose copy opens.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import urllib.parse
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import jrs_adhoc_chart_props as cp  # noqa: E402

# What differs between two copies of the SAME saved state: the server's temp report id, version
# stamps, and the run-mode attributes the editor toggles (sample vs full, max-rows guard).
VARIES = re.compile(
    r"/temp/aru[0-9a-f-]+"
    r"|<(version|creationDate|updateDate)>[^<]*</\1>"
    r'| (dataSize|ignoreMaxRows)="[^"]*"'
)


def canon(state: str) -> str:
    return re.sub(r"\s+", " ", VARIES.sub("", state.replace("\r", ""))).strip()


def load_like(spec: str) -> str:
    if "::" in spec:
        z, entry = spec.split("::", 1)
        with zipfile.ZipFile(z) as zf:
            return zf.read(entry).decode("utf-8", "replace")
    return pathlib.Path(spec).read_text(encoding="utf-8", errors="replace")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True)
    ap.add_argument("--folder", default="/SmartCity/Report/Standard_Offering")
    ap.add_argument("--like", required=True, help="a known-broken stateXML: a file, or zip::entry")
    ap.add_argument("--json", type=pathlib.Path, help="write the hits here as well")
    a = ap.parse_args()
    target = canon(load_like(a.like))
    uris = cp.list_states(a.env, a.org, a.folder)
    hits = []
    for uri in uris:
        c, b, _ = cp._http(a.env, a.org, f"/rest_v2/resources{urllib.parse.quote(uri)}")
        if c == 200 and canon(b.decode("utf-8", "replace")) == target:
            view = uri.rsplit("_files/", 1)[0]
            hits.append({"view": view, "state": uri, "embedded": "_files/tmpAdv_" in uri or "dashboardReport" in uri})
            print(f"  SAME STATE  {view.split('/Standard_Offering/')[-1]}")
    print(f"{a.env}/{a.org}: {len(uris)} chart states under {a.folder}: {len(hits)} identical to the known-broken state")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps({"env": a.env, "org": a.org, "folder": a.folder, "like": a.like, "hits": hits}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
