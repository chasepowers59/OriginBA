"""FastAPI auth dependencies."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Annotated, Callable

import jwt
from fastapi import Depends, Header, HTTPException

from api.auth.config import auth_disabled
from api.auth.database import get_session_factory
from api.auth.permissions import role_at_least
from api.auth.security import decode_access_token
from api.auth.service import get_user, user_to_public, workstreams_allowed
from api.organizations import dev_organization_id, organization_display_name


@dataclass(frozen=True)
class AuthContext:
    id: str
    email: str
    display_name: str
    role: str
    client_id: str
    organization_id: str | None
    organization_name: str | None
    permissions: set[str]
    workstreams: list[str]
    disabled: bool = False
    must_change_password: bool = False
    # Set ONLY for an admin who has switched tenant in the header control. It is the
    # tenant they are currently looking at, never the tenant they belong to.
    active_organization_id: str | None = None

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions

    def require_permission(self, permission: str) -> None:
        if not self.has_permission(permission):
            raise HTTPException(status_code=403, detail=f"Permission required: {permission}")

    def can_access_workstream(self, workstream_id: str) -> bool:
        return workstreams_allowed(self.workstreams, workstream_id)

    def effective_organization_id(self) -> str | None:
        # An admin's in-session tenant choice wins. It is validated against the registry
        # and against the admin role before it ever reaches this field, so by the time it
        # is set it is already known to be legitimate.
        if self.active_organization_id:
            return self.active_organization_id
        if self.organization_id:
            return self.organization_id
        if self.disabled:
            return dev_organization_id()
        return None

    def require_organization(self) -> str:
        org_id = self.effective_organization_id()
        if not org_id:
            raise HTTPException(
                status_code=403,
                detail="No organization assigned. Contact an administrator to assign your client environment.",
            )
        return org_id


def _dev_context() -> AuthContext:
    dev_org = dev_organization_id()
    return AuthContext(
        id="dev-user",
        email="dev@origin.local",
        display_name="Development User",
        role="admin",
        client_id="demo",
        organization_id=dev_org,
        organization_name=organization_display_name(dev_org),
        permissions={
            "portal:read",
            "report_library:read",
            "snapshots:read",
            "snapshots:query",
            "database:sql",
            "nlq:read",
            "saved_views:write",
            "dashboards:write",
            "explorer:builder",
            "users:manage",
            "groups:manage",
            "data_source:manage",
            "snapshots:raw_sql",
            "settings:manage",
        },
        workstreams=["*"],
        disabled=True,
        must_change_password=False,
    )


def _resolve_active_organization(role: str, requested: str | None) -> str | None:
    """The tenant an admin has switched to, or None.

    THREE THINGS HAVE TO BE TRUE and all three are checked here rather than at the call
    sites, because a tenant override that leaks is a data-separation failure, not a bug:

      the caller is an ADMIN -- for anyone else the header is IGNORED, not rejected.
      Ignoring is the fail-safe: a non-admin who sends it gets their own tenant's data,
      which is the correct answer to their request, instead of an error that confirms
      the header does something.

      the value NAMES A REGISTERED ORGANIZATION. Anything else is discarded, so the
      header can never reach a connection string or a catalog path.

      the value is used only to CHOOSE among configured tenants. It is never a
      connection detail itself.
    """
    if not requested or role != "admin":
        return None
    from api.organizations import is_valid_org_id
    return requested if is_valid_org_id(requested) else None


def _resolve_auth_context(
    authorization: str | None,
    *,
    allow_password_change_pending: bool,
    active_organization: str | None = None,
) -> AuthContext:
    if auth_disabled():
        # AuthContext is frozen on purpose -- a request's identity must not be editable
        # once resolved -- so the dev context is REPLACED rather than mutated.
        ctx = _dev_context()
        return replace(
            ctx,
            active_organization_id=_resolve_active_organization(ctx.role, active_organization),
        )

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Authentication required")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired token") from exc

    factory = get_session_factory()
    with factory() as session:
        user = get_user(session, str(payload.get("sub")))
        if not user or not user.is_active:
            raise HTTPException(status_code=401, detail="User inactive or not found")
        public = user_to_public(user)

    if public["must_change_password"] and not allow_password_change_pending:
        raise HTTPException(status_code=403, detail="password_change_required")

    return AuthContext(
        id=public["id"],
        email=public["email"],
        display_name=public["display_name"],
        role=public["role"],
        client_id=public["client_id"],
        organization_id=public.get("organization_id"),
        organization_name=public.get("organization_name"),
        permissions=set(public["permissions"]),
        workstreams=public["workstreams"],
        must_change_password=public["must_change_password"],
        active_organization_id=_resolve_active_organization(
            public["role"], active_organization),
    )


def get_auth_context(
    authorization: str | None = Header(None),
    x_organization_id: str | None = Header(None),
) -> AuthContext:
    return _resolve_auth_context(
        authorization,
        allow_password_change_pending=False,
        active_organization=x_organization_id,
    )


def get_session_auth_context(authorization: str | None = Header(None)) -> AuthContext:
    """Auth context that allows access while a password change is still pending."""
    return _resolve_auth_context(authorization, allow_password_change_pending=True)


def optional_auth_context(
    authorization: str | None = Header(None),
) -> AuthContext | None:
    if auth_disabled():
        return _dev_context()
    if not authorization:
        return None
    return get_auth_context(authorization)


def require_permission(permission: str) -> Callable:
    def _dep(ctx: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        ctx.require_permission(permission)
        return ctx

    return _dep


def require_role(minimum: str) -> Callable:
    def _dep(ctx: Annotated[AuthContext, Depends(get_auth_context)]) -> AuthContext:
        if not role_at_least(ctx.role, minimum):
            raise HTTPException(status_code=403, detail=f"Role {minimum} or higher required")
        return ctx

    return _dep
