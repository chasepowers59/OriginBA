"""What a person may be told when the database or a mail server fails.

Driver and network errors name hosts, IP addresses, connection strings and service names
(production-readiness audit, 2026-10-05). `public_error` turns one into a sentence that is
safe to show: a connection failure becomes the unreachable note with the request's
reference; anything else keeps the first line of its message (a person writing SQL needs
"column X does not exist") with hosts, addresses and connection strings removed. The full
text stays in the server log under the same reference. Pinned by tests/test_public_errors.py,
which also refuses any broad `except Exception` that returns raw exception text.
"""
from __future__ import annotations

import logging
import re
from contextvars import ContextVar

log = logging.getLogger("originba.api")

# set by api/request_tracing.py for every request; "-" outside one (the warmer, tests)
current_reference: ContextVar[str] = ContextVar("current_reference", default="-")

_REDACTIONS = (
    re.compile(r"\b[a-z][a-z0-9+.-]*://\S+", re.IGNORECASE),                      # URLs, DSNs with credentials
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?\b"),                           # IPv4 (+ port)
    re.compile(r"\b(?:[a-z0-9-]+\.){2,}[a-z]{2,}(?::\d+)?(?:/[\w.$-]+)?", re.IGNORECASE),  # host.domain.tld[:port][/service]
    re.compile(r"\b(?:host|hostaddr|server|user|password|dsn)\s*=\s*\S+", re.IGNORECASE),
)


def scrub(message: object) -> str:
    """The first line of a driver message with hosts, addresses and connection strings removed."""
    first = (str(message).strip().splitlines() or [""])[0]
    for pattern in _REDACTIONS:
        first = pattern.sub("[server]", first)
    return first[:300]


def public_error(prefix: str, exc: BaseException, *, reference: str | None = None) -> str:
    from api.executive_dashboard import DATABASE_UNREACHABLE_NOTE, is_not_connected_error

    ref = reference or current_reference.get()
    log.warning("ref=%s %s: %s: %s", ref, prefix, type(exc).__name__, str(exc)[:500])
    if is_not_connected_error(str(exc)) or re.search(r"cannot connect|connection (refused|reset|timed out)|could not connect|"
                                                     r"DPY-6005|ORA-12\d{3}|getaddrinfo|Name or service not known",
                                                     str(exc), re.IGNORECASE):
        return f"{DATABASE_UNREACHABLE_NOTE} Reference: {ref}"
    return f"{prefix}: {scrub(exc)} (reference {ref})"
