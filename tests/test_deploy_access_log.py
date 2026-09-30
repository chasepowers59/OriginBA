"""B-10: every deployed launch of the API runs uvicorn without its own access log. That log
prints each request path in full, and an embed link's path carries its token (a credential);
the API's request log (api/request_tracing.py) already records every request, token masked."""
from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class AccessLogTests(unittest.TestCase):
    def test_every_launcher_turns_off_uvicorns_access_log(self):
        for launcher in ("Procfile", "deploy/Dockerfile.api"):
            text = (ROOT / launcher).read_text()
            with self.subTest(launcher=launcher):
                self.assertIn("uvicorn api.app:app", text)
                self.assertIn("--no-access-log", text)


if __name__ == "__main__":
    unittest.main()
