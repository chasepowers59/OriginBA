"""Portal auth configuration — separate from Oracle analytics DB."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# Dedicated identity store (PostgreSQL in production; SQLite for local dev).
DEFAULT_SQLITE_URL = f"sqlite:///{ROOT / 'data' / 'analytics_portal' / 'portal_auth.db'}"


def auth_disabled() -> bool:
    return os.getenv("PORTAL_AUTH_DISABLED", "").strip().lower() in {"1", "true", "yes"}


def database_url() -> str:
    return os.getenv("PORTAL_AUTH_DATABASE_URL", DEFAULT_SQLITE_URL).strip()


def jwt_secret() -> str:
    secret = os.getenv("PORTAL_AUTH_SECRET", "").strip()
    if auth_disabled():
        return secret or "portal-auth-dev-disabled"
    if not secret or len(secret) < 32:
        raise RuntimeError(
            "PORTAL_AUTH_SECRET must be set (min 32 chars) when portal auth is enabled. "
            "Set PORTAL_AUTH_DISABLED=true for local open access."
        )
    return secret


# Pinned, not merely defaulted. decode() is called with algorithms=[jwt_algorithm()],
# so an env value of "none" would have made it accept UNSIGNED tokens. Anything outside
# this set falls back to HS256 rather than being trusted because it was configured.
_ALLOWED_JWT_ALGORITHMS = frozenset({"HS256", "HS384", "HS512"})


def jwt_algorithm() -> str:
    requested = os.getenv("PORTAL_AUTH_ALGORITHM", "HS256").strip()
    return requested if requested in _ALLOWED_JWT_ALGORITHMS else "HS256"


# Eight hours, and a floor of one minute. A bare int() here raised on any typo INSIDE
# create_access_token, so a malformed variable 500s every login rather than one; and a
# 0 or negative lifetime mints tokens that are already expired, which presents to every
# user at once as "the password is wrong".
DEFAULT_ACCESS_MINUTES = 480


def access_token_minutes() -> int:
    try:
        minutes = int(str(os.getenv("PORTAL_AUTH_ACCESS_MINUTES", "")).strip())
    except (TypeError, ValueError):
        return DEFAULT_ACCESS_MINUTES
    return max(1, minutes)


class BootstrapError(RuntimeError):
    """Refusing to create the first admin with a credential anyone can read."""


def bootstrap_admin_email() -> str:
    return os.getenv("PORTAL_BOOTSTRAP_ADMIN_EMAIL", "admin@origin.local").strip().lower()


def bootstrap_admin_password() -> str:
    """The first admin's password. There is deliberately NO default.

    A literal here is a published credential: the email defaults to a known value too,
    so any deployment that skipped this variable had an admin login readable in this
    repository. must_change_password does not save it — the intruder authenticates,
    changes the password, and locks the operator out. PORTAL_AUTH_SECRET already
    establishes the pattern of refusing to start rather than defaulting a secret.
    """
    password = os.getenv("PORTAL_BOOTSTRAP_ADMIN_PASSWORD", "")
    if len(password.strip()) < 12:
        raise BootstrapError(
            "PORTAL_BOOTSTRAP_ADMIN_PASSWORD must be set (min 12 chars) to create the "
            "first admin account. There is no default: one would be a published "
            "credential. Set PORTAL_AUTH_DISABLED=true for local open access."
        )
    return password
