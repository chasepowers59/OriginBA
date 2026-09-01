"""H4 (2026-09-01): a protected column was a queryable dimension.

`output/catalog_cisadm.json` declared `ALERT_INFO` on ACCT_CUSTOMER_RPT_CURR and
`ACCT_ALERT_INFO` on CASE_PREM_CONTACT_RPT_CURR with `role: dimension`, and
`build_query` allow-lists exactly the catalog's field set — so any role `user` at a
cisadm org could read them through `POST /snapshots/{id}/query`, while the SQL
workspace fenced the very same column. Two policies, one column, opposite answers.

Contract: the secrets denylist is enforced at the ALLOW-LIST, so a regenerated or
hand-edited catalog can never re-expose a protected column, and no shipped catalog
declares one.
"""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.snapshot_catalog import (  # noqa: E402
    PROTECTED_COLUMNS,
    allowed_fields,
    is_protected_column,
)


class AllowListRefusesProtectedColumnsTests(unittest.TestCase):
    def test_protected_columns_are_dropped_from_the_allow_list(self):
        snapshot = {
            "id": "ACCT_CUSTOMER_RPT_CURR",
            "fields": [
                {"id": "ACCT_ID", "role": "dimension"},
                {"id": "ALERT_INFO", "role": "dimension"},
                {"id": "ACCT_ALERT_INFO", "role": "dimension"},
                {"id": "MICR_ID", "role": "dimension"},
                {"id": "WEB_PASSWD", "role": "dimension"},
                {"id": "CUR_AMT", "role": "measure"},
            ],
        }
        allowed = allowed_fields(snapshot)
        self.assertEqual(allowed, {"ACCT_ID", "CUR_AMT"})

    def test_the_rule_matches_title_case_canvas_names_too(self):
        snapshot = {"fields": [
            {"id": "Account ID"},
            {"id": "Alert Info"},
            {"id": "Bank Routing Number (MICR ID)"},
        ]}
        self.assertEqual(allowed_fields(snapshot), {"Account ID"})

    def test_an_ordinary_column_that_merely_contains_a_word_is_kept(self):
        # "Alert" alone is not a secret — the DQ worklist has legitimate alert
        # counts, and over-blocking would quietly delete real columns.
        snapshot = {"fields": [{"id": "Open Alert Count"}, {"id": "Has Alert"}]}
        self.assertEqual(allowed_fields(snapshot), {"Open Alert Count", "Has Alert"})

    def test_the_denylist_covers_every_secret_the_fence_knows(self):
        joined = " ".join(PROTECTED_COLUMNS).lower()
        for secret in ("micr", "web_passwd", "alert_info", "ext_acct_id"):
            self.assertIn(secret.split("_")[0], joined)


class ShippedCatalogsAreCleanTests(unittest.TestCase):
    @staticmethod
    def _field_ids(node, out):
        """Every {'id': ...} in the document, whatever the catalog's shape."""
        if isinstance(node, dict):
            if "id" in node and isinstance(node["id"], str):
                out.append(node["id"])
            for v in node.values():
                ShippedCatalogsAreCleanTests._field_ids(v, out)
        elif isinstance(node, list):
            for v in node:
                ShippedCatalogsAreCleanTests._field_ids(v, out)
        return out

    def test_no_catalog_declares_a_protected_column(self):
        offenders = []
        for path in sorted((ROOT / "output").glob("catalog*.json")):
            for fid in self._field_ids(json.loads(path.read_text()), []):
                if is_protected_column(fid):
                    offenders.append(f"{path.name}:{fid}")
        self.assertEqual(offenders, [], f"protected columns in a shipped catalog: {offenders}")


if __name__ == "__main__":
    unittest.main()
