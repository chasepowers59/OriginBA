"""The last of the untested backend helpers: audit writes, NLQ matching, org defaults.

`log_audit` (10 uses), `run_snapshot_analytics_nlq` (6), `dev_organization_id` (5),
`assert_snapshot_access` (5), `assert_workstream_access` (4), `match_metric` (3),
`get_session_auth_context` (3) and `bootstrap_admin_email` (3) were named in no test.

AUDIT M4 IS NOT FIXED HERE, deliberately. `AuditLog` carries a process-wide
`client_id` and no tenant dimension, so an admin's action in one org is
indistinguishable from another. The blocker is not the column, it is that
`api/auth/bootstrap.py` builds the schema with `Base.metadata.create_all()` and the
project has no migration mechanism at all: `create_all` creates MISSING tables and
never alters existing ones, so a new column works on a fresh database and silently
breaks every audit write on the deployed one. That needs a migration story before it
needs a column, so it stays open with the reason recorded rather than half-done.
"""

from __future__ import annotations

import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.auth.bootstrap import init_auth_database  # noqa: E402
from api.auth.database import get_session_factory  # noqa: E402


class LogAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._env = mock.patch.dict(os.environ, {
            "PORTAL_AUTH_DISABLED": "true", "PORTAL_DEV_ORGANIZATION": "dev"})
        cls._env.start()
        init_auth_database()

    @classmethod
    def tearDownClass(cls):
        cls._env.stop()

    def _rows(self, action):
        from api.auth.models import AuditLog
        with get_session_factory()() as session:
            return [
                {"actor_email": r.actor_email, "action": r.action,
                 "target_type": r.target_type, "target_id": r.target_id, "detail": r.detail}
                for r in session.query(AuditLog).filter(AuditLog.action == action).all()
            ]

    def test_writes_the_row_it_was_given(self):
        from api.auth.service import log_audit
        # A unique action per run: the auth database persists between test runs, so an
        # assertion on the row COUNT for a fixed action passes once and then never again.
        action = f"test_write_{uuid.uuid4().hex[:8]}"
        with get_session_factory()() as session:
            log_audit(session, actor_id="u1", actor_email="Someone@Origin.Local",
                      action=action, target_type="snapshot", target_id="rpt_bill",
                      detail="did a thing")
            session.commit()
        rows = self._rows(action)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_id"], "rpt_bill")
        self.assertEqual(rows[0]["detail"], "did a thing")

    def test_normalizes_the_actor_email(self):
        """Audit rows are searched by address; mixed case would split one actor in two."""
        from api.auth.service import log_audit
        action = f"test_case_{uuid.uuid4().hex[:8]}"
        with get_session_factory()() as session:
            log_audit(session, actor_id="u1", actor_email="  MiXeD@Origin.Local  ",
                      action=action)
            session.commit()
        self.assertEqual(self._rows(action)[0]["actor_email"], "mixed@origin.local")

    def test_an_actorless_event_is_attributed_to_system_not_blank(self):
        """Scheduled runs and the bootstrap have no user; a blank actor is unreadable."""
        from api.auth.service import log_audit
        action = f"test_system_{uuid.uuid4().hex[:8]}"
        with get_session_factory()() as session:
            log_audit(session, actor_id=None, actor_email="", action=action)
            session.commit()
        self.assertEqual(self._rows(action)[0]["actor_email"], "system")


class WorkstreamAssertTests(unittest.TestCase):
    """The thin wrappers that turn a False into a 403."""

    @staticmethod
    def _ctx(workstreams):
        import dataclasses
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
        kw.update(workstreams=workstreams, organization_id="dev", disabled=False)
        return AuthContext(**kw)

    def test_a_granted_workstream_passes_silently(self):
        from api.auth.workstream_access import assert_workstream_access
        self.assertIsNone(assert_workstream_access(self._ctx(["finance"]), "finance"))
        self.assertIsNone(assert_workstream_access(self._ctx(["*"]), "anything"))

    def test_an_ungranted_workstream_raises_403_not_404(self):
        """403 is deliberate: a 404 would deny the workstream EXISTS, and the nav
        already names it."""
        from fastapi import HTTPException
        from api.auth.workstream_access import assert_workstream_access
        with self.assertRaises(HTTPException) as caught:
            assert_workstream_access(self._ctx(["finance"]), "assets")
        self.assertEqual(caught.exception.status_code, 403)

    def test_snapshot_access_raises_the_same_way(self):
        from fastapi import HTTPException
        from api.auth.workstream_access import assert_snapshot_access
        with mock.patch.dict(os.environ, {"PORTAL_DEV_ORGANIZATION": "dev"}):
            with self.assertRaises(HTTPException) as caught:
                assert_snapshot_access(self._ctx(["finance"]), "NO_SUCH_SNAPSHOT")
        self.assertEqual(caught.exception.status_code, 403)


class MatchMetricTests(unittest.TestCase):
    def test_an_explicit_id_wins_over_the_text(self):
        from api.nlq_metrics import METRICS, match_metric
        target = METRICS[0]
        self.assertIs(match_metric("something else entirely", target.id), target)

    def test_no_question_matches_nothing(self):
        from api.nlq_metrics import match_metric
        for empty in ("", "   ", None):
            self.assertIsNone(match_metric(empty))

    def test_an_unrecognised_question_matches_nothing(self):
        from api.nlq_metrics import match_metric
        self.assertIsNone(match_metric("zzzz qqqq not a utility question at all"))

    def test_an_unknown_id_falls_back_to_the_text_rather_than_erroring(self):
        """A stale bookmark carrying a retired metric id still answers the question."""
        from api.nlq_metrics import match_metric
        self.assertIsNone(match_metric("zzzz qqqq", "no_such_metric_id"))


