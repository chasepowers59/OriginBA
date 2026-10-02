"""Two customer counts, each named for what it is (2026-10-02).
"How many customers do we have?" ran the vetted metric that counts EVERY account in CIS,
open or closed (92.8K at Ellensburg), while the Home card "Billing accounts" shows the
accounts with at least one active service agreement (12.2K). The card names which one it
shows (api/executive_dashboard.py); the metrics now do too: "how many customers" means the
billing accounts, and the all-accounts count answers to "accounts in CIS".
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.nlq_metrics import match_metric  # noqa: E402


class CustomerCountMetrics(unittest.TestCase):
    def test_how_many_customers_means_billing_accounts(self):
        for q in ("How many customers do we have?", "total customers", "customer count", "how many billing accounts"):
            with self.subTest(q=q):
                m = match_metric(q)
                self.assertIsNotNone(m)
                self.assertEqual(m.id, "billing_accounts")
                query = m.build({})["query"]
                self.assertIn({"field": "Active SA Count", "op": "gte", "value": 1}, query["filters"])
        self.assertIn("active service agreement", match_metric("how many customers").label.lower())

    def test_every_account_in_cis_is_its_own_metric_and_says_so(self):
        for q in ("How many accounts are in CIS?", "total accounts in CIS", "number of accounts"):
            with self.subTest(q=q):
                m = match_metric(q)
                self.assertIsNotNone(m)
                self.assertEqual(m.id, "total_customers")
                self.assertEqual(m.build({})["query"]["filters"], [])
        self.assertIn("open or closed", match_metric("accounts in CIS").label.lower())


if __name__ == "__main__":
    unittest.main()
