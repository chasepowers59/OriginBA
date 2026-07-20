# OriginBA snapshot explorer — live demo integration tests
# Requires VPN + DEMO_* credentials in .env and uvicorn on :8000

import json
import os
import unittest
import urllib.error
import urllib.request


API_BASE = os.getenv("ORIGINBA_API_URL", "http://localhost:8000")
RUN_LIVE = os.getenv("ORIGINBA_LIVE_DEMO_TESTS", "").lower() in {"1", "true", "yes"}


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


@unittest.skipUnless(RUN_LIVE, "Set ORIGINBA_LIVE_DEMO_TESTS=1 to run live demo API tests")
class LiveDemoSnapshotTests(unittest.TestCase):
    def test_workflow_queue_todo_by_status(self) -> None:
        result = _post(
            "/snapshots/WORKFLOW_QUEUE_RPT_CURR/query",
            {
                "dimensions": ["ENTRY_STATUS_DESC"],
                "measures": [{"field": "*", "agg": "count"}],
                "filters": [
                    {"field": "TD_CRE_DTTM", "op": "between", "value": ["2024-01-01", "2026-12-31"]},
                    {"field": "QUEUE_SOURCE", "op": "eq", "value": "TODO"},
                ],
                "limit": 20,
            },
        )
        self.assertGreater(result["row_count"], 0)

    def test_bseg_usage_by_class(self) -> None:
        result = _post(
            "/snapshots/BSEG_BILLED_USAGE_RPT_CURR/query",
            {
                "dimensions": ["CUST_CL_DESC"],
                "measures": [{"field": "TOTAL_BILL_SQ", "agg": "sum"}],
                "filters": [{"field": "BILL_DT", "op": "between", "value": ["2024-01-01", "2026-12-31"]}],
                "limit": 20,
            },
        )
        self.assertGreater(result["row_count"], 0)


if __name__ == "__main__":
    unittest.main()
