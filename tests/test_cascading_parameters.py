"""A value list can be narrowed by the answers above it (cascading report parameters).

GET /snapshots/{id}/scope-options/{field}?where=<JSON filters> lists only the values that
occur under those filters, e.g. the customer classes in the chosen bill cycle. The filters
go through the query builder, so an unknown field or operator is refused, exactly as in a
query; a person's row rules still apply on top.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest import mock

from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import snapshot_explorer as se  # noqa: E402
from api.auth.dependencies import AuthContext  # noqa: E402


def _ctx(rules=()):
    return AuthContext(id="u", email="u@x.gov", display_name="u", role="editor", client_id="dev", organization_id="dev",
                       organization_name="Dev", permissions={"snapshots:query", "snapshots:read"}, workstreams=["*"],
                       row_rules=tuple(rules))


class CascadingTests(unittest.TestCase):
    def setUp(self):
        self.executed = []

        def run(sql, binds=None, **_):
            self.executed.append((sql, binds))
            return ["v", "n"], [["Residential", 3]]
        self.patches = [
            mock.patch.object(se, "require_org_for_data", return_value="dev"),
            mock.patch.object(se, "snapshot_backend", return_value=("postgres", "postgres", "reporting")),
            mock.patch.object(se, "_row_estimate", return_value=10),
            mock.patch("api.warehouse_db.execute_query", side_effect=run),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in self.patches:
            p.stop()

    def _options(self, where, ctx=None):
        return se.snapshot_scope_options("rpt_bill_segment", "Customer Class", where=json.dumps(where) if where is not None else None,
                                         ctx=ctx or _ctx())

    def test_the_list_is_narrowed_by_the_answers_above_it(self):
        out = self._options([{"field": "Bill Cycle", "op": "eq", "value": "C1"}])
        sql, binds = self.executed[-1]
        self.assertIn('"Bill Cycle" =', sql)
        self.assertIn("C1", list(binds.values()))
        self.assertEqual(out["values"], ["Residential"])

    def test_without_answers_the_list_is_unchanged(self):
        self._options(None)
        self.assertIn("SELECT DISTINCT", self.executed[-1][0])

    def test_an_unknown_field_is_refused(self):
        with self.assertRaises(HTTPException) as err:
            self._options([{"field": "Made Up", "op": "eq", "value": "x"}])
        self.assertEqual(err.exception.status_code, 400)

    def test_row_rules_still_apply(self):
        self._options([{"field": "Bill Cycle", "op": "eq", "value": "C1"}],
                      ctx=_ctx(({"field": "Service Type", "values": ["Water"]},)))
        self.assertIn('"Service Type" IN', self.executed[-1][0])


if __name__ == "__main__":
    unittest.main()
