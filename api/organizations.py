"""SmartCity client organization registry and per-org Oracle connection resolution."""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import dotenv_values


ROOT = Path(__file__).resolve().parent.parent
ORG_CONFIG_PATH = ROOT / "config" / "portal_organizations.json"


def _load_env() -> dict[str, str]:
    values = dotenv_values(ROOT / ".env")
    return {k: v for k, v in values.items() if v is not None}


@lru_cache(maxsize=1)
def load_organizations() -> list[dict[str, Any]]:
    if not ORG_CONFIG_PATH.exists():
        return []
    data = json.loads(ORG_CONFIG_PATH.read_text(encoding="utf-8"))
    orgs = data.get("organizations") or []
    return sorted(orgs, key=lambda row: str(row.get("display_name", "")).lower())


def list_organizations_public() -> list[dict[str, str]]:
    return [
        {
            "id": str(org["id"]),
            "display_name": str(org["display_name"]),
        }
        for org in load_organizations()
    ]


def is_valid_org_id(org_id: str | None) -> bool:
    if not org_id:
        return False
    return any(org["id"] == org_id for org in load_organizations())


def get_organization(org_id: str | None) -> dict[str, Any] | None:
    if not org_id:
        return None
    for org in load_organizations():
        if org["id"] == org_id:
            return org
    return None


def organization_display_name(org_id: str | None) -> str | None:
    org = get_organization(org_id)
    return str(org["display_name"]) if org else None


def _env_value(env: dict[str, str], *keys: str) -> str | None:
    for key in keys:
        value = (env.get(key) or os.getenv(key) or "").strip()
        if value:
            return value
    return None


def org_env_connection_config(org_id: str) -> tuple[str, str, str, str, bool] | None:
    """Resolve Oracle credentials for an organization from .env (no vault)."""
    org = get_organization(org_id)
    if not org:
        return None

    env = _load_env()
    prefix = str(org.get("env_prefix") or org_id.upper())

    user = _env_value(env, f"{prefix}_DB_USER", f"{prefix}_ORACLE_USER")
    password = _env_value(env, f"{prefix}_DB_PASSWORD", f"{prefix}_ORACLE_PASSWORD")
    dsn = _env_value(env, f"{prefix}_ORACLE_DSN", f"{prefix}_DB_CONNECT_STRING")

    if not user or not password:
        user = _env_value(env, "DEMO_DB_USER", "DB_USER", "ORACLE_USER")
        password = _env_value(env, "DEMO_DB_PASSWORD", "DB_PASSWORD", "ORACLE_PASSWORD")

    if not dsn:
        dsn = str(org.get("default_dsn") or "").strip() or None

    lib_dir = _env_value(env, f"{prefix}_ORACLE_CLIENT_LIB_DIR", "ORACLE_CLIENT_LIB_DIR") or ""
    thick_raw = _env_value(env, f"{prefix}_DB_THICK_MODE", "DB_THICK_MODE") or ""
    thick_mode = thick_raw.lower() in {"1", "true", "yes", "y"}

    if not user or not password or not dsn:
        return None
    return user, password, dsn, lib_dir, thick_mode


def org_env_configured(org_id: str) -> bool:
    return org_env_connection_config(org_id) is not None


def dev_organization_id() -> str | None:
    env = _load_env()
    org_id = (env.get("PORTAL_DEV_ORGANIZATION") or os.getenv("PORTAL_DEV_ORGANIZATION") or "").strip()
    if org_id and is_valid_org_id(org_id):
        return org_id
    orgs = load_organizations()
    return str(orgs[0]["id"]) if orgs else None
