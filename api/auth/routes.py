"""Authentication and admin routes."""

from __future__ import annotations

import secrets
from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import delete
from sqlalchemy.orm import Session

from api.auth.config import access_token_minutes, auth_disabled
from api.auth import oidc
from api.auth.database import get_session_factory
from api.auth.models import RevokedToken
from api.auth.password_policy import password_problem
from api.auth.dependencies import AuthContext, get_auth_context, get_session_auth_context, require_permission
from api.auth.rate_limit import check_login_rate_limit, clear_login_attempts, record_login_failure
from api.auth.schemas import (
    PasswordChangedResponse,
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
from api.auth.security import create_access_token, decode_access_token, hash_password, password_fingerprint
from api.auth.service import (
    sync_sso_access,
    AUDIT_CATEGORIES,
    AuthError,
    authenticate_user,
    change_password,
    create_group,
    create_user,
    delete_group,
    get_user,
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
    """One transaction per request. Declared scope="function" wherever it is used, so the
    commit lands BEFORE the response: by default FastAPI runs this exit code after the
    response is sent, and a caller could sign in with a new password before it was saved
    (tests/test_auth_commit_before_response.py)."""
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



def _require_strong(password: str | None, email: str) -> None:
    """A password being SET meets the policy (api/auth/password_policy.py); sign-in never checks it."""
    if password is not None and (problem := password_problem(password, email)):
        raise HTTPException(status_code=400, detail=problem)

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
    session: Session = Depends(_db_session, scope="function"),
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
        # committed here: the 401 below rolls the request's transaction back
        log_audit(session, actor_id=None, actor_email=body.email.strip()[:200], action="login_failed",
                  target_type="user", detail=f"ip={client_ip}", organization_id=None)
        session.commit()
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    clear_login_attempts(rate_key)
    log_audit(session, actor_id=user.id, actor_email=user.email, action="login",
              target_type="user", target_id=user.id, detail=f"ip={client_ip}")
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
        pwv=password_fingerprint(user.password_hash),
    )
    return LoginResponse(
        access_token=token,
        expires_in_minutes=access_token_minutes(),
        user=AuthUserPublic(**public),
        active_organization_id=active_org,
    )


@router.post("/change-password", response_model=PasswordChangedResponse)
def change_password_route(
    body: ChangePasswordRequest,
    request: Request,
    ctx: AuthContext = Depends(get_session_auth_context),
    session: Session = Depends(_db_session, scope="function"),
) -> PasswordChangedResponse:
    # the current password is a credential check like sign-in, and limited the same way
    rate_key = f"change-password|{ctx.id}|{request.client.host if request.client else 'unknown'}"
    check_login_rate_limit(rate_key)
    _require_strong(body.new_password, ctx.email)
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
        clear_login_attempts(rate_key)
        # the change retires every token issued before it (api/auth/security.py password_fingerprint),
        # this one included: the caller continues on a fresh one
        user = get_user(session, ctx.id)
        token = create_access_token(
            user_id=public["id"], email=public["email"], role=public["role"],
            client_id=public["client_id"], organization_id=public.get("organization_id"),
            workstreams=public["workstreams"], pwv=password_fingerprint(user.password_hash))
        return PasswordChangedResponse(**public, access_token=token)
    except AuthError as exc:
        record_login_failure(rate_key)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/logout")
def logout(
    authorization: str = Header(...),
    ctx: AuthContext = Depends(get_session_auth_context),
    session: Session = Depends(_db_session, scope="function"),
) -> dict[str, bool]:
    """End THIS session on the server: its token id is recorded and never opens a session
    again. Clearing the browser alone left a copied token working until it expired."""
    payload = decode_access_token(authorization.split(" ", 1)[1].strip())
    now = datetime.now(timezone.utc)
    session.execute(delete(RevokedToken).where(RevokedToken.expires_at < now))
    if payload.get("jti"):
        session.merge(RevokedToken(jti=payload["jti"], user_id=ctx.id,
                                   expires_at=datetime.fromtimestamp(int(payload["exp"]), timezone.utc)))
    log_audit(session, actor_id=ctx.id, actor_email=ctx.email, action="logout",
              target_type="user", target_id=ctx.id, detail="")
    return {"signed_out": True}


@router.get("/me", response_model=AuthUserPublic)
def me(ctx: AuthContext = Depends(get_session_auth_context), session: Session = Depends(_db_session, scope="function")) -> AuthUserPublic:
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


# Roles an identity provider's group never demotes or revokes: they are granted here.
PORTAL_MANAGED_ROLES = frozenset({"admin", "client_admin"})


def _scope(ctx: AuthContext) -> str | None:
    """The one client a client admin administers; None for the platform admin. Read from
    the caller's own account, never the request, and never a tenant they switched to."""
    return None if ctx.role == "admin" else ctx.require_organization()


@router.get("/organizations", response_model=list[PortalOrganizationPublic])
def list_organizations(
    ctx: AuthContext = Depends(require_permission("users:manage")),
) -> list[PortalOrganizationPublic]:
    scope = _scope(ctx)
    return [PortalOrganizationPublic(**row) for row in list_organizations_public()
            if scope is None or row["id"] == scope]


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
    session: Session = Depends(_db_session, scope="function"),
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
    # An IdP that says it has not verified the address has not proven who this is.
    if str(claims.get("email_verified", "")).lower() == "false":
        raise HTTPException(status_code=403, detail="Your identity provider has not verified this email address")
    user = session.query(User).filter(User.email == email).one_or_none()

    # With a group map, the person's IdP groups decide their access at every sign-in.
    access = None
    try:
        mapping = oidc.group_map()
        if mapping is not None:
            access = oidc.mapped_access(claims, mapping, oidc.groups_claim_name())
    except oidc.SsoAccessError as exc:
        log_audit(session, actor_id=None, actor_email=email, action="sso_refused",
                  target_type="user", target_id="", detail=str(exc))
        # Removed from every group at the IdP: switch the account off, which also ends its
        # open sessions, schedules and embeds. An admin is managed in the portal.
        if exc.revoke and user is not None and user.is_active and user.role not in PORTAL_MANAGED_ROLES:
            user.is_active = False
            log_audit(session, actor_id=user.id, actor_email=email, action="sso_deactivated",
                      target_type="user", target_id=user.id, detail="in no mapped sign-in group")
        session.commit()
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    created = user is None
    if created:
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
        session.flush()
        log_audit(session, actor_id=user.id, actor_email=email, action="sso_jit_provision",
                  target_type="user", target_id=user.id, detail="OIDC first login")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is deactivated")
    if access and user.role not in PORTAL_MANAGED_ROLES:   # admins are managed in the portal, never by a group
        before = (user.role, user.organization_id, user.row_rules_json)
        sync_sso_access(session, user, access)
        after = (user.role, user.organization_id, user.row_rules_json)
        if after != before and not created:
            log_audit(session, actor_id=user.id, actor_email=email, action="sso_group_sync",
                      target_type="user", target_id=user.id, detail=f"{before} -> {after}")
    # one commit: a new account never exists without the access its groups give
    session.commit()
    session.refresh(user)

    public = user_to_public(user)
    token = create_access_token(
        user_id=public["id"], email=public["email"], role=public["role"],
        client_id=public["client_id"], organization_id=public.get("organization_id"),
        workstreams=public["workstreams"], pwv=password_fingerprint(user.password_hash))

    dest = cfg.get("OIDC_POST_LOGIN_URL") or "/login"
    return RedirectResponse(f"{dest}#sso_token={token}")


@router.get("/users", response_model=list[AuthUserPublic])
def admin_list_users(
    ctx: AuthContext = Depends(require_permission("users:manage")),
    session: Session = Depends(_db_session, scope="function"),
) -> list[AuthUserPublic]:
    return [AuthUserPublic(**row) for row in list_users(session, _scope(ctx))]


@router.post("/users", response_model=AuthUserPublic)
def admin_create_user(
    body: UserCreate,
    ctx: AuthContext = Depends(require_permission("users:manage")),
    session: Session = Depends(_db_session, scope="function"),
) -> AuthUserPublic:
    _require_strong(body.password, body.email)
    try:
        public = create_user(session, ctx.role, body.model_dump(), _scope(ctx))
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="user.create",
            target_type="user",
            target_id=public["id"],
            detail=public["email"],
            organization_id=public.get("organization_id"),
        )
        return AuthUserPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/users/{user_id}", response_model=AuthUserPublic)
