"""Authentication and admin routes."""

from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from api.auth.config import access_token_minutes, auth_disabled
from api.auth import oidc
from api.auth.database import get_session_factory
from api.auth.dependencies import AuthContext, get_auth_context, get_session_auth_context, require_permission
from api.auth.rate_limit import check_login_rate_limit, clear_login_attempts, record_login_failure
from api.auth.schemas import (
    AccessGroupCreate,
    AccessGroupPublic,
    AccessGroupUpdate,
    AuthStatusResponse,
    AuthUserPublic,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    PortalOrganizationPublic,
    UserCreate,
    UserUpdate,
)
from api.auth.models import User
from api.auth.security import create_access_token, hash_password
from api.auth.service import (
    AuthError,
    authenticate_user,
    change_password,
    create_group,
    create_user,
    delete_group,
    list_audit_events,
    list_groups,
    list_users,
    log_audit,
    update_group,
    update_user,
    user_to_public,
)
from api.organizations import list_organizations_public, resolve_organization

router = APIRouter(prefix="/auth", tags=["auth"])


def _db_session():
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(authorization: str | None = Header(None)) -> AuthStatusResponse:
    sso = oidc.oidc_enabled()
    if auth_disabled():
        return AuthStatusResponse(enabled=False, authenticated=True, oidc_enabled=sso)
    if not authorization or not authorization.lower().startswith("bearer "):
        return AuthStatusResponse(enabled=True, authenticated=False, oidc_enabled=sso)
    try:
        get_auth_context(authorization)
        return AuthStatusResponse(enabled=True, authenticated=True, oidc_enabled=sso)
    except HTTPException:
        return AuthStatusResponse(enabled=True, authenticated=False, oidc_enabled=sso)


@router.post("/login", response_model=LoginResponse)
def login(
    body: LoginRequest,
    request: Request,
    session: Session = Depends(_db_session),
) -> LoginResponse:
    if auth_disabled():
        raise HTTPException(status_code=400, detail="Auth is disabled in this environment")
    client_ip = request.client.host if request.client else "unknown"
    rate_key = f"{body.email}|{client_ip}"
    check_login_rate_limit(rate_key)
    try:
        user = authenticate_user(session, body.email, body.password)
    except AuthError as exc:
        record_login_failure(rate_key)
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    clear_login_attempts(rate_key)
    public = user_to_public(user)

    # Multi-tenant binding. When the login names an organization (a /<slug> tenant URL
    # or a typed org at root), resolve and authorize it: a non-admin may only enter the
    # organization their account belongs to; an admin may enter any registered tenant.
    home_org = public.get("organization_id")
    active_org = home_org
    if body.organization:
        target = resolve_organization(body.organization)
        if not target:
            raise HTTPException(
                status_code=400, detail=f"Unknown organization '{body.organization}'."
            )
        target_id = str(target["id"])
        if public["role"] != "admin" and home_org != target_id:
            raise HTTPException(
                status_code=403,
                detail=f"This account is not part of {target['display_name']}.",
            )
        active_org = target_id

    token = create_access_token(
        user_id=public["id"],
        email=public["email"],
        role=public["role"],
        client_id=public["client_id"],
        organization_id=public.get("organization_id"),
        workstreams=public["workstreams"],
    )
    return LoginResponse(
        access_token=token,
        expires_in_minutes=access_token_minutes(),
        user=AuthUserPublic(**public),
        active_organization_id=active_org,
    )


@router.post("/change-password", response_model=AuthUserPublic)
def change_password_route(
    body: ChangePasswordRequest,
    ctx: AuthContext = Depends(get_session_auth_context),
    session: Session = Depends(_db_session),
) -> AuthUserPublic:
    try:
        public = change_password(session, ctx.id, body.current_password, body.new_password)
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="user.password_change",
            target_type="user",
            target_id=ctx.id,
            detail="Password updated",
        )
        return AuthUserPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/me", response_model=AuthUserPublic)
