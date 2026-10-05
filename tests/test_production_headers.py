"""What a production response says about itself (production-readiness audit, 2026-10-05).

The API set no security headers, served its interactive docs and full schema to anyone,
and always allowed credentialed calls from localhost:3000. Now every response carries
nosniff, deny-framing, no-referrer and a deny-all content policy (the API serves JSON and
files, never pages), plus HSTS outside development; the docs exist only in development;
the localhost origins are allowed only in development.
"""
from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from api import app as app_module  # noqa: E402


class Headers(unittest.TestCase):
    def test_every_response_carries_the_security_headers(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            r = TestClient(app_module.app).get("/health")
        self.assertEqual(r.headers.get("x-content-type-options"), "nosniff")
        self.assertEqual(r.headers.get("x-frame-options"), "DENY")
        self.assertEqual(r.headers.get("referrer-policy"), "no-referrer")
        self.assertIn("default-src 'none'", r.headers.get("content-security-policy", ""))
        self.assertIn("max-age=", r.headers.get("strict-transport-security", ""))

    def test_no_hsts_on_a_development_machine(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            r = TestClient(app_module.app).get("/health")
        self.assertIsNone(r.headers.get("strict-transport-security"))


class DocsAndOrigins(unittest.TestCase):
    def test_the_docs_exist_only_in_development(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            self.assertEqual(app_module._docs_urls(), {"docs_url": None, "redoc_url": None, "openapi_url": None})
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            self.assertEqual(app_module._docs_urls()["docs_url"], "/docs")

    def test_localhost_is_an_allowed_origin_only_in_development(self):
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "production", "PORTAL_CORS_ORIGINS": ""}):
            prod = app_module._cors_origins()
        with mock.patch.dict(os.environ, {"ENVIRONMENT": "development", "PORTAL_CORS_ORIGINS": ""}):
            dev = app_module._cors_origins()
        self.assertFalse([o for o in prod if "localhost" in o or "127.0.0.1" in o], prod)
        self.assertIn("http://localhost:3000", dev)


if __name__ == "__main__":
    unittest.main()