def admin_update_user(
    user_id: str,
    body: UserUpdate,
    ctx: AuthContext = Depends(require_permission("users:manage")),
    session: Session = Depends(_db_session, scope="function"),
) -> AuthUserPublic:
    if body.password is not None:
        target = get_user(session, user_id)
        _require_strong(body.password, target.email if target else "")
    try:
        public = update_user(session, ctx.role, ctx.id, user_id, body.model_dump(exclude_unset=True),
                             _scope(ctx))
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="user.update",
            target_type="user",
            target_id=user_id,
            organization_id=public.get("organization_id"),
            # Access changes are recorded as what they became, not just that they happened.
            detail=public["email"] + (f"; row_rules={public['row_rules']}" if "row_rules" in body.model_fields_set else ""),
        )
        return AuthUserPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.get("/groups", response_model=list[AccessGroupPublic])
def admin_list_groups(
    ctx: AuthContext = Depends(require_permission("groups:manage")),
    session: Session = Depends(_db_session, scope="function"),
) -> list[AccessGroupPublic]:
    return [AccessGroupPublic(**row) for row in list_groups(session, _scope(ctx))]


@router.post("/groups", response_model=AccessGroupPublic)
def admin_create_group(
    body: AccessGroupCreate,
    ctx: AuthContext = Depends(require_permission("groups:manage")),
    session: Session = Depends(_db_session, scope="function"),
) -> AccessGroupPublic:
    try:
        public = create_group(session, body.model_dump(), _scope(ctx))
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="group.create",
            target_type="group",
            target_id=public["id"],
            detail=public["name"],
            organization_id=public.get("organization_id"),
        )
        return AccessGroupPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.put("/groups/{group_id}", response_model=AccessGroupPublic)
