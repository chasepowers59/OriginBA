"""The governed builder must not assume CISADM.

`build_query` defaulted to `dialect="oracle"` and `schema="CISADM"` -- the world it was
born in, when every query read the legacy snapshots. The canvases changed that: a query
now belongs to postgres, oracle_dbt or legacy oracle, and which one is a property of the
ORG and the snapshot, resolved by snapshot_backend().

All three production callers already pass both explicitly, so the defaults were never
used -- they only sat there waiting for the next caller to forget, and to send that
query silently to CISADM with Oracle syntax. The same class of assumption already cost
the dashboard its cross-filter (`_cross_filter` upper-cased field names because CISADM
columns are UPPER_SNAKE) and the SQL workspace its aggregates.

Requiring both makes the choice visible at every call site.
"""
from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.query_builder import build_query  # noqa: E402

SIG = inspect.signature(build_query)


@pytest.mark.parametrize("param", ["schema", "dialect"])
def test_has_no_legacy_default(param: str) -> None:
    assert SIG.parameters[param].default is inspect.Parameter.empty, (
        f"build_query({param}=...) must be explicit: a default sends a forgetful "
        "caller's query to the legacy CISADM path without saying so"
    )


def test_omitting_them_is_an_error_rather_than_a_silent_cisadm_query() -> None:
    with pytest.raises(TypeError):
        build_query(
            table_name="rpt_bill",
            allowed_fields={"Bill Date"},
            trusted_measures=set(),
            dimensions=[],
            measures=[{"field": "*", "agg": "count"}],
            filters=[],
            limit=10,
        )
