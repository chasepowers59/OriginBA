"""User and access-group business logic."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from api.auth.models import AccessGroup, AuditLog, User, UserAccessGroup
from api.auth.permissions import ROLES, can_assign_role, permissions_for_role
from api.auth.security import hash_password, verify_password
from api.organizations import get_organization, is_valid_org_id
from api.portal_config import load_portal_config


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
) -> None:
    session.add(
        AuditLog(
            client_id=_client_id(),
            actor_id=actor_id,
            actor_email=actor_email.strip().lower() or "system",
            action=action,
            target_type=target_type,
            target_id=target_id,
            detail=detail,
        )
    )


def list_audit_events(session: Session, limit: int = 100,
                      action: str | None = None) -> list[dict[str, Any]]:
    stmt = select(AuditLog).where(AuditLog.client_id == _client_id())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    rows = session.scalars(
        stmt.order_by(AuditLog.created_at.desc()).limit(max(1, min(limit, 500)))
    ).all()
    return [
        {
            "id": row.id,
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


def _validate_organization_id(organization_id: str | None, role: str) -> str | None:
    org_id = (organization_id or "").strip() or None
    if role == "admin" and not org_id:
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
        raise AuthError("Invalid email or password")
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password")
    user.last_login_at = datetime.now(timezone.utc)
    session.add(user)
    return user


def list_users(session: Session) -> list[dict[str, Any]]:
    users = session.scalars(
        select(User)
        .options(selectinload(User.group_links).selectinload(UserAccessGroup.group))
        .where(User.client_id == _client_id())
        .order_by(User.display_name)
    ).all()
    return [user_to_public(u) for u in users]


def get_user(session: Session, user_id: str) -> User | None:
    return session.scalar(
        select(User)
        .options(selectinload(User.group_links).selectinload(UserAccessGroup.group))
        .where(User.id == user_id, User.client_id == _client_id())
    )


def _set_user_groups(session: Session, user: User, group_ids: list[str]) -> None:
    valid_groups = session.scalars(
        select(AccessGroup).where(
            AccessGroup.client_id == _client_id(),
            AccessGroup.id.in_(group_ids),
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


def create_user(session: Session, actor_role: str, payload: dict[str, Any]) -> dict[str, Any]:
    role = payload.get("role", "user")
    if role not in ROLES:
        raise AuthError(f"Invalid role: {role}")
    if not can_assign_role(actor_role, role):
        raise AuthError("You cannot assign that role")

    email = str(payload["email"]).strip().lower()
    existing = session.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise AuthError("A user with this email already exists")

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
) -> dict[str, Any]:
    user = get_user(session, user_id)
    if not user:
        raise AuthError("User not found")

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
    if "organization_id" in payload:
        next_role = payload.get("role", user.role)
        user.organization_id = _validate_organization_id(payload.get("organization_id"), next_role)

    session.add(user)
    return _public_user(session, user.id)


def list_groups(session: Session) -> list[dict[str, Any]]:
    groups = session.scalars(
        select(AccessGroup).where(AccessGroup.client_id == _client_id()).order_by(AccessGroup.name)
    ).all()
    out = []
    for group in groups:
        count = session.scalar(
            select(func.count()).select_from(UserAccessGroup).where(UserAccessGroup.group_id == group.id)
        )
        out.append(
            {
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "client_id": group.client_id,
                "workstreams": group.workstream_ids(),
                "member_count": int(count or 0),
            }
        )
    return out


def create_group(session: Session, payload: dict[str, Any]) -> dict[str, Any]:
    workstreams = payload.get("workstreams") or ["*"]
    group = AccessGroup(
        name=payload["name"].strip(),
        description=(payload.get("description") or "").strip(),
        client_id=_client_id(),
        workstreams_csv=",".join(workstreams) if workstreams != ["*"] else "*",
    )
    session.add(group)
    session.flush()
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "client_id": group.client_id,
        "workstreams": group.workstream_ids(),
        "member_count": 0,
    }


def update_group(session: Session, group_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    group = session.scalar(
        select(AccessGroup).where(AccessGroup.id == group_id, AccessGroup.client_id == _client_id())
    )
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
    count = session.scalar(
        select(func.count()).select_from(UserAccessGroup).where(UserAccessGroup.group_id == group.id)
    )
    return {
        "id": group.id,
        "name": group.name,
        "description": group.description,
        "client_id": group.client_id,
        "workstreams": group.workstream_ids(),
        "member_count": int(count or 0),
    }


def delete_group(session: Session, group_id: str) -> bool:
    group = session.scalar(
        select(AccessGroup).where(AccessGroup.id == group_id, AccessGroup.client_id == _client_id())
    )
    if not group:
        return False
    session.delete(group)
    return True


def workstreams_allowed(workstreams: list[str], workstream_id: str) -> bool:
    if not workstreams or "*" in workstreams:
        return True
    return workstream_id in workstreams
