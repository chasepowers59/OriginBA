"""jrs_adhoc_chart_props.patch/matches on real Ad Hoc chart states saved before the 2026-09-21 edits."""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts" / "jaspersoft"))
import jrs_adhoc_chart_props as cp  # noqa: E402

BACKUP = REPO / "backups" / "jaspersoft" / "adhoc_state" / "internal_Origin_DEMO_20260921-101217"
WITH_PROPS = BACKUP / "SmartCity__Report__Standard_Offering__Meter_Operations__Usage__Usage_Dashboard_files__tmpAdv_1777575074962_kpbe_files__stateXML"
NO_PROPS = BACKUP / "SmartCity__Report__Standard_Offering__Meter_Operations__Usage__Usage_Dashboard_files__tmpAdv_1777574584909_dfhj_files__stateXML"
COLOR = "plotOptions.series.dataLabels.style.color"

pytestmark = pytest.mark.skipif(not WITH_PROPS.exists(), reason="backup states not present")


def _props(state: str) -> list[tuple[str, str]]:
    return re.findall(r"<name>([^<]*)</name>\s*<value>([^<]*)</value>", state)


def test_replace_keeps_every_other_property():
    state = WITH_PROPS.read_text()
    once = cp.patch(state, [(COLOR, "contrast")])
    assert _props(once) == _props(state) + [(COLOR, "contrast")]
    twice = cp.patch(once, [(COLOR, "#1F2933")])
    assert _props(twice) == _props(state) + [(COLOR, "#1F2933")]
    assert twice.count("<advancedProperties>") == 1
    assert ("plotOptions.series.dataLabels.enabled", "true") in _props(twice)


def test_add_creates_the_list_when_the_chart_has_none():
    state = NO_PROPS.read_text()
    assert "<advancedProperties>" not in state
    new = cp.patch(state, [(COLOR, "#1F2933"), ("xAxis.labels.style.fontSize", "13px")])
    assert _props(new) == [(COLOR, "#1F2933"), ("xAxis.labels.style.fontSize", "13px")]
    assert new.index("<advancedProperties>") > new.index("<intelligentChartState")
    assert new.count("<advancedProperties>") == 1


def test_only_if_matches_exact_value():
    state = cp.patch(WITH_PROPS.read_text(), [(COLOR, "contrast")])
    assert cp.matches(state, [(COLOR, "contrast")])
    assert not cp.matches(state, [(COLOR, "#1F2933")])
    assert not cp.matches(state, [("no.such.prop", "x")])
    assert cp.matches(state, [])


def test_patch_is_a_no_op_when_the_value_is_already_there():
    state = cp.patch(WITH_PROPS.read_text(), [(COLOR, "#1F2933")])
    assert cp.patch(state, [(COLOR, "#1F2933")]) == state


def test_non_chart_state_is_refused():
    with pytest.raises(ValueError):
        cp.patch("<adhocState><table/></adhocState>", [(COLOR, "#1F2933")])
