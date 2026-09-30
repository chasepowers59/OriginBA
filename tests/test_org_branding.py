"""Each client organization can carry its own brand: name, logo, accent colours.

An organization's record in config/portal_organizations.json may hold
    "branding": {"brand": {"name": ..., "logo_src": "/clients/newark.png", ...},
                 "theme": {"accent_from": "#0a7d3b", ...}}
/portal/config merges it over the portal default for that organization only. Colours must
be hex or rgba, and a logo must be a path the portal itself serves (starting with '/'), so
a config file cannot make the portal load from elsewhere; anything invalid is ignored.
PDFs carry the organization's logo when it is a PNG the portal serves.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import portal_config as pc  # noqa: E402

ORGS = {
    "newark": {"id": "newark", "display_name": "Newark", "branding": {
        "brand": {"name": "Newark Water Analytics", "logo_src": "/origin-logo.png", "tagline": 42},
        "theme": {"accent_from": "#0a7d3b", "accent_to": "javascript:alert(1)", "made_up": "#fff"}}},
    "evil": {"id": "evil", "display_name": "Evil", "branding": {"brand": {"logo_src": "https://tracker.test/x.png"}}},
    "plain": {"id": "plain", "display_name": "Plain"},
}


class BrandingTests(unittest.TestCase):
    def _config(self, org):
        with mock.patch.object(pc, "get_organization", side_effect=lambda o: ORGS.get(o)):
            return pc.config_for_organization(org)

    def test_an_organization_brand_is_merged_over_the_default(self):
        c = self._config("newark")
        self.assertEqual(c["brand"]["name"], "Newark Water Analytics")
        self.assertEqual(c["brand"]["logo_src"], "/origin-logo.png")
        self.assertEqual(c["theme"]["accent_from"], "#0a7d3b")
        self.assertEqual(c["organization_name"], "Newark")

    def test_invalid_values_are_ignored(self):
        c = self._config("newark")
        self.assertEqual(c["theme"]["accent_to"], pc.load_portal_config()["theme"]["accent_to"])
        self.assertNotIn("made_up", c["theme"])
        self.assertEqual(c["brand"]["tagline"], pc.load_portal_config()["brand"]["tagline"])

    def test_a_logo_from_elsewhere_is_refused(self):
        self.assertEqual(self._config("evil")["brand"]["logo_src"], pc.load_portal_config()["brand"]["logo_src"])

    def test_other_organizations_keep_the_default(self):
        self.assertEqual(self._config("plain")["brand"]["name"], pc.load_portal_config()["brand"]["name"])

    def test_pdfs_use_the_organizations_png_logo(self):
        with mock.patch.object(pc, "get_organization", side_effect=lambda o: ORGS.get(o)):
            self.assertEqual(pc.pdf_logo_path("newark").name, "origin-logo.png")
            self.assertIsNone(pc.pdf_logo_path("evil"))


if __name__ == "__main__":
    unittest.main()
