"""
Encrypted server-side Oracle data-source overrides for the analytics portal.

Credentials are never returned to clients after save. Passwords are not stored in
the browser, JRXML, or git — only in an encrypted vault file (or in-memory fallback).

Vault format (v2): { "version": 2, "organizations": { "<org_id>": { ...config } } }
Legacy single-org payloads are read as a global fallback when an org has no entry.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet, InvalidToken


ROOT = Path(__file__).resolve().parent.parent
VAULT_PATH = ROOT / "output" / ".portal_data_source.vault"
KEY_PATH = ROOT / "output" / ".portal_vault_key"

_memory_config: dict[str, dict[str, Any]] | None = None


@dataclass
class DataSourceConfig:
    user: str
    password: str
    dsn: str
    oracle_client_lib_dir: str = ""
    thick_mode: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "password": self.password,
            "dsn": self.dsn,
            "oracle_client_lib_dir": self.oracle_client_lib_dir,
            "thick_mode": self.thick_mode,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DataSourceConfig:
        return cls(
            user=str(data["user"]).strip(),
            password=str(data["password"]),
            dsn=str(data["dsn"]).strip(),
            oracle_client_lib_dir=str(data.get("oracle_client_lib_dir") or "").strip(),
            thick_mode=bool(data.get("thick_mode")),
        )


def _fernet() -> Fernet | None:
    env_key = (os.getenv("PORTAL_DB_ENCRYPTION_KEY") or "").strip()
    if env_key:
        try:
            return Fernet(env_key.encode("utf-8"))
        except Exception:
            return None
    try:
        if KEY_PATH.exists():
            return Fernet(KEY_PATH.read_bytes())
        KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        key = Fernet.generate_key()
        KEY_PATH.write_bytes(key)
        try:
            KEY_PATH.chmod(0o600)
        except OSError:
            pass
        return Fernet(key)
    except Exception:
        return None


def _write_vault(payload: dict[str, Any]) -> bool:
    fernet = _fernet()
    if not fernet:
        return False
    token = fernet.encrypt(json.dumps(payload).encode("utf-8"))
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    VAULT_PATH.write_bytes(token)
    try:
        VAULT_PATH.chmod(0o600)
    except OSError:
        pass
    return True


def _read_vault_raw() -> dict[str, Any] | None:
    if not VAULT_PATH.exists():
        return None
    fernet = _fernet()
    if not fernet:
        return None
    try:
        raw = fernet.decrypt(VAULT_PATH.read_bytes())
        return json.loads(raw.decode("utf-8"))
    except (InvalidToken, json.JSONDecodeError, OSError):
        return None


def _normalize_vault(data: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not data:
        return {}
    if "organizations" in data and isinstance(data["organizations"], dict):
        return {str(k): dict(v) for k, v in data["organizations"].items() if isinstance(v, dict)}
    if "user" in data:
        return {"_legacy": dict(data)}
    return {}


def _read_vault_orgs() -> dict[str, dict[str, Any]]:
    global _memory_config
    disk = _normalize_vault(_read_vault_raw())
    if disk:
        return disk
    if _memory_config:
        return dict(_memory_config)
    return {}


def _vault_document(organizations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    return {"version": 2, "organizations": organizations}


def save_config(config: DataSourceConfig, *, organization_id: str) -> dict[str, Any]:
    global _memory_config
    org_id = organization_id.strip()
    if not org_id:
        raise ValueError("organization_id is required")

    payload = config.as_dict()
    organizations = _read_vault_orgs()
    organizations[org_id] = payload
    document = _vault_document(organizations)

    if _write_vault(document):
        _memory_config = None
        return {"persisted": True, "storage": "encrypted_vault", "organization_id": org_id}
    _memory_config = organizations
    return {
        "persisted": False,
        "storage": "memory",
        "organization_id": org_id,
        "warning": "Vault encryption unavailable — credentials last until API restart.",
    }


def clear_config(*, organization_id: str) -> None:
    global _memory_config
    org_id = organization_id.strip()
    organizations = _read_vault_orgs()
    organizations.pop(org_id, None)
    organizations.pop("_legacy", None)

    if organizations:
        if _write_vault(_vault_document(organizations)):
            _memory_config = None
        else:
            _memory_config = organizations
    else:
        _memory_config = None
        if VAULT_PATH.exists():
            VAULT_PATH.unlink(missing_ok=True)


def load_config(organization_id: str | None = None) -> DataSourceConfig | None:
    organizations = _read_vault_orgs()
    if organization_id:
        data = organizations.get(organization_id)
        if data:
            try:
                return DataSourceConfig.from_dict(data)
            except (KeyError, ValueError):
                pass
    legacy = organizations.get("_legacy")
    if legacy:
        try:
            return DataSourceConfig.from_dict(legacy)
        except (KeyError, ValueError):
            pass
    return None


def vault_configured(organization_id: str | None = None) -> bool:
    return load_config(organization_id) is not None


def mask_user(user: str) -> str:
    user = user.strip()
    if len(user) <= 2:
        return "***"
    return f"{user[:2]}***"


def mask_dsn(dsn: str) -> str:
    dsn = dsn.strip()
    if not dsn:
        return ""
    if "/" in dsn:
        host_part, service = dsn.rsplit("/", 1)
        host_masked = _mask_host(host_part)
        svc = service[:2] + "***" if len(service) > 2 else "***"
        return f"{host_masked}/{svc}"
    return _mask_host(dsn)


def _mask_host(host_part: str) -> str:
    if ":" in host_part:
        host, port = host_part.rsplit(":", 1)
        return f"{_mask_host(host)}:{port}"
    if len(host_part) <= 4:
        return "***"
    return f"{host_part[:4]}***{host_part[-2:]}" if len(host_part) > 6 else f"{host_part[:2]}***"


def public_status(*, organization_id: str, env_configured: bool) -> dict[str, Any]:
    cfg = load_config(organization_id)
    organizations = _read_vault_orgs()
    org_data = organizations.get(organization_id) or {}

    if cfg and organization_id in organizations:
        return {
            "configured": True,
            "source": "portal_vault" if VAULT_PATH.exists() else "portal_memory",
            "organization_id": organization_id,
            "user_masked": mask_user(cfg.user),
            "dsn_masked": mask_dsn(cfg.dsn),
            "thick_mode": cfg.thick_mode,
            "has_oracle_client_lib_dir": bool(cfg.oracle_client_lib_dir),
            "saved_at": org_data.get("saved_at"),
            "env_fallback_available": env_configured,
        }
    if env_configured:
        from api.demo_db import env_connection_config_masked

        masked = env_connection_config_masked(organization_id)
        return {
            "configured": True,
            "source": "environment",
            "organization_id": organization_id,
            "user_masked": masked.get("user_masked", "***"),
            "dsn_masked": masked.get("dsn_masked", ""),
            "thick_mode": masked.get("thick_mode", False),
            "has_oracle_client_lib_dir": masked.get("has_oracle_client_lib_dir", False),
            "saved_at": None,
            "env_fallback_available": True,
        }
    return {
        "configured": False,
        "source": "none",
        "organization_id": organization_id,
        "user_masked": None,
        "dsn_masked": None,
        "thick_mode": False,
        "has_oracle_client_lib_dir": False,
        "saved_at": None,
        "env_fallback_available": False,
    }


def settings_token_required() -> bool:
    return bool((os.getenv("PORTAL_SETTINGS_TOKEN") or "").strip())


def verify_settings_token(header_value: str | None) -> bool:
    expected = (os.getenv("PORTAL_SETTINGS_TOKEN") or "").strip()
    if not expected:
        return True
    return bool(header_value and header_value.strip() == expected)


def validate_dsn(dsn: str) -> None:
    dsn = dsn.strip()
    if not dsn or len(dsn) > 512:
        raise ValueError("DSN must be between 1 and 512 characters.")
    if not re.match(r"^[\w.\-:@/]+$", dsn):
        raise ValueError("DSN contains unsupported characters.")


def validate_user(user: str) -> None:
    user = user.strip()
    if not user or len(user) > 128:
        raise ValueError("Username must be between 1 and 128 characters.")
