"""The validation summary, built offline from real sweep files: the verdict, the against-baseline
lists, and the inventory diff read from two trees."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts/jaspersoft"))
import jrs_validate as v  # noqa: E402

A = ROOT / "jaspersoft/sweeps/test_Fond_Du_Lac_20260918.json"
B = ROOT / "jaspersoft/sweeps/test_Fond_Du_Lac_20260919_calibrated.json"


def test_summary_names_the_verdict_the_baseline_movement_and_the_slow_list():
    base, now = json.load(open(A)), json.load(open(B))
    md = v.summary_md("test", "Fond_Du_Lac", "post", now, base, {"added": ["/x"], "removed": [], "changed": ["/y", "/z"]}, 60, "backups/x.zip")
    assert md.startswith("# test / Fond_Du_Lac: post") and "**BROKEN: errors below.**" in md
    assert "13 slow (over 60 s)" in md and "## Slow (over 60 s, not waited for)" in md
    assert "- **Healed: 0**" in md or "- **Healed:" in md
    assert "- **Now slow (ran within the cap before):" in md
    assert "added 1, removed 0, changed 2" in md and "`/y`" in md
    assert "Customer___SA_s_start_stop_last_6_months" in md          # the one real error, listed under Errors


def test_summary_without_a_baseline_and_with_an_aborted_run():
    now = json.load(open(B)); now = {**now, "results": [{**r, "outcome": "aborted"} if i == 0 else r for i, r in enumerate(now["results"])]}
    md = v.summary_md("prod", "CityCorp", "check", now, None, {"added": [], "removed": [], "changed": [], "note": "first snapshot"}, 20, None)
    assert "ABORTED" in md and "Backup: skipped" in md and "first snapshot" in md and "Against the baseline" not in md


def test_inventory_diff_reads_two_trees(tmp_path, monkeypatch):
    import jrs_inventory as inv
    monkeypatch.setattr(inv, "INVENTORY", tmp_path / "inv")
    before = tmp_path / "before" / "Org"; after = tmp_path / "inv" / "test" / "Org"
    for base, files in ((before, {"a.xml": "<r><label>A</label><updateDate>1</updateDate></r>", "b.xml": "<r>B</r>"}),
                        (after, {"a.xml": "<r><label>A</label><updateDate>2</updateDate></r>", "c.xml": "<r>C</r>"})):
        (base / "resources/SmartCity").mkdir(parents=True)
        for n, t in files.items(): (base / "resources/SmartCity" / n).write_text(t)
    d = v.inventory_diff("test", "Org", before)
    assert d["added"] == ["/SmartCity/c.xml"] and d["removed"] == ["/SmartCity/b.xml"] and d["changed"] == []   # updateDate is volatile
