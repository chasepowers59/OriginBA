"""A breakdown of NET money ranks its groups by size either way, not by value.

Ellensburg 2026-09-29, 30 days: Finance "Adjustment dollars" nets to $17,350 while its six
bars (the six largest POSITIVE groups) summed ~$127K; the credits (SYNC-DEP -$12,796, SYNC
-$8,532) ranked last and never drew. A card opts in with trend "rank": "magnitude"; the
default ranking is unchanged, so explorer results and the aggregate routing keep theirs.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import kpi_runner  # noqa: E402
from api.query_builder import build_query  # noqa: E402

ARGS = dict(table_name="rpt_financial_txn", allowed_fields={"Adjustment Type", "Current Amount"},
            trusted_measures={"Current Amount"}, dimensions=["Adjustment Type"],
            measures=[{"field": "Current Amount", "agg": "sum"}], filters=[], limit=6)


class RankByMagnitudeTests(unittest.TestCase):
    def test_both_engines_rank_by_absolute_size(self):
        for dialect, schema in (("postgres", "reporting"), ("oracle_dbt", "ORIGINBA_REPORTING")):
            sql, _ = build_query(**ARGS, dialect=dialect, schema=schema, rank_by_magnitude=True)
            self.assertIn('ORDER BY ABS(SUM("Current Amount")) DESC NULLS LAST, "Adjustment Type"', sql, dialect)

    def test_the_default_ranking_is_unchanged(self):
        sql, _ = build_query(**ARGS, dialect="postgres", schema="reporting")
        self.assertIn('ORDER BY "m0" DESC NULLS LAST', sql)

    def test_a_card_opts_in_through_its_query_spec(self):
        seen = {}

        def capture(**kw):
            seen.update(kw)
            return "select 1", {}
        with mock.patch.object(kpi_runner, "build_query", side_effect=capture), \
             mock.patch.object(kpi_runner, "get_snapshot", return_value={"table_name": "rpt_financial_txn"}), \
             mock.patch.object(kpi_runner, "allowed_fields", return_value=set()), \
             mock.patch.object(kpi_runner, "snapshot_backend", return_value=("oracle", "oracle_dbt", "ORIGINBA_REPORTING")), \
             mock.patch.object(kpi_runner, "execute_query", return_value=([], [])):
            kpi_runner.run_kpi_query("rpt_financial_txn", {**ARGS, "rank": "magnitude"}, "Accounting Date",
                                     "2026-05-19", "2026-06-18", organization_id="ellensburg")
        self.assertTrue(seen["rank_by_magnitude"])


if __name__ == "__main__":
    unittest.main()
