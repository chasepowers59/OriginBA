"""Role and permission model for the analytics portal."""

from __future__ import annotations

from typing import Final

RoleName = str  # "user" | "editor" | "client_admin" | "admin"

ROLES: Final[tuple[str, ...]] = ("user", "editor", "client_admin", "admin")

ROLE_LABELS: Final[dict[str, str]] = {
    "user": "User",
    "editor": "Editor",
    "client_admin": "Client admin",
    "admin": "Admin",
}

# Each role inherits permissions from lower roles.
ROLE_PERMISSIONS: Final[dict[str, frozenset[str]]] = {
    "user": frozenset(
        {
            "portal:read",
            "report_library:read",
            "snapshots:read",
            "snapshots:query",
            "database:sql",
            "nlq:read",
        }
    ),
    "editor": frozenset(
        {
            "saved_views:write",
            "dashboards:write",
            "explorer:builder",
            # Collections letters carry names, addresses and amounts owed: editors and up.
            # A run is approved by someone other than its creator (api/letters/runs.py).
            "letters:read",
            "letters:generate",
            "letters:approve",
            "letters:release",
        }
    ),
    # Administers ONE client: its users, groups and audit trail, scoped by organization in
    # api/auth/service.py. Never the platform powers below, never another client.
    "client_admin": frozenset(
        {
            "users:manage",
            "groups:manage",
        }
    ),
    # The platform (root) admin: every client, no organization of their own.
    "admin": frozenset(
        {
            "data_source:manage",
            "snapshots:raw_sql",
            "settings:manage",
        }
    ),
}

ROLE_RANK: Final[dict[str, int]] = {"user": 1, "editor": 2, "client_admin": 3, "admin": 4}


def permissions_for_role(role: str) -> set[str]:
    rank = ROLE_RANK.get(role, 0)
    perms: set[str] = set()
    for name, level in ROLE_RANK.items():
        if level <= rank:
            perms |= set(ROLE_PERMISSIONS.get(name, frozenset()))
    return perms


def role_at_least(role: str, minimum: str) -> bool:
    """Whether `role` satisfies a requirement of `minimum`.

    The MINIMUM used to default to rank 0 when unrecognised, so a misspelled
    requirement ("adminn", "owner") admitted every caller -- while an unrecognised
    ACTOR role already failed closed. The two directions disagreed, and the open one is
    the one that matters. An unknown requirement is now unsatisfiable.
    """
    required = ROLE_RANK.get(minimum)
    if required is None:
        return False
    return ROLE_RANK.get(role, 0) >= required


def can_assign_role(actor_role: str, target_role: str) -> bool:
    """The platform admin assigns any role; a client admin assigns every role but admin
    (within their own client, which the service enforces); nobody else assigns roles."""
    if actor_role == "admin":
        return True
    if actor_role == "client_admin":
        return target_role in ("user", "editor", "client_admin")
    return False