def admin_update_group(
    group_id: str,
    body: AccessGroupUpdate,
    ctx: AuthContext = Depends(require_permission("groups:manage")),
    session: Session = Depends(_db_session, scope="function"),
) -> AccessGroupPublic:
    try:
        public = update_group(session, group_id, body.model_dump(exclude_unset=True), _scope(ctx))
        log_audit(
            session,
            actor_id=ctx.id,
            actor_email=ctx.email,
            action="group.update",
            target_type="group",
            target_id=group_id,
            detail=public["name"],
            organization_id=public.get("organization_id"),
        )
        return AccessGroupPublic(**public)
    except AuthError as exc:
        raise HTTPException(status_code=404 if "not found" in str(exc).lower() else 400, detail=str(exc)) from exc


@router.delete("/groups/{group_id}")
def admin_delete_group(
    group_id: str,
    ctx: AuthContext = Depends(require_permission("groups:manage")),
    session: Session = Depends(_db_session, scope="function"),
) -> dict[str, str]:
    if not delete_group(session, group_id, _scope(ctx)):
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
    # A named set, not a list of actions the caller assembles: "admin" is every event
    # that changes who can do what, and it is defined once in service.py. Literal so an
    # unknown category is a 422 rather than silently falling through to "everything".
    category: Literal["admin"] | None = None,
    ctx: AuthContext = Depends(require_permission("users:manage")),
    session: Session = Depends(_db_session, scope="function"),
) -> list[dict[str, Any]]:
    return list_audit_events(
        session,
        limit=limit,
        action=action,
        actions=AUDIT_CATEGORIES.get(category) if category else None,
        scope_org=_scope(ctx),
    )
