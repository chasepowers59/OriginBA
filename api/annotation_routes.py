"""Annotation routes: notes on saved views, dashboards, and tiles."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from api.auth.dependencies import AuthContext, get_auth_context
from api.org_db import require_org_for_data
from api import annotations as an

router = APIRouter(prefix="/annotations", tags=["annotations"])


class AnnotationCreateRequest(BaseModel):
    target_type: str
    target_id: str
    text: str


@router.get("")
def get_annotations(
    target_type: str,
    target_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = require_org_for_data(ctx)
    return {"annotations": an.list_annotations(
        org_id, target_type=target_type, target_id=target_id)}


@router.post("")
def create_annotation(
    body: AnnotationCreateRequest,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = require_org_for_data(ctx)
    try:
        return an.create_annotation(body.model_dump(), organization_id=org_id,
                                    author_email=ctx.email)
    except an.AnnotationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.delete("/{annotation_id}")
def delete_annotation(
    annotation_id: str,
    ctx: AuthContext = Depends(get_auth_context),
) -> dict[str, Any]:
    ctx.require_permission("portal:read")
    org_id = require_org_for_data(ctx)
    if not an.delete_annotation(annotation_id, organization_id=org_id,
                                requester_email=ctx.email,
                                is_admin=ctx.role == "admin"):
        raise HTTPException(status_code=404,
                            detail="Note not found, or it isn't yours to remove")
    return {"deleted": annotation_id}