class SnapshotAnalyticsNlqTests(unittest.TestCase):
    """The guards in front of the metric runner, which are the interesting part."""

    def test_no_database_configured_means_no_answer(self):
        from api.snapshot_analytics_nlq import run_snapshot_analytics_nlq
        with mock.patch("api.snapshot_analytics_nlq.demo_configured", return_value=False), \
             mock.patch("api.snapshot_analytics_nlq.warehouse_configured", return_value=False):
            self.assertIsNone(run_snapshot_analytics_nlq("anything", organization_id="dev"))

    def test_an_empty_question_with_no_id_is_not_guessed_at(self):
        from api.snapshot_analytics_nlq import run_snapshot_analytics_nlq
        with mock.patch("api.snapshot_analytics_nlq.demo_configured", return_value=True):
            for empty in ("", "   "):
                self.assertIsNone(run_snapshot_analytics_nlq(empty, organization_id="dev"))

    def test_a_metric_this_org_cannot_resolve_is_refused_before_running(self):
        """A dbt-catalog org has no legacy *_RPT_CURR snapshots; offering the metric
        anyway just errors on click."""
        from api.nlq_metrics import METRICS
        from api.snapshot_analytics_nlq import run_snapshot_analytics_nlq
        target = METRICS[0]
        with mock.patch("api.snapshot_analytics_nlq.demo_configured", return_value=True), \
             mock.patch("api.snapshot_analytics_nlq._org_snapshot_ids", return_value=set()), \
             mock.patch("api.snapshot_analytics_nlq.run_metric_nlq") as runner:
            self.assertIsNone(run_snapshot_analytics_nlq("q", metric_id=target.id,
                                                         organization_id="dev"))
            runner.assert_not_called()

    def test_an_unbuilt_warehouse_answers_in_a_sentence_not_a_driver_error(self):
        """Every org reads the dbt catalog; on one whose warehouse is not built yet the
        answer card would otherwise print ORA-00942 into the conversation."""
        from api.nlq_metrics import METRICS
        from api.snapshot_analytics_nlq import run_snapshot_analytics_nlq
        target = METRICS[0]
        with mock.patch("api.snapshot_analytics_nlq.demo_configured", return_value=True), \
             mock.patch("api.snapshot_analytics_nlq._org_snapshot_ids",
                        return_value={target.snapshot_id}), \
             mock.patch("api.snapshot_analytics_nlq.run_metric_nlq",
                        side_effect=RuntimeError("ORA-00942: table or view does not exist")):
            out = run_snapshot_analytics_nlq("q", metric_id=target.id, organization_id="newark")
        self.assertIn("not been built", out["narrative"].lower())
        self.assertNotIn("ORA-", out["narrative"])

    def test_a_failure_answers_with_the_reason_rather_than_raising(self):
        """This runs behind /nlq; an exception here would 500 the whole answer."""
        from api.nlq_metrics import METRICS
        from api.snapshot_analytics_nlq import run_snapshot_analytics_nlq
        target = METRICS[0]
        with mock.patch("api.snapshot_analytics_nlq.demo_configured", return_value=True), \
             mock.patch("api.snapshot_analytics_nlq._org_snapshot_ids",
                        return_value={target.snapshot_id}), \
             mock.patch("api.snapshot_analytics_nlq.run_metric_nlq",
                        side_effect=RuntimeError("database is down")):
            out = run_snapshot_analytics_nlq("q", metric_id=target.id, organization_id="dev")
        self.assertIsNotNone(out)
        self.assertIn("database is down", out["narrative"])
        self.assertEqual(out["source"], "snapshot_analytics")


class OrganizationDefaultTests(unittest.TestCase):
    def test_a_valid_configured_dev_org_is_used(self):
        from api.organizations import dev_organization_id
        with mock.patch.dict(os.environ, {"PORTAL_DEV_ORGANIZATION": "dev"}):
            self.assertEqual(dev_organization_id(), "dev")

    def test_an_invalid_id_falls_back_to_the_first_org_rather_than_returning_it(self):
        """An unvalidated id would flow on as a catalog/connection key."""
        from api.organizations import dev_organization_id, load_organizations
        with mock.patch.dict(os.environ, {"PORTAL_DEV_ORGANIZATION": "../../etc/passwd"}):
            result = dev_organization_id()
        self.assertNotEqual(result, "../../etc/passwd")
        self.assertIn(result, [str(o["id"]) for o in load_organizations()])


class BootstrapEmailTests(unittest.TestCase):
    def test_defaults_and_normalizes(self):
        from api.auth.config import bootstrap_admin_email
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PORTAL_BOOTSTRAP_ADMIN_EMAIL", None)
            self.assertEqual(bootstrap_admin_email(), "admin@origin.local")
        with mock.patch.dict(os.environ,
                             {"PORTAL_BOOTSTRAP_ADMIN_EMAIL": "  Ops@City.GOV "}):
            self.assertEqual(bootstrap_admin_email(), "ops@city.gov")


class SessionAuthContextTests(unittest.TestCase):
    def test_it_differs_from_the_normal_one_only_on_pending_password_change(self):
        """It exists so a user forced to change their password can call that one route.

        Pinned because the difference is a single keyword argument, and widening it to
        the normal dependency would let a pending user roam the whole API.
        """
        import inspect
        from api.auth import dependencies as dep
        src = inspect.getsource(dep.get_session_auth_context)
        self.assertIn("allow_password_change_pending=True", src)
        normal = inspect.getsource(dep.get_auth_context)
        self.assertNotIn("allow_password_change_pending=True", normal)


if __name__ == "__main__":
    unittest.main()
