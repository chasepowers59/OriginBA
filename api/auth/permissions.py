"""Role and permission model for the analytics portal."""

from __future__ import annotations

from typing import Final

RoleName = str  # "user" | "editor" | "admin"

ROLES: Final[tuple[str, ...]] = ("user", "editor", "admin")

ROLE_LABELS: Final[dict[str, str]] = {
    "user": "User",
    "editor": "Editor",
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
        }
    ),
    "admin": frozenset(
        {
            "users:manage",
            "groups:manage",
            "data_source:manage",
            "snapshots:raw_sql",
            "settings:manage",
        }
    ),
}

ROLE_RANK: Final[dict[str, int]] = {"user": 1, "editor": 2, "admin": 3}


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
    """Admins may create editors/users; only admins assign admin."""
    if not role_at_least(actor_role, "admin"):
        return False
    if target_role == "admin":
        return actor_role == "admin"
    return True
