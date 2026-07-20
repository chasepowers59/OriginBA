"""Production security helpers."""

from __future__ import annotations

import os


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
