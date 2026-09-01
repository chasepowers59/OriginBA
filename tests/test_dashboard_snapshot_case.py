"""A saved dashboard tile must keep the snapshot id it was given.

`_validate_tiles` upper-cased `snapshot_id` -- correct while every snapshot was an
Oracle table, wrong for a dbt canvas, which is lowercase `rpt_*`. Measured against the
running API: posting a tile for `rpt_bill_segment` stored `RPT_BILL_SEGMENT`, and
looking that stored id back up returned 404. The dashboard saved happily and could not
render, on every canvas-backed org.

get_snapshot already carries a comment about precisely this ("Upper was right while
every snapshot was an Oracle table; a dbt canvas is lowercase rpt_*"), so the READER was
fixed and the WRITER was missed. The reader now also tries lower case, which heals the
rows written while the writer was wrong -- there is no migration for user-saved state.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.saved_dashboards import _validate_tiles  # noqa: E402


def _tile(snapshot_id: str) -> dict:
    return {"slot": 0, "title": "t", "visual": "chart", "snapshot_id": snapshot_id}


def test_a_dbt_canvas_id_keeps_its_lower_case() -> None:
    out = _validate_tiles([_tile("rpt_bill_segment")])
    assert out[0]["snapshot_id"] == "rpt_bill_segment"


def test_a_cisadm_id_keeps_its_upper_case() -> None:
    out = _validate_tiles([_tile("FT_RPT_CURR")])
    assert out[0]["snapshot_id"] == "FT_RPT_CURR"


def test_a_missing_snapshot_id_is_still_rejected() -> None:
    from api.saved_dashboards import DashboardError

    with pytest.raises(DashboardError):
        _validate_tiles([_tile("")])


def test_an_untitled_tile_does_not_get_a_shouted_id_as_its_title() -> None:
    tile = {"slot": 0, "visual": "chart", "snapshot_id": "rpt_bill_segment"}
    assert _validate_tiles([tile])[0]["title"] == "rpt_bill_segment"


class TestReaderHealsWhatTheWriterBroke:
    """Dashboards saved before the fix hold an upper-cased canvas id."""

    def test_get_snapshot_resolves_an_upper_cased_canvas_id(self) -> None:
        from api.snapshot_catalog import CatalogError, get_snapshot

        try:
            canonical = get_snapshot("rpt_bill_segment", "dev")
        except CatalogError:
            pytest.skip("dbt catalog not built in this checkout")
        assert get_snapshot("RPT_BILL_SEGMENT", "dev")["table_name"] == canonical["table_name"]
