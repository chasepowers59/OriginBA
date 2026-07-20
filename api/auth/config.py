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


def jwt_algorithm() -> str:
    return os.getenv("PORTAL_AUTH_ALGORITHM", "HS256")


def access_token_minutes() -> int:
    return int(os.getenv("PORTAL_AUTH_ACCESS_MINUTES", "480"))


def bootstrap_admin_email() -> str:
    return os.getenv("PORTAL_BOOTSTRAP_ADMIN_EMAIL", "admin@origin.local").strip().lower()


def bootstrap_admin_password() -> str:
    return os.getenv("PORTAL_BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe-Admin-1!")