def me(ctx: AuthContext = Depends(get_session_auth_context), session: Session = Depends(_db_session)) -> AuthUserPublic:
    if ctx.disabled:
        return AuthUserPublic(
            id=ctx.id,
            email=ctx.email,
            display_name=ctx.display_name,
            role=ctx.role,
            client_id=ctx.client_id,
            organization_id=ctx.organization_id,
            organization_name=ctx.organization_name,
            is_active=True,
            must_change_password=False,
            workstreams=ctx.workstreams,
            permissions=sorted(ctx.permissions),
        )
    from api.auth.service import get_user

    user = get_user(session, ctx.id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return AuthUserPublic(**user_to_public(user))


@router.get("/organizations", response_model=list[PortalOrganizationPublic])
def list_organizations(
    _: AuthContext = Depends(require_permission("users:manage")),
) -> list[PortalOrganizationPublic]:
    return [PortalOrganizationPublic(**row) for row in list_organizations_public()]


@router.get("/tenants/{slug}", response_model=PortalOrganizationPublic)
def resolve_tenant(slug: str) -> PortalOrganizationPublic:
    """Public, unauthenticated single-tenant lookup for the login page.

    A /<slug> tenant URL uses this to show the tenant's real display name and to
    reject an unknown slug. It returns only {id, display_name} for one org — never the
    full tenant list — so the client roster is not enumerable from here.
    """
    org = resolve_organization(slug)
    if not org:
        raise HTTPException(status_code=404, detail="Unknown organization")
    return PortalOrganizationPublic(id=str(org["id"]), display_name=str(org["display_name"]))


@router.get("/oidc/login")
def oidc_login():
    """Kick off SSO: redirect to the IdP with our client id and a signed state."""
    cfg = oidc.oidc_config()
    if not cfg:
        raise HTTPException(status_code=404, detail="SSO is not configured")
    disc = oidc.fetch_discovery(cfg["OIDC_ISSUER"])
    params = urlencode({
        "client_id": cfg["OIDC_CLIENT_ID"],
        "response_type": "code",
        "scope": "openid email profile",
        "redirect_uri": cfg["OIDC_REDIRECT_URI"],
        "response_mode": "query",
        "state": oidc.make_state(),
    })
    return RedirectResponse(f"{disc['authorization_endpoint']}?{params}")


@router.get("/oidc/callback")
def oidc_callback(
    code: str = "",
    state: str = "",
    session: Session = Depends(_db_session),
):
    """IdP redirect target: verify state + id_token, JIT-provision, hand the SPA our JWT.

    The token travels in the URL FRAGMENT (#sso_token=...) — fragments never reach
    server logs — and the login page stores it exactly like a password login's token.
    Users are provisioned as role `user` in the configured default org; SSO never
    mints admins.
    """
    cfg = oidc.oidc_config()
    if not cfg:
        raise HTTPException(status_code=404, detail="SSO is not configured")
    if not code or not oidc.verify_state(state):
        raise HTTPException(status_code=400, detail="Invalid SSO state")

    disc = oidc.fetch_discovery(cfg["OIDC_ISSUER"])
    tokens = oidc.exchange_code(disc["token_endpoint"], code, cfg)
    claims = oidc.verify_id_token(
        tokens.get("id_token", ""), disc["jwks_uri"],
        cfg["OIDC_CLIENT_ID"], disc.get("issuer", cfg["OIDC_ISSUER"]))
    email = oidc.claims_email(claims)
    if not email:
        raise HTTPException(status_code=400, detail="Identity token carried no email address")

    user = session.query(User).filter(User.email == email).one_or_none()
    if user is None:
        user = User(
            email=email,
            display_name=str(claims.get("name") or email.split("@")[0]),
            # unusable password: SSO users authenticate at the IdP only
            password_hash=hash_password(secrets.token_urlsafe(24)),
            role="user",
            organization_id=cfg.get("OIDC_DEFAULT_ORGANIZATION") or None,
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        log_audit(session, actor_id=user.id, actor_email=email, action="sso_jit_provision",
                  target_type="user", target_id=user.id, detail="OIDC first login")
        session.commit()
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is deactivated")

    public = user_to_public(user)
    token = create_access_token(
        user_id=public["id"], email=public["email"], role=public["role"],
        client_id=public["client_id"], organization_id=public.get("organization_id"),
        workstreams=public["workstreams"])

    dest = cfg.get("OIDC_POST_LOGIN_URL") or "/login"
    return RedirectResponse(f"{dest}#sso_token={token}")


@router.get("/users", response_model=list[AuthUserPublic])
def admin_list_users(
    _: AuthContext = Depends(require_permission("users:manage")),
    session: Session = Depends(_db_session),
) -> list[AuthUserPublic]:
    return [AuthUserPublic(**row) for row in list_users(session)]


@router.post("/users", response_model=AuthUserPublic)
def admin_create_user(
    body: UserCreate,
    ctx: AuthContext = Depends(require_permission("users:manage")),
    session: Session = Depends(_db_session),
) -> AuthUserPublic:
    try:
        public = create_user(session, ctx.role, body.model_dump())
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="user.create",
            target_type="user",
            target_id=public["id"],
            detail=public["email"],
        )
        return AuthUserPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/users/{user_id}", response_model=AuthUserPublic)
def admin_update_user(
    user_id: str,
    body: UserUpdate,
    ctx: AuthContext = Depends(require_permission("users:manage")),
    session: Session = Depends(_db_session),
) -> AuthUserPublic:
    try:
        public = update_user(session, ctx.role, ctx.id, user_id, body.model_dump(exclude_unset=True))
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="user.update",
            target_type="user",
            target_id=user_id,
            detail=public["email"],
        )
        return AuthUserPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.get("/groups", response_model=list[AccessGroupPublic])
