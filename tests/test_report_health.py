"""The report-health sweep's verdicts (scripts/check_report_health.py).

A report that answers with nothing, with one "not recorded" bar, or with zeros passes every
other test: the query ran. Each such answer found on Ellensburg (2026-09-30) was a real bug
(an empty source column, a constant axis, a missing open-only filter) or a fact about the
client worth writing down. The verdict is a pure function so it is tested without a warehouse.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from check_report_health import verdict  # noqa: E402


def test_an_empty_answer():
    assert verdict([], "Bill Status") == "EMPTY"


def test_one_bar_that_says_nothing_was_recorded():
    assert verdict([{"Route": None, "m0": 33092}], "Route") == "ONLY-NOT-RECORDED"
    assert verdict([{"Route": "Not recorded", "m0": 5}], "Route") == "ONLY-NOT-RECORDED"


def test_every_value_zero_or_missing():
    assert verdict([{"Asset Type": "Meter", "m0": 0}, {"Asset Type": "Pole", "m0": None}],
                   "Asset Type") == "ALL-ZERO"


def test_one_real_group():
    assert verdict([{"Bill Status": "Complete", "m0": 720187}], "Bill Status") == "ONE-GROUP"


def test_a_healthy_answer():
    assert verdict([{"Cycle": "C1", "m0": 3}, {"Cycle": "C2", "m0": 0}], "Cycle") is None
