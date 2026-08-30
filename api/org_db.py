"""Helpers for org-scoped Oracle access in API routes."""

from __future__ import annotations

from fastapi import HTTPException

from api.auth.dependencies import AuthContext
from api.demo_db import demo_configured
from api.organizations import organization_display_name
from api.warehouse_db import warehouse_configured


def require_org_for_data(ctx: AuthContext) -> str:
    org_id = ctx.require_organization()
    # A Postgres/dbt org is served by warehouse_db, an Oracle org by demo_db --
    # EITHER backend being configured means the org has a data source. Gating only
    # on demo_configured (Oracle) 503'd every Postgres org in a deployment with no
    # Oracle/DEMO_* creds (e.g. Render serving the dbt warehouse); locally it slipped
    # through only via the DEMO_* global fallback.
    if not (demo_configured(org_id) or warehouse_configured(org_id)):
        label = ctx.organization_name or organization_display_name(org_id) or org_id
        raise HTTPException(
            status_code=503,
            detail=f"Database not configured for {label}. Set {label} connection in Settings or .env.",
        )
    return org_id
