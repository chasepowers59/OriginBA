"""Generated aliases must round-trip with the case the client asked for.

`AS TD0` was emitted unquoted, and an unquoted identifier folds to lower case in
PostgreSQL and UPPER case in Oracle. So the column the client got back was `td0` on one
engine and `TD0` on the other, while the builder looks for `TD0` and the label map in
snapshot_explorer builds itself with `TD0`. On Postgres that nulled the x axis of every
chart with a date on it -- every tick rendered as the "—" placeholder.

Measure aliases (`m0`) have the same defect pointed the other way: lower case survives
Postgres untouched, so the bug is invisible there and appears only on Oracle.

Quoting pins the alias on both engines, which is the only form that can satisfy a client
that must not care which engine answered.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.query_builder import build_query  # noqa: E402

# Every dialect the portal can be answered by. `oracle_dbt` is the one that matters most
# in production -- the Oracle-native dbt canvases -- and it is the case-folding opposite
# of Postgres, so a client that works against one must be given the same column names by
# the other. Legacy `oracle` reads CISADM, whose identifiers are UPPER_SNAKE.
DIALECTS = {
    "postgres": ("rpt_bill_segment", "Bill Date", "Bill Segment Status Code", "Amount"),
    "oracle_dbt": ("rpt_bill_segment", "Bill Date", "Bill Segment Status Code", "Amount"),
    "oracle": ("BILL_SEG_RPT_CURR", "BILL_DATE", "BSEG_STATUS_CD", "AMOUNT"),
}


def _sql(dialect: str) -> str:
    table, date_field, dim, measure = DIALECTS[dialect]
    sql, _ = build_query(
        table_name=table,
        allowed_fields={date_field, dim, measure},
        trusted_measures={measure},
        required_date_field=None,
        dimensions=[dim],
        measures=[{"field": "*", "agg": "count"}, {"field": measure, "agg": "sum"}],
        filters=[],
        limit=100,
        time_dimensions=[{"field": date_field, "grain": "month"}],
        dialect=dialect,
    )
    return sql


class AliasCaseTests(unittest.TestCase):
    def test_time_dimension_alias_is_quoted_on_every_dialect(self) -> None:
        for dialect in DIALECTS:
            with self.subTest(dialect=dialect):
                self.assertIn('AS "TD0"', _sql(dialect))

    def test_measure_aliases_are_quoted_on_every_dialect(self) -> None:
        for dialect in DIALECTS:
            with self.subTest(dialect=dialect):
                sql = _sql(dialect)
                self.assertIn('AS "m0"', sql)
                self.assertIn('AS "m1"', sql)

    def test_no_bare_alias_survives(self) -> None:
        # A bare `AS TD0` / `AS m0` is the actual defect; catch it whatever else changes.
        for dialect in DIALECTS:
            with self.subTest(dialect=dialect):
                self.assertIsNone(
                    re.search(r'\bAS\s+(?!")(TD\d|m\d)\b', _sql(dialect)),
                    "aliases must be quoted or the engine folds their case",
                )

    def test_every_dialect_returns_the_same_column_names(self) -> None:
        """The point of the fix: the client must not care which engine answered."""
        aliases = {
            dialect: sorted(re.findall(r'AS "([^"]+)"', _sql(dialect))) for dialect in DIALECTS
        }
        self.assertEqual(len(set(map(tuple, aliases.values()))), 1, aliases)


if __name__ == "__main__":
    unittest.main()
