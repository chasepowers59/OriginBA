"""Tests for governed snapshot query builder."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.query_builder import QueryValidationError, build_query  # noqa: E402
from api.snapshot_catalog import allowed_fields, get_snapshot  # noqa: E402


class QueryBuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        catalog_path = ROOT / "output" / "snapshot_explorer_catalog.json"
        if not catalog_path.exists():
            raise unittest.SkipTest("Run scripts/build_snapshot_explorer_catalog.py first")

    def _snapshot(self, name: str):
        snap = get_snapshot(name)
        return snap, allowed_fields(snap)

    def test_workflow_queue_requires_date_filter(self) -> None:
        snap, fields = self._snapshot("WORKFLOW_QUEUE_RPT_CURR")
        with self.assertRaises(QueryValidationError):
            build_query(
                table_name=snap["table_name"],
                allowed_fields=fields,
                trusted_measures=set(),
                required_date_field=snap["required_date_field"],
                dimensions=["ENTRY_STATUS_DESC"],
                measures=[{"field": "*", "agg": "count"}],
                filters=[],
                limit=100,
            )

    def test_workflow_queue_count_by_status(self) -> None:
        snap, fields = self._snapshot("WORKFLOW_QUEUE_RPT_CURR")
        sql, binds = build_query(
            table_name=snap["table_name"],
            allowed_fields=fields,
            trusted_measures=set(),
            required_date_field=snap["required_date_field"],
            dimensions=["ENTRY_STATUS_DESC"],
            measures=[{"field": "*", "agg": "count"}],
            filters=[
                {"field": "TD_CRE_DTTM", "op": "between", "value": ["2025-01-01", "2025-06-01"]},
                {"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"},
            ],
            limit=100,
        )
        self.assertIn("COUNT(*) AS m0", sql)
        self.assertIn("ENTRY_STATUS_DESC", sql)
        self.assertIn("QUEUE_SOURCE = :b1", sql)
        self.assertEqual(binds["b1"], "TODO")

    def test_bseg_sum_requires_trusted_measure(self) -> None:
        snap, fields = self._snapshot("BSEG_BILLED_USAGE_RPT_CURR")
        with self.assertRaises(QueryValidationError):
            build_query(
                table_name=snap["table_name"],
                allowed_fields=fields,
                trusted_measures={"TOTAL_BILL_SQ"},
                required_date_field=snap["required_date_field"],
                dimensions=["CUST_CL_DESC"],
                measures=[{"field": "READ_LINE_COUNT", "agg": "sum"}],
                filters=[{"field": "BILL_DT", "op": "between", "value": ["2025-01-01", "2025-06-01"]}],
                limit=100,
            )

    def test_ft_sum_cur_amt(self) -> None:
        snap, fields = self._snapshot("FT_RPT_CURR")
        sql, _ = build_query(
            table_name=snap["table_name"],
            allowed_fields=fields,
            trusted_measures={"CUR_AMT"},
            required_date_field=snap["required_date_field"],
            dimensions=["FT_TYPE_FLG_DESC"],
            measures=[{"field": "CUR_AMT", "agg": "sum"}],
            filters=[{"field": "ACCOUNTING_DT", "op": "between", "value": ["2025-01-01", "2025-06-01"]}],
            limit=50,
        )
        self.assertIn("SUM(CUR_AMT) AS m0", sql)

    def test_rejects_unknown_field(self) -> None:
        snap, fields = self._snapshot("FT_RPT_CURR")
        with self.assertRaises(QueryValidationError):
            build_query(
                table_name=snap["table_name"],
                allowed_fields=fields,
                trusted_measures={"CUR_AMT"},
                required_date_field=snap["required_date_field"],
                dimensions=["NOT_A_REAL_FIELD"],
                measures=[{"field": "*", "agg": "count"}],
                filters=[{"field": "ACCOUNTING_DT", "op": "between", "value": ["2025-01-01", "2025-06-01"]}],
                limit=10,
            )


if __name__ == "__main__":
    unittest.main()
