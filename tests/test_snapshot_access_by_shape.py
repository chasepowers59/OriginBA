"""A workstream grant must mean the same thing on both deployment shapes.

`snapshot_workstream()` called `get_snapshot()` with NO organization_id, and
`catalog_name_for_org(None)` returns "dbt" — so every authorization lookup resolved
against the dbt catalog no matter which org the caller belonged to. The two shapes
share no snapshot ids (`rpt_financial_txn` against `FT_RPT_CURR`), so on the six legacy
orgs the lookup missed, raised CatalogError, and returned "".

`workstreams_allowed(["finance"], "")` is False, so the guard DENIED. Measured before
the fix, for a user granted exactly ["finance"]:

    dbt    rpt_financial_txn  (finance)  -> True
    dbt    rpt_gl             (finance)  -> True
    legacy FT_RPT_CURR        (finance)  -> False    <-- their own workstream

FT_RPT_CURR declares `workstream: finance`. So a workstream-restricted user on any
legacy org was locked out of EVERY snapshot, their own grants included — and through
`filter_nlq_metrics_for_auth` and `filter_dashboard_for_auth`, their metrics and
dashboard tiles silently filtered to empty rather than erroring.

It fails CLOSED, so this is a lockout and not a leak. It stayed invisible because the
dev org is a dbt org and a user with "*" or an empty grant (both mean full access)
never reaches the comparison at all — the two configurations we develop against.

Neither of these functions was named in any test before this file.
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


def _catalog_ids(name: str, workstream: str | None = None) -> list[str]:
    snaps = json.loads((ROOT / "output" / f"{name}.json").read_text())["snapshots"]
    if workstream is None:
        return list(snaps)
    return [k for k, v in snaps.items() if v.get("workstream") == workstream]


def _legacy_org(org_id: str):
    """Make `org_id` a real legacy (cisadm-catalog) organization.

    Deliberately patches the registry rather than catalog_name_for_org, so that
    `catalog_name_for_org(None)` still answers "dbt" exactly as in production. That
    difference is the whole test: patching the selector hands the lookup the org it
    fails to ask for, and the assertion then passes against the broken code.
    """
    import api.snapshot_catalog as sc
    sc.load_catalog(force=True)  # drop any cache keyed on a previous patch
    return mock.patch("api.organizations.get_organization",
                      side_effect=lambda oid, *a, **k: {"catalog": "cisadm"} if oid == org_id else None)


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
            kw[name] = True if name == "disabled" else None
    kw["workstreams"] = workstreams
    kw["organization_id"] = organization_id
    kw["disabled"] = False
    return AuthContext(**kw)


class SnapshotAccessAcrossShapesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev"})
        cls._env.start()

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def test_a_finance_grant_reaches_finance_on_the_dbt_shape(self):
        from api.auth.workstream_access import can_access_snapshot
        ctx = _ctx(["finance"], "dev")
        for sid in _catalog_ids("catalog_dbt", "finance")[:3]:
            self.assertTrue(can_access_snapshot(ctx, sid), sid)

    def test_a_finance_grant_reaches_finance_on_the_LEGACY_shape(self):
        """The bug: FT_RPT_CURR declares workstream 'finance' and was denied."""
        from api.auth.workstream_access import can_access_snapshot
        legacy_finance = _catalog_ids("catalog_cisadm", "finance")
        self.assertTrue(legacy_finance, "fixture expects finance snapshots in the legacy catalog")
        # Patch the ORG REGISTRY, not catalog_name_for_org: mocking the selector makes
        # it answer "cisadm" for the organization_id=None call too, which silently
        # supplies the very argument whose absence IS the bug, and the test passes
        # against the broken code. The org must genuinely be legacy while the lookup
        # simply never asks.
        with _legacy_org("legacy_org"):
            ctx = _ctx(["finance"], "legacy_org")
            for sid in legacy_finance[:3]:
                self.assertTrue(can_access_snapshot(ctx, sid), sid)

    def test_a_grant_still_DENIES_another_workstream_on_the_legacy_shape(self):
        """Fixing the lookup must not turn the lockout into a leak."""
        from api.auth.workstream_access import can_access_snapshot
        snaps = json.loads((ROOT / "output" / "catalog_cisadm.json").read_text())["snapshots"]
        other = [k for k, v in snaps.items()
                 if v.get("workstream") not in ("finance", None, "")][:3]
        self.assertTrue(other, "fixture expects non-finance snapshots in the legacy catalog")
        with _legacy_org("legacy_org"):
            ctx = _ctx(["finance"], "legacy_org")
            for sid in other:
                self.assertFalse(can_access_snapshot(ctx, sid), sid)

    def test_an_unknown_snapshot_is_denied_for_a_restricted_grant(self):
        from api.auth.workstream_access import can_access_snapshot
        ctx = _ctx(["finance"], "dev")
        self.assertFalse(can_access_snapshot(ctx, "NO_SUCH_SNAPSHOT_ANYWHERE"))

    def test_full_and_empty_grants_are_unaffected(self):
        """Both mean full access, and neither reaches the workstream comparison —
        which is exactly why this shipped."""
        from api.auth.workstream_access import can_access_snapshot
        for grant in (["*"], []):
            ctx = _ctx(grant, "dev")
            for sid in _catalog_ids("catalog_dbt")[:2]:
                self.assertTrue(can_access_snapshot(ctx, sid), f"{grant} {sid}")


if __name__ == "__main__":
    unittest.main()
