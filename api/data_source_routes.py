"""Portal data-source settings — test, save, and clear Oracle connections."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field

from api.auth.dependencies import AuthContext, get_auth_context
from api.data_source_store import (
    DataSourceConfig,
    clear_config,
    public_status,
    save_config,
    settings_token_required,
    validate_dsn,
    validate_user,
    verify_settings_token,
)
from api.demo_db import env_configured, test_oracle_connection
from api.organizations import is_valid_org_id


router = APIRouter(prefix="/portal/data-source", tags=["portal-data-source"])


class DataSourceBody(BaseModel):
    user: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=256)
    dsn: str = Field(min_length=1, max_length=512)
    oracle_client_lib_dir: str = Field(default="", max_length=512)
    thick_mode: bool = False


def _require_settings_token(x_portal_settings_token: str | None = Header(None)) -> None:
    if not verify_settings_token(x_portal_settings_token):
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid X-Portal-Settings-Token header.",
        )


def _require_data_source_manage(
    ctx: AuthContext = Depends(get_auth_context),
    x_portal_settings_token: str | None = Header(None),
) -> AuthContext:
    if ctx.has_permission("data_source:manage"):
        return ctx
    if verify_settings_token(x_portal_settings_token):
        return ctx
    raise HTTPException(status_code=403, detail="Admin access required for data source settings")


def _target_organization_id(
    ctx: AuthContext,
    organization_id: str | None = Query(None),
) -> str:
    if organization_id:
        if not is_valid_org_id(organization_id):
            raise HTTPException(status_code=400, detail="Invalid organization_id")
        if ctx.organization_id and ctx.organization_id != organization_id:
            raise HTTPException(status_code=403, detail="Cannot manage another organization's connection")
        if not ctx.organization_id and ctx.role != "admin":
            raise HTTPException(status_code=403, detail="Cannot manage another organization's connection")
        return organization_id
    return ctx.require_organization()


def _to_config(body: DataSourceBody) -> DataSourceConfig:
    try:
        validate_user(body.user)
        validate_dsn(body.dsn)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return DataSourceConfig(
        user=body.user.strip(),
        password=body.password,
        dsn=body.dsn.strip(),
        oracle_client_lib_dir=body.oracle_client_lib_dir.strip(),
        thick_mode=body.thick_mode,
    )


@router.get("")
def get_data_source_status(
    ctx: AuthContext = Depends(get_auth_context),
    organization_id: str | None = Query(None),
) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = ctx.effective_organization_id()
    if ctx.has_permission("data_source:manage"):
        try:
            org_id = _target_organization_id(ctx, organization_id)
        except HTTPException:
            if not org_id:
                raise
    if not org_id:
        return {"configured": False, "settings_token_required": settings_token_required()}
    configured = env_configured(org_id)
    if not ctx.has_permission("data_source:manage"):
        return {
            "configured": configured,
            "organization_id": org_id,
            "settings_token_required": settings_token_required(),
        }
    status = public_status(organization_id=org_id, env_configured=configured)
    status["settings_token_required"] = settings_token_required()
    return status


@router.post("/test")
def test_data_source(
    body: DataSourceBody,
    ctx: AuthContext = Depends(_require_data_source_manage),
    organization_id: str | None = Query(None),
) -> dict[str, Any]:
    org_id = _target_organization_id(ctx, organization_id)
    config = _to_config(body)
    try:
        result = test_oracle_connection(config)
        return {"ok": True, "organization_id": org_id, **result}
    except Exception as exc:
        return {"ok": False, "organization_id": org_id, "error": str(exc)}


@router.put("")
def save_data_source(
    body: DataSourceBody,
    ctx: AuthContext = Depends(_require_data_source_manage),
    organization_id: str | None = Query(None),
) -> dict[str, Any]:
    org_id = _target_organization_id(ctx, organization_id)
    config = _to_config(body)
    try:
        test_oracle_connection(config)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Connection test failed: {exc}") from exc
    meta = save_config(config, organization_id=org_id)
    status = public_status(organization_id=org_id, env_configured=env_configured(org_id))
    return {"saved": True, "storage": meta, "status": status}


@router.delete("")
def remove_data_source(
    ctx: AuthContext = Depends(_require_data_source_manage),
    organization_id: str | None = Query(None),
) -> dict[str, Any]:
    org_id = _target_organization_id(ctx, organization_id)
    clear_config(organization_id=org_id)
    status = public_status(organization_id=org_id, env_configured=env_configured(org_id))
    return {"cleared": True, "status": status}