def admin_list_groups(
    _: AuthContext = Depends(require_permission("groups:manage")),
    session: Session = Depends(_db_session),
) -> list[AccessGroupPublic]:
    return [AccessGroupPublic(**row) for row in list_groups(session)]


@router.post("/groups", response_model=AccessGroupPublic)
def admin_create_group(
    body: AccessGroupCreate,
    ctx: AuthContext = Depends(require_permission("groups:manage")),
    session: Session = Depends(_db_session),
) -> AccessGroupPublic:
    try:
        public = create_group(session, body.model_dump())
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="group.create",
            target_type="group",
            target_id=public["id"],
            detail=public["name"],
        )
        return AccessGroupPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/groups/{group_id}", response_model=AccessGroupPublic)
def admin_update_group(
    group_id: str,
    body: AccessGroupUpdate,
    ctx: AuthContext = Depends(require_permission("groups:manage")),
    session: Session = Depends(_db_session),
) -> AccessGroupPublic:
    try:
        public = update_group(session, group_id, body.model_dump(exclude_unset=True))
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="group.update",
            target_type="group",
            target_id=group_id,
            detail=public["name"],
        )
        return AccessGroupPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.delete("/groups/{group_id}")
def admin_delete_group(
    group_id: str,
    ctx: AuthContext = Depends(require_permission("groups:manage")),
    session: Session = Depends(_db_session),
) -> dict[str, str]:
    if not delete_group(session, group_id):
        raise HTTPException(status_code=404, detail="Access group not found")
    log_audit(
        session,
        actor_id=ctx.id,
        actor_email=ctx.email,
        action="group.delete",
        target_type="group",
        target_id=group_id,
    )
    return {"deleted": group_id}


@router.get("/audit-log")
def admin_audit_log(
    limit: int = 100,
    action: str | None = None,
    _: AuthContext = Depends(require_permission("users:manage")),
    session: Session = Depends(_db_session),
) -> list[dict[str, Any]]:
    return list_audit_events(session, limit=limit, action=action)
