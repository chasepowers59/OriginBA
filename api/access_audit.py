"""Access audit: who ran which report / SQL, recorded beside the admin audit log.

Report runs and SQL-workspace executions (including FENCE REFUSALS — the security
signal) land in the same portal_audit_log table the admin actions use, so one
admin endpoint answers "who touched what". Recording must never fail the query it
logs: every write is wrapped, and a broken audit DB degrades to silence, not 500s.
"""
from __future__ import annotations

import re

from api.auth.database import get_session_factory
from api.auth.service import log_audit

_STRING = re.compile(r"'(?:[^']|'')*'")
_LONG_NUMBER = re.compile(r"\b\d{5,}(?:\.\d+)?\b")


def sql_for_audit(sql: str, limit: int = 300) -> str:
    """The statement's shape, never its values: a customer's name or account number typed into
    a WHERE clause does not belong in the audit trail. String literals and numbers of five or
    more digits become ?; small numbers (a LIMIT, a flag) stay."""
    shape = _LONG_NUMBER.sub("?", _STRING.sub("?", sql or ""))
    return " ".join(shape.split())[:limit]


def record_access_event(*, actor_email: str, action: str, target_type: str,
                        target_id: str, detail: str, actor_id: str | None = None,
                        organization_id: str | None = None) -> None:
    """Best-effort audit write; swallows every failure by design. `organization_id` is the
    client the event touched; left out, it is the actor's own (log_audit)."""
    try:
        factory = get_session_factory()
        with factory() as session:
            log_audit(session, actor_id=actor_id, actor_email=actor_email,
                      action=action, target_type=target_type,
                      target_id=target_id, detail=detail[:2000], organization_id=organization_id)
            session.commit()
    except Exception:  # noqa: BLE001 — an audit failure must not fail the request
        pass
