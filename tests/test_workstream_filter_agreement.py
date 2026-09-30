"""The workstream filters must agree with the permission check they enforce.

`workstreams_allowed()` is the authority, and it treats an EMPTY list as full access:

    def workstreams_allowed(workstreams, workstream_id):
        if not workstreams or "*" in workstreams:   # <- empty means ALL
            return True

The `filter_*_for_auth` family in api/auth/workstream_access.py only ever checked for
"*", so an empty list made every one of them return NOTHING. Two answers to the same
question: `ctx.can_access_workstream("billing")` says yes while
`filter_snapshots_for_auth([...])` hands back an empty portal.

This is LATENT, not live -- `_workstreams_for_user` returns ["*"] for a user with no
groups, never [] -- so nothing is broken today. It is worth closing anyway, because the
whole family is one line away from silently hiding every canvas from a user the
permission check just approved, and the two functions live in different files.

Also removes `filter_kpis_for_auth`, which nothing called: executive_dashboard has its
own `_kpis_for_workstreams`, and that one already handled the empty case correctly. Of
the two implementations the unused one was the weaker.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.auth.service import workstreams_allowed  # noqa: E402
from api.auth.workstream_access import (  # noqa: E402
    filter_snapshots_for_auth,
    filter_workstreams_for_auth,
)


class _Ctx:
    """Minimal stand-in: these filters only read .workstreams."""

    def __init__(self, workstreams):
        self.workstreams = workstreams

    def can_access_workstream(self, workstream_id):
        return workstreams_allowed(self.workstreams, workstream_id)


SNAPSHOTS = [
    {"id": "rpt_bill_segment", "workstream": "billing"},
    {"id": "rpt_device_asset", "workstream": "assets"},
]
WORKSTREAMS = [{"id": "billing"}, {"id": "assets"}]


class EmptyMeansAllTests(unittest.TestCase):
    def test_the_permission_check_treats_empty_as_full_access(self):
        self.assertTrue(workstreams_allowed([], "billing"))

    def test_snapshot_filter_agrees(self):
        self.assertEqual(filter_snapshots_for_auth(SNAPSHOTS, _Ctx([])), SNAPSHOTS)

    def test_workstream_filter_agrees(self):
        self.assertEqual(filter_workstreams_for_auth(WORKSTREAMS, _Ctx([])), WORKSTREAMS)


class StarStillMeansAllTests(unittest.TestCase):
    def test_snapshots(self):
        self.assertEqual(filter_snapshots_for_auth(SNAPSHOTS, _Ctx(["*"])), SNAPSHOTS)

    def test_workstreams(self):
        self.assertEqual(filter_workstreams_for_auth(WORKSTREAMS, _Ctx(["*"])), WORKSTREAMS)


class ScopingStillScopesTests(unittest.TestCase):
    """The point of the family: a real grant must still exclude what it does not name."""

    def test_snapshots(self):
        out = filter_snapshots_for_auth(SNAPSHOTS, _Ctx(["billing"]))
        self.assertEqual([s["id"] for s in out], ["rpt_bill_segment"])

    def test_workstreams(self):
        out = filter_workstreams_for_auth(WORKSTREAMS, _Ctx(["assets"]))
        self.assertEqual([w["id"] for w in out], ["assets"])

    def test_a_grant_naming_nothing_real_shows_nothing(self):
        self.assertEqual(filter_snapshots_for_auth(SNAPSHOTS, _Ctx(["no_such_workstream"])), [])


class RemovedDuplicateTests(unittest.TestCase):
    def test_filter_kpis_for_auth_is_gone(self):
        """executive_dashboard._kpis_for_workstreams is the live implementation, and it
        is the more correct of the two."""
        import api.auth.workstream_access as wa

        self.assertFalse(hasattr(wa, "filter_kpis_for_auth"))

    def test_filter_report_library_for_auth_is_gone(self):
        """The library route scopes packs and folders with api/report_library.scope_library
        (tests/test_report_library_folders.py); a second, unused copy tested green whatever
        the route did."""
        import api.auth.workstream_access as wa

        self.assertFalse(hasattr(wa, "filter_report_library_for_auth"))


if __name__ == "__main__":
    unittest.main()
