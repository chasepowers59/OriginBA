"""Production security helpers."""

from __future__ import annotations

import os


def is_development() -> bool:
    """AFFIRMATIVE proof this is not a production deployment.

    Audit M3: `/health` disclosed the client roster unauthenticated because it asked
    `not is_production()`, and is_production() defaults to False. ENVIRONMENT is set in
    no deployment file and is absent from deploy/api.env.example; the API runs on
    Render, which sets neither RAILWAY_ENVIRONMENT_NAME nor VERCEL_ENV. So the verbose
    branch was the live one.

    The fix is the DIRECTION of the default rather than another platform name to
    recognise: anything unrecognised is treated as production and discloses nothing.
    A developer who wants the detailed /health sets ENVIRONMENT=development.
    """
    if is_production():
        return False
    return os.getenv("ENVIRONMENT", "").strip().lower() in {
        "development", "dev", "local", "test"}


def is_production() -> bool:
    explicit = os.getenv("ENVIRONMENT", "").strip().lower()
    if explicit in {"production", "prod"}:
        return True
    if explicit in {"development", "dev", "local", "test"}:
        return False
    if os.getenv("RAILWAY_ENVIRONMENT_NAME", "").strip().lower() == "production":
        return True
    if os.getenv("VERCEL_ENV", "").strip().lower() == "production":
        return True
    return False
