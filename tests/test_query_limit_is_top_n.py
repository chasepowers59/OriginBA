"""A LIMIT with no ORDER BY returns an ARBITRARY slice, not the biggest one.

Every executive KPI trend asks for `limit: 6`, and build_query emitted no ORDER BY at
all, so the six groups that survived were whatever the planner happened to produce first.

Measured on the Demo 25.4 warehouse: "Active service agreements" reads 1,486 across 43
SA Types, whose real top four are Electric Residential (399), Gas Residential (289),
Waste Water Residential (267) and Water Residential (267) -- 1,222 of the 1,486. The card
was drawing types ranked 13th and 14th (10 and 9) and none of the top four, while looking
exactly like a breakdown of the headline number. A chart that cannot be trusted to show
the big categories is worse than no chart.

So a limited aggregate is ordered:
  - by the first measure, descending, so LIMIT means "the biggest N"; and
  - by the time bucket, descending, when the query has one, so LIMIT means "the most
    recent N" -- the client re-sorts those chronologically for display.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.query_builder import QueryValidationError, build_query  # noqa: E402

FIELDS = {"Bill Date", "SA Type", "Amount"}


DIALECT_FIELDS = {
    "postgres": ("rpt_service_agreement", "Bill Date", "SA Type", "Amount"),
    "oracle_dbt": ("rpt_service_agreement", "Bill Date", "SA Type", "Amount"),
}


def _sql(dialect: str = "postgres", *, time_dim: bool = False, measures=None) -> str:
    table, date_field, dim, measure = DIALECT_FIELDS[dialect]
    sql, _ = build_query(
        table_name=table,
        allowed_fields={date_field, dim, measure},
        trusted_measures={measure},
        dimensions=[dim],
        measures=measures if measures is not None else [{"field": "*", "agg": "count"}],
        filters=[],
        limit=6,
        time_dimensions=[{"field": date_field, "grain": "month"}] if time_dim else None,
        dialect=dialect,
        # legacy oracle reads CISADM; the canvas dialects read the reporting schema
        schema="CISADM" if dialect == "oracle" else "reporting",
    )
    return sql


class LimitIsTopNTests(unittest.TestCase):
    def test_grouped_query_orders_by_the_first_measure_descending(self) -> None:
        for dialect in ("postgres", "oracle_dbt"):
            with self.subTest(dialect=dialect):
                self.assertIn('ORDER BY "m0" DESC', _sql(dialect))

    def test_a_time_bucketed_query_takes_the_most_recent(self) -> None:
        # Ranking a date by size would drop the interesting months, not the old ones.
        self.assertIn('ORDER BY "TD0" DESC', _sql(time_dim=True))

    def test_nulls_sort_last_so_they_cannot_take_the_top_slots(self) -> None:
        """DESC defaults to NULLS FIRST in BOTH Postgres and Oracle.

        Measured on Demo 25.4: `... ORDER BY m0 DESC LIMIT 5` over bill-segment status
        returns Error (null) first, ahead of Frozen at 868,262.10. Under `limit: 6` a
        handful of null-measure groups would evict the real leaders -- the very bug this
        ordering exists to prevent, wearing a different hat.
        """
        for dialect in ("postgres", "oracle_dbt"):
            with self.subTest(dialect=dialect):
                self.assertIn('DESC NULLS LAST', _sql(dialect))
                self.assertIn('DESC NULLS LAST', _sql(dialect, time_dim=True))

    def test_ordering_precedes_the_row_limit(self) -> None:
        sql = _sql()
        self.assertLess(sql.index("ORDER BY"), sql.index("FETCH FIRST"), sql)

    def test_multi_measure_ranks_on_the_first_measure(self) -> None:
        sql = _sql(measures=[{"field": "*", "agg": "count"}, {"field": "Amount", "agg": "sum"}])
        self.assertIn('ORDER BY "m0" DESC', sql)

    def test_a_measure_is_required_so_there_is_always_something_to_rank_by(self) -> None:
        # This is what lets the ordering be unconditional rather than a special case.
        with self.assertRaises(QueryValidationError):
            build_query(
                table_name="rpt_service_agreement",
                allowed_fields=FIELDS,
                trusted_measures=set(),
                    dimensions=["SA Type"],
                measures=[],
                filters=[],
                limit=6,
                dialect="postgres",
                schema="reporting",
            )


if __name__ == "__main__":
    unittest.main()
