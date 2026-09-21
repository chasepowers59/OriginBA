#!/usr/bin/env python3
"""One command per org: back it up, say what changed since the last backup, run everything with
a short threshold, compare with the baseline sweep, and write the summary a person reads.

  python3 scripts/jaspersoft/jrs_validate.py --env prod --org CityCorp \\
      [--folder /SmartCity] [--cap 20] [--workers 3] [--baseline jaspersoft/sweeps/<before>.json] \\
      [--exclude /SmartCity/Report/FDL_Trial_Balance ...] [--skip-snapshot] [--label post_upgrade]

Steps, each its own artefact under jaspersoft/sweeps/ and jaspersoft/inventory/:
  1. snapshot the org (jrs_inventory.py; the re-importable zip under backups/ is the rollback)
  2. inventory diff: this snapshot vs the previously COMMITTED tree of the same org (added /
     removed / changed resources, volatile fields ignored)
  3. run-sweep the folder: views and reports, `--cap` seconds each -- past the cap a resource is
     recorded as SLOW and the sweep moves on; nothing waits
  4. compare with --baseline (or the newest earlier sweep of this org under jaspersoft/sweeps/)
  5. write jaspersoft/sweeps/<env>_<org>_<label>_<date>.md: the summary

Prod: one org at a time (five at once saturated the 9.0 server). Runs `jrs_validate.py summary
<md>` for the files alone. Every threshold is a flag; the defaults are the tomorrow-morning ones.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile
import time

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
REPO = HERE.parents[1]
SWEEPS = REPO / "jaspersoft/sweeps"


def inventory_diff(env: str, org: str, before_tree: pathlib.Path | None) -> dict:
    """What the new snapshot changed against the previously committed tree of the same org."""
    import jrs_inventory as inv
    after = inv.INVENTORY / env / org
    if before_tree is None or not before_tree.exists():
        return {"added": [], "removed": [], "changed": [], "note": "no earlier committed snapshot to compare with"}
    a, b = inv._normalized_files(before_tree, None), inv._normalized_files(after, None)
    return {"added": sorted(set(b) - set(a)), "removed": sorted(set(a) - set(b)),
            "changed": sorted(k for k in set(a) & set(b) if a[k] != b[k])}


def newest_earlier_sweep(env: str, org: str, exclude: pathlib.Path | None) -> pathlib.Path | None:
    cands = sorted(p for p in SWEEPS.glob(f"*{env}_{org}_*.json") if p != exclude)
    return cands[-1] if cands else None


def summary_md(env: str, org: str, label: str, sweep: dict, baseline: dict | None, inv_diff: dict, cap: int, backup: str | None) -> str:
    r = sweep["results"]; c = sweep["counts"]
    slow = [x for x in r if x["outcome"] == "timeout"]; err = [x for x in r if x["outcome"] == "error"]; ab = [x for x in r if x["outcome"] == "aborted"]
    ok = [x for x in r if x["outcome"] == "ok"]; med = sorted(x["seconds"] for x in ok)[len(ok) // 2] if ok else 0
    lines = [f"# {env} / {org}: {label}", "",
             f"{sweep['server']} · {sweep['folder']} · swept {sweep['taken']} in {sweep['seconds']} s · cap {cap} s per resource",
             f"Backup: `{backup}`" if backup else "Backup: skipped (--skip-snapshot)", ""]
    verdict = "ABORTED: the link dropped mid-sweep; rerun" if ab else ("BROKEN: errors below" if err else "no errors")
    lines += ["## Verdict", "", f"**{verdict}.** {len(r)} resources: {c.get('ok', 0)} ok, {c.get('empty', 0)} empty, {len(slow)} slow (over {cap} s), {len(err)} error"
              + (f", {len(ab)} not run" if ab else "") + f". Median ok time {med:.1f} s.", ""]
    if baseline:
        b = {x["uri"]: x for x in baseline["results"]}; a = {x["uri"]: x for x in r}
        broke = [u for u in a if u in b and b[u]["outcome"] in ("ok", "empty") and a[u]["outcome"] == "error"]
        healed = [u for u in a if u in b and b[u]["outcome"] == "error" and a[u]["outcome"] in ("ok", "empty")]
        emptied = [u for u in a if u in b and b[u]["outcome"] == "ok" and a[u]["outcome"] == "empty"]
        slower = [u for u in a if u in b and b[u]["outcome"] == "ok" and a[u]["outcome"] == "timeout"]
        gone = sorted(set(b) - set(a)); new = sorted(set(a) - set(b))
        lines += [f"## Against the baseline ({baseline['server']}, {baseline['taken']})", ""]
        for title, items in (("Broke (ran before, errors now)", broke), ("Went empty", emptied), ("Now slow (ran within the cap before)", slower), ("Healed", healed), ("Missing now", gone), ("New", new)):
            lines.append(f"- **{title}: {len(items)}**" + ("".join(f"\n  - `{u}`" + (f" — {a[u].get('detail', '')[:120]}" if u in a and a[u].get("detail") else "") for u in items[:40]) if items else ""))
        lines.append("")
    lines += ["## Inventory: what changed since the last committed snapshot", "",
              f"- added {len(inv_diff['added'])}, removed {len(inv_diff['removed'])}, changed {len(inv_diff['changed'])}" + (f" — {inv_diff['note']}" if inv_diff.get("note") else "")]
    for title, items in (("Added", inv_diff["added"]), ("Removed", inv_diff["removed"]), ("Changed", inv_diff["changed"])):
        if items:
            lines.append(f"- {title}:" + "".join(f"\n  - `{u}`" for u in items[:60]) + (f"\n  - … {len(items) - 60} more" if len(items) > 60 else ""))
    lines.append("")
    if err:
        lines += ["## Errors", ""] + [f"- `{x['uri']}` — {x.get('detail', '')[:200]}" for x in err] + [""]
    if slow:
        lines += [f"## Slow (over {cap} s, not waited for)", ""] + [f"- `{x['uri']}`" for x in slow] + [""]
    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "summary":
        print(pathlib.Path(sys.argv[2]).read_text()); return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--env", required=True); ap.add_argument("--org", required=True); ap.add_argument("--folder", default="/SmartCity")
    ap.add_argument("--cap", type=int, default=20); ap.add_argument("--workers", type=int, default=3); ap.add_argument("--types", default="view,report")
    ap.add_argument("--baseline"); ap.add_argument("--label", default="check"); ap.add_argument("--skip-snapshot", action="store_true")
    ap.add_argument("--exclude", nargs="*", default=[], help="folders the exporter never finishes (Fond_Du_Lac prod: FDL_Bill_Processing_Reports__Linda_, FDL_Trial_Balance)")
    a = ap.parse_args()
    import jrs_inventory as inv
    os.environ["JRS_ENV"] = a.env; stamp = time.strftime("%Y%m%d-%H%M")
    before = None; backup = None
    if not a.skip_snapshot:
        tree = inv.INVENTORY / a.env / a.org
        if tree.exists():
            before = pathlib.Path(tempfile.mkdtemp()) / a.org; shutil.copytree(tree, before)
        print(f"[1/5] snapshot {a.env} {a.org}")
        if a.env == "prod" or a.exclude:
            inv.snapshot(a.env, None, [a.org], ["/SmartCity", "/SmartCity/Report"] if a.exclude else None, 300, tuple(a.exclude))
        else:
            inv.snapshot(a.env, a.org, None)
        s = json.load(open(inv.INVENTORY / a.env / f"{a.org}.summary.json")); backup = s["snapshot"]["backup"]
    print("[2/5] inventory diff"); inv_diff = inventory_diff(a.env, a.org, before) if not a.skip_snapshot else {"added": [], "removed": [], "changed": [], "note": "snapshot skipped"}
    out_json = SWEEPS / f"{a.env}_{a.org}_{a.label}_{stamp}.json"
    print(f"[3/5] sweep {a.folder} (cap {a.cap} s, {a.workers} workers)")
    cmd = [sys.executable, str(HERE / "jrs_run_sweep.py"), "--env", a.env, "--org", a.org, "--folder", a.folder, "--types", a.types, "--workers", str(a.workers), "--timeout", str(a.cap), "--out", str(out_json)]
    rc = subprocess.run(cmd).returncode
    if rc == 2 or not out_json.exists():
        print("sweep aborted (link dropped) -- no summary written"); return 2
    sweep = json.load(open(out_json))
    print("[4/5] compare"); base = pathlib.Path(a.baseline) if a.baseline else newest_earlier_sweep(a.env, a.org, out_json)
    baseline = json.load(open(base)) if base and base.exists() else None
    md = summary_md(a.env, a.org, a.label, sweep, baseline, inv_diff, a.cap, backup)
    out_md = out_json.with_suffix(".md"); out_md.write_text(md)
    print(f"[5/5] {out_md}\n"); print(md)
    return 1 if sweep["counts"].get("error") else 0


if __name__ == "__main__":
    raise SystemExit(main())
