"""Access audit: who ran which report / SQL, recorded beside the admin audit log.

Report runs and SQL-workspace executions (including FENCE REFUSALS — the security
signal) land in the same portal_audit_log table the admin actions use, so one
admin endpoint answers "who touched what". Recording must never fail the query it
logs: every write is wrapped, and a broken audit DB degrades to silence, not 500s.
"""
from __future__ import annotations

from api.auth.database import get_session_factory
from api.auth.service import log_audit


def record_access_event(*, actor_email: str, action: str, target_type: str,
                        target_id: str, detail: str, actor_id: str | None = None) -> None:
    """Best-effort audit write; swallows every failure by design."""
    try:
        factory = get_session_factory()
        with factory() as session:
            log_audit(session, actor_id=actor_id, actor_email=actor_email,
                      action=action, target_type=target_type,
                      target_id=target_id, detail=detail[:2000])
            session.commit()
    except Exception:  # noqa: BLE001 — an audit failure must not fail the request
        pass
