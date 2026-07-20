"""Helpers for org-scoped Oracle access in API routes."""

from __future__ import annotations

from fastapi import HTTPException

from api.auth.dependencies import AuthContext
from api.demo_db import demo_configured
from api.organizations import organization_display_name


def require_org_for_data(ctx: AuthContext) -> str:
    org_id = ctx.require_organization()
    if not demo_configured(org_id):
        label = ctx.organization_name or organization_display_name(org_id) or org_id
        raise HTTPException(
            status_code=503,
            detail=f"Database not configured for {label}. Set {label} connection in Settings or .env.",
        )
    return org_id
