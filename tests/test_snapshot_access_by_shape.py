"""A workstream grant is evaluated against the caller's own catalog.

`snapshot_workstream()` once called `get_snapshot()` with NO organization_id. When two
catalogs existed that resolved every authorization lookup against the default one, and
a user granted "finance" was refused their own finance snapshots on every org that used
the other -- a lockout, and a silent one, because their metrics and tiles filtered to
empty rather than erroring. Invisible in development because "*" and an empty grant
both mean full access and never reach the comparison.

There is one catalog now (tests/test_single_catalog_shape.py), which removes the way
that bug happened. The org is still threaded through, because that is what the lookup
MEANS, and these tests pin the decision itself: a restricted grant reaches its own
workstream, is refused another, and is refused an unknown snapshot.
"""

from __future__ import annotations

import dataclasses
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _ids(workstream: str | None = None, exclude: str | None = None) -> list[str]:
    snaps = json.loads((ROOT / "output" / "catalog_dbt.json").read_text())["snapshots"]
    out = []
    for k, v in snaps.items():
        ws = v.get("workstream")
        if workstream and ws != workstream:
            continue
        if exclude and ws in (exclude, None, ""):
            continue
        out.append(k)
    return out


def _ctx(workstreams: list[str], organization_id: str | None):
    from api.auth.dependencies import AuthContext

    fields = {f.name: f for f in dataclasses.fields(AuthContext)}
    kw = {}
    for name, f in fields.items():
        if f.default is not dataclasses.MISSING:
            kw[name] = f.default
        elif f.default_factory is not dataclasses.MISSING:  # type: ignore[misc]
            kw[name] = f.default_factory()  # type: ignore[misc]
        else:
            kw[name] = None
    kw.update(workstreams=workstreams, organization_id=organization_id, disabled=False)
    return AuthContext(**kw)


class SnapshotAccessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev"})
        cls._env.start()

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def test_a_finance_grant_reaches_finance(self):
        from api.auth.workstream_access import can_access_snapshot
        ctx = _ctx(["finance"], "dev")
        for sid in _ids("finance")[:3]:
            self.assertTrue(can_access_snapshot(ctx, sid), sid)

    def test_a_finance_grant_is_refused_another_workstream(self):
        from api.auth.workstream_access import can_access_snapshot
        ctx = _ctx(["finance"], "dev")
        for sid in _ids(exclude="finance")[:3]:
            self.assertFalse(can_access_snapshot(ctx, sid), sid)

    def test_the_same_decision_holds_for_an_oracle_org(self):
        """Every client org now reads the one catalog; the answer cannot differ by org."""
        from api.auth.workstream_access import can_access_snapshot
        for org in ("ellensburg", "newark"):
            ctx = _ctx(["finance"], org)
            for sid in _ids("finance")[:2]:
                self.assertTrue(can_access_snapshot(ctx, sid), f"{org} {sid}")

    def test_an_unknown_snapshot_is_denied_for_a_restricted_grant(self):
        from api.auth.workstream_access import can_access_snapshot
        self.assertFalse(can_access_snapshot(_ctx(["finance"], "dev"), "NO_SUCH_SNAPSHOT"))

    def test_full_and_empty_grants_are_unaffected(self):
        from api.auth.workstream_access import can_access_snapshot
        for grant in (["*"], []):
            ctx = _ctx(grant, "dev")
            for sid in _ids()[:2]:
                self.assertTrue(can_access_snapshot(ctx, sid), f"{grant} {sid}")


if __name__ == "__main__":
    unittest.main()
