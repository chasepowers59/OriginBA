"""A module a client does not use is hidden from that client, by measurement.

originba_dbt/scripts/client_capability_profile.py measures each client's own CISADM and writes
config/client_capabilities.json: Odessa printed 2 letters in a year (2026-10-01), so the
letters hub would open empty there. The portal reads the switch for the ACTIVE organization:
the nav drops the module (portal config "modules") and the API refuses it, so a typed URL
finds nothing either. A client not measured, or a switch the run could not decide, keeps the
module: a missing measurement never hides a working page.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import client_capabilities as caps  # noqa: E402
from api.auth.dependencies import AuthContext, get_auth_context  # noqa: E402
from api.auth.permissions import permissions_for_role  # noqa: E402
from api.letters import routes  # noqa: E402
from api.portal_config import config_for_organization  # noqa: E402

MEASURED = {
    "odessa": {"portal_org_id": "odessa", "features": {"letters": False}},
    "fond_du_lac": {"portal_org_id": "fond_du_lac", "features": {"letters": True}},
    "newark": {"portal_org_id": "newark", "features": {"letters": None}},
    "unreached": {"last_error": "DPY-6005"},
}


class CapabilityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(MEASURED, self.tmp)
        self.tmp.close()
        self.path = mock.patch.object(caps, "CAPABILITIES_PATH", Path(self.tmp.name))
        self.path.start()

    def tearDown(self):
        self.path.stop()
        Path(self.tmp.name).unlink()

    def test_a_client_measured_without_letters_has_no_letters_module(self):
        self.assertFalse(caps.module_enabled("odessa", "letters"))
        self.assertTrue(caps.module_enabled("fond_du_lac", "letters"))

    def test_no_measurement_never_hides_a_module(self):
        self.assertTrue(caps.module_enabled("newark", "letters"))        # undecided
        self.assertTrue(caps.module_enabled("demo25", "letters"))        # not a measured client
        self.assertTrue(caps.module_enabled(None, "letters"))
        with mock.patch.object(caps, "CAPABILITIES_PATH", Path("/nonexistent/caps.json")):
            self.assertTrue(caps.module_enabled("odessa", "letters"))

    def test_the_portal_config_carries_the_switches(self):
        with mock.patch("api.portal_config.get_organization", return_value={"display_name": "Odessa"}):
            self.assertEqual(config_for_organization("odessa")["modules"], {"letters": False})

    def test_the_letters_api_refuses_a_client_that_does_not_use_letters(self):
        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[get_auth_context] = lambda: AuthContext(
            id="u1", email="u1@utility.gov", display_name="u1", role="editor", client_id="smartcity",
            organization_id="odessa", organization_name="Odessa",
            permissions=set(permissions_for_role("editor")), workstreams=["*"], row_rules=())
        with mock.patch.object(routes, "require_org_for_data", return_value="odessa"):
            out = TestClient(app).get("/portal/letters", params={"from": "2026-09-01", "to": "2026-09-30"})
        self.assertEqual(out.status_code, 404)
        self.assertIn("does not use", out.json()["detail"])


if __name__ == "__main__":
    unittest.main()
