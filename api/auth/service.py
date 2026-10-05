"""User and access-group business logic."""

from __future__ import annotations

import json
from collections.abc import Collection
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from api.auth.models import AccessGroup, AuditLog, User, UserAccessGroup
from api.auth.permissions import ROLES, can_assign_role, permissions_for_role
from api.auth.security import dummy_password_check, hash_password, needs_rehash, verify_password
from api.organizations import get_organization, is_valid_org_id
from api.portal_config import load_portal_config
from api.row_security import clean_rules


class AuthError(ValueError):
    pass


def _client_id() -> str:
    return load_portal_config().get("client_id", "demo")


def log_audit(
    session: Session,
    *,
    actor_id: str | None,
    actor_email: str,
    action: str,
    target_type: str = "",
    target_id: str = "",
    detail: str = "",
    organization_id: str | None = None,
) -> None:
    # The client the event belongs to: given (the target's), else the actor's own.
    if organization_id is None and actor_id:
        actor = session.get(User, actor_id)
        organization_id = actor.organization_id if actor else None
    session.add(
        AuditLog(
            client_id=_client_id(),
            organization_id=organization_id,
            actor_id=actor_id,
            actor_email=actor_email.strip().lower() or "system",
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )


# Who-can-do-what changed, plus the security events that are not just a query running.
# The Users & access feed asks for this set BY NAME: it used to ask for everything and
# take the newest 40, and report_run -- the highest-volume action there is -- filled
# every slot, so not one permission change was visible. Naming the set here rather than
# listing action names in the client is what keeps the two from drifting apart.
ADMIN_AUDIT_ACTIONS: frozenset[str] = frozenset({
    "user.create",
    "user.update",
    "user.password_change",
    "group.create",
    "group.update",
    "group.delete",
    # No admin acts on these two, which is exactly why they belong in this feed.
    "sso_jit_provision",
    "sql_refused",
})

AUDIT_CATEGORIES: dict[str, frozenset[str]] = {"admin": ADMIN_AUDIT_ACTIONS}


def list_audit_events(session: Session, limit: int = 100,
                      action: str | None = None,
                      actions: Collection[str] | None = None,
                      scope_org: str | None = None) -> list[dict[str, Any]]:
    stmt = select(AuditLog).where(AuditLog.client_id == _client_id())
    if scope_org:
        stmt = stmt.where(AuditLog.organization_id == scope_org)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actions:
        # Narrowed in the query, not after it: filtering a page that telemetry already
        # filled would still come back empty.
        stmt = stmt.where(AuditLog.action.in_(sorted(actions)))
    rows = session.scalars(
        stmt.order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 500)))
    ).all()
    return [
        {
            "id": row.id,
            "organization_id": row.organization_id,
            "actor_email": row.actor_email,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "detail": row.detail,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def _workstreams_for_user(user: User) -> list[str]:
    groups = [link.group for link in user.group_links if link.group]
    if not groups:
        return ["*"]
    merged: set[str] = set()
    for group in groups:
        for ws in group.workstream_ids():
            merged.add(ws)
    return sorted(merged) if merged else ["*"]


# An admin is a PLATFORM admin: no organization of their own, and therefore every
# organization. Binding one to a single client used to be accepted and looked like it
# scoped them, but nothing in the backend reads that field for authorization -- users,
# groups and the audit log are all filtered by client_id, which is one value for the
# whole deployment -- so the account was a deployment-wide superuser wearing a client's
# name. The invariant is enforced here so both the create and update paths inherit it.
# The per-client tier is the client_admin role (2026-09-30): groups and the audit log now
# carry an organization, and every read and write is scoped to it (tests/test_client_admin.py).
ADMIN_ORG_ERROR = (
    "An admin administers every client and cannot be bound to one. "
    "Leave the organization blank, or use the client admin role for one client."
)


def _validate_organization_id(organization_id: str | None, role: str) -> str | None:
    org_id = (organization_id or "").strip() or None
    if role == "admin":
        if org_id:
            raise AuthError(ADMIN_ORG_ERROR)
        return None
    if not org_id:
        raise AuthError("Organization is required for this role")
    if not is_valid_org_id(org_id):
        raise AuthError("Invalid organization")
    return org_id


def user_to_public(user: User) -> dict[str, Any]:
    groups = [link.group for link in user.group_links if link.group]
    workstreams = _workstreams_for_user(user)
    org_id = user.organization_id
    return {
        "id": user.id,
        "email": user.email,
        "display_name": user.display_name,
        "role": user.role,
        "client_id": user.client_id,
        "organization_id": org_id,
        "organization_name": get_organization(org_id)["display_name"] if org_id and get_organization(org_id) else None,
        "is_active": user.is_active,
        "must_change_password": bool(user.must_change_password),
        "workstreams": workstreams,
        "row_rules": json.loads(user.row_rules_json) if user.row_rules_json else [],
        "permissions": sorted(permissions_for_role(user.role)),
        "group_ids": [g.id for g in groups],
        "group_names": [g.name for g in groups],
    }


def authenticate_user(session: Session, email: str, password: str) -> User:
    user = session.scalar(
        select(User)
        .options(selectinload(User.group_links).selectinload(UserAccessGroup.group))
        .where(func.lower(User.email) == email.strip().lower())
    )
    if not user or not user.is_active:
        dummy_password_check(password)   # same work, same time: timing must not list accounts
        raise AuthError("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    return user


# `scope_org` below is the client a CLIENT ADMIN administers; None is the platform admin,
# who sees every client. It comes from the caller's own account (api/auth/routes.py
# _scope), never from the request.

def list_users(session: Session, scope_org: str | None = None) -> list[dict[str, Any]]:
    stmt = (select(User)
            .options(selectinload(User.group_links).selectinload(UserAccessGroup.group))
            .where(User.client_id == _client_id()))
    if scope_org:
        stmt = stmt.where(User.organization_id == scope_org)
    users = session.scalars(stmt.order_by(User.display_name)).all()
    return [user_to_public(u) for u in users]


def get_user(session: Session, user_id: str, scope_org: str | None = None) -> User | None:
    stmt = (select(User)
            .options(selectinload(User.group_links).selectinload(UserAccessGroup.group))
            .where(User.id == user_id, User.client_id == _client_id()))
    if scope_org:
        stmt = stmt.where(User.organization_id == scope_org)
    return session.scalar(stmt)


def _set_user_groups(session: Session, user: User, group_ids: list[str]) -> None:
    # A user joins platform groups or their own client's, never another client's.
    valid_groups = session.scalars(
        select(AccessGroup).where(
            AccessGroup.client_id == _client_id(),
            AccessGroup.id.in_(group_ids),
            (AccessGroup.organization_id.is_(None)) | (AccessGroup.organization_id == user.organization_id),
        )
    ).all()
    valid_ids = {g.id for g in valid_groups}
    user.group_links.clear()
    for gid in valid_ids:
        user.group_links.append(UserAccessGroup(user_id=user.id, group_id=gid))
    session.flush()


def _public_user(session: Session, user_id: str) -> dict[str, Any]:
    user = get_user(session, user_id)
    if not user:
        raise AuthError("User not found")
    return user_to_public(user)


def _admin_count(session: Session, exclude_user_id: str | None = None) -> int:
    stmt = select(func.count()).select_from(User).where(
        User.client_id == _client_id(),
        User.role == "admin",
        User.is_active.is_(True),
    )
    if exclude_user_id:
        stmt = stmt.where(User.id != exclude_user_id)
    return int(session.scalar(stmt) or 0)


def change_password(session: Session, user_id: str, current_password: str, new_password: str) -> dict[str, Any]:
    user = get_user(session, user_id)
    if not user or not user.is_active:
        raise AuthError("User not found")
    if not verify_password(current_password, user.password_hash):
        raise AuthError("Current password is incorrect")
    if current_password == new_password:
        raise AuthError("New password must be different from the current password")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    session.add(user)
    return _public_user(session, user.id)


CLIENT_SCOPE_ERROR = "A client admin manages users of their own client only."


def create_user(session: Session, actor_role: str, payload: dict[str, Any],
                scope_org: str | None = None) -> dict[str, Any]:
    role = payload.get("role", "user")
    if role not in ROLES:
        raise AuthError(f"Invalid role: {role}")
    if not can_assign_role(actor_role, role):
        raise AuthError("You cannot assign that role")

    email = str(payload["email"]).strip().lower()
    existing = session.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise AuthError("A user with this email already exists")

    if scope_org:
        requested = (payload.get("organization_id") or "").strip() or scope_org
        if requested != scope_org:
            raise AuthError(CLIENT_SCOPE_ERROR)
        payload = {**payload, "organization_id": scope_org}
    organization_id = _validate_organization_id(payload.get("organization_id"), role)

    user = User(
        email=email,
        display_name=payload["display_name"].strip(),
        password_hash=hash_password(payload["password"]),
        role=role,
        client_id=_client_id(),
        organization_id=organization_id,
        is_active=bool(payload.get("is_active", True)),
        must_change_password=True,
    )
    session.add(user)
    session.flush()
    _set_user_groups(session, user, payload.get("group_ids") or [])
    return _public_user(session, user.id)


def update_user(
    session: Session,
    actor_role: str,
    actor_user_id: str,
    user_id: str,
    payload: dict[str, Any],
    scope_org: str | None = None,
) -> dict[str, Any]:
    user = get_user(session, user_id, scope_org)
    if not user:
        raise AuthError("User not found")
    if scope_org and "organization_id" in payload and payload["organization_id"] != scope_org:
        raise AuthError(CLIENT_SCOPE_ERROR)

    is_self = actor_user_id == user_id

    if payload.get("role") is not None:
        role = payload["role"]
        if role not in ROLES:
            raise AuthError(f"Invalid role: {role}")
        if not can_assign_role(actor_role, role):
            raise AuthError("You cannot assign that role")
        if is_self and role != user.role:
            raise AuthError("You cannot change your own role")
        if user.role == "admin" and role != "admin" and _admin_count(session, exclude_user_id=user_id) == 0:
            raise AuthError("At least one active admin is required")
        user.role = role
        if role != "admin" and not (payload.get("organization_id") or user.organization_id):
            raise AuthError("Organization is required for this role")
        # Promotion carries the old organization unless the caller clears it, and the
        # panel's role dropdown sends only {role} -- so without this an org-bound editor
        # promoted to admin kept their client and became the very account the invariant
        # forbids, never passing through _validate_organization_id at all.
        # The organization is assigned further down, so read what this request will
        # LEAVE the user with: an explicit value (including a deliberate null) if the
        # caller sent one, otherwise the organization they already carry.
        if role == "admin":
            resulting_org = (
                payload["organization_id"] if "organization_id" in payload
                else user.organization_id
            )
            if resulting_org:
                raise AuthError(ADMIN_ORG_ERROR)

    if payload.get("display_name") is not None:
        user.display_name = payload["display_name"].strip()
    if payload.get("is_active") is not None:
        if is_self and not bool(payload["is_active"]):
            raise AuthError("You cannot deactivate your own account")
        if user.role == "admin" and user.is_active and not bool(payload["is_active"]):
            if _admin_count(session, exclude_user_id=user_id) == 0:
                raise AuthError("At least one active admin is required")
        user.is_active = bool(payload["is_active"])
    if payload.get("password"):
        user.password_hash = hash_password(payload["password"])
        user.must_change_password = actor_user_id != user_id
    if payload.get("group_ids") is not None:
        _set_user_groups(session, user, payload["group_ids"])
    if payload.get("row_rules") is not None:
        try:
            rules = clean_rules(payload["row_rules"])
        except ValueError as exc:
            raise AuthError(str(exc)) from exc
        if rules and payload.get("role", user.role) == "admin":
            raise AuthError("Administrators see every row; row rules apply to users and editors")
        user.row_rules_json = json.dumps(rules) if rules else None
    if "organization_id" in payload:
        next_role = payload.get("role", user.role)
        user.organization_id = _validate_organization_id(payload.get("organization_id"), next_role)

    session.add(user)
    return _public_user(session, user.id)


def _group_public(session: Session, group: AccessGroup) -> dict[str, Any]:
    count = session.scalar(
        select(func.count()).select_from(UserAccessGroup).where(UserAccessGroup.group_id == group.id)
    )
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "client_id": group.client_id,
        "organization_id": group.organization_id,
        "workstreams": group.workstream_ids(),
        "member_count": int(count or 0),
    }


def _group(session: Session, group_id: str, scope_org: str | None) -> AccessGroup | None:
    stmt = select(AccessGroup).where(AccessGroup.id == group_id, AccessGroup.client_id == _client_id())
    if scope_org:
        stmt = stmt.where(AccessGroup.organization_id == scope_org)
    return session.scalar(stmt)


def list_groups(session: Session, scope_org: str | None = None) -> list[dict[str, Any]]:
    stmt = select(AccessGroup).where(AccessGroup.client_id == _client_id())
    if scope_org:
        stmt = stmt.where(AccessGroup.organization_id == scope_org)
    return [_group_public(session, g) for g in session.scalars(stmt.order_by(AccessGroup.name)).all()]


def create_group(session: Session, payload: dict[str, Any], scope_org: str | None = None) -> dict[str, Any]:
    workstreams = payload.get("workstreams") or ["*"]
    requested = (payload.get("organization_id") or "").strip() or None
    if scope_org and requested not in (None, scope_org):
        raise AuthError("A client admin manages groups of their own client only.")
    organization_id = scope_org or requested
    if organization_id and not is_valid_org_id(organization_id):
        raise AuthError("Invalid organization")
    group = AccessGroup(
        name=payload["name"].strip(),
        description=(payload.get("description") or "").strip(),
        client_id=_client_id(),
        organization_id=organization_id,
        workstreams_csv=",".join(workstreams) if workstreams != ["*"] else "*",
    )
    session.add(group)
    session.flush()
    return _group_public(session, group)


def update_group(session: Session, group_id: str, payload: dict[str, Any],
                 scope_org: str | None = None) -> dict[str, Any]:
    group = _group(session, group_id, scope_org)
    if not group:
        raise AuthError("Access group not found")
    if payload.get("name") is not None:
        group.name = payload["name"].strip()
    if payload.get("description") is not None:
        group.description = payload["description"].strip()
    if payload.get("workstreams") is not None:
        ws = payload["workstreams"] or ["*"]
        group.workstreams_csv = ",".join(ws) if ws != ["*"] else "*"
    session.add(group)
    return _group_public(session, group)


def delete_group(session: Session, group_id: str, scope_org: str | None = None) -> bool:
    group = _group(session, group_id, scope_org)
    if not group:
        return False
    session.delete(group)
    return True


def workstreams_allowed(workstreams: list[str], workstream_id: str) -> bool:
    if not workstreams or "*" in workstreams:
        return True
    return workstream_id in workstreams


def sync_sso_access(session: Session, user: User, access: dict[str, Any]) -> None:
    """Set a user's role, organization, row rules and (when the map names them) access groups
    from their identity-provider groups. Never called for an admin."""
    user.role = access["role"]
    user.organization_id = access.get("organization_id") or user.organization_id
    if access.get("row_rules") is not None:   # already checked by mapped_access
        user.row_rules_json = json.dumps(access["row_rules"]) if access["row_rules"] else None
    if access.get("access_groups"):
        ids = [g.id for g in session.scalars(select(AccessGroup).where(AccessGroup.name.in_(access["access_groups"])))]
        _set_user_groups(session, user, ids)
    session.add(user)
