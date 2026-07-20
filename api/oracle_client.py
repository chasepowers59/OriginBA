"""Shared python-oracledb client initialization for local scripts and API."""

from __future__ import annotations

import os
from pathlib import Path

import oracledb
from dotenv import dotenv_values

_thick_initialized = False
_thick_lib_dir: str | None = None


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load .env values; file entries win over process environment."""
    merged = {k: v for k, v in dotenv_values(env_path).items() if v is not None}
    for key, value in os.environ.items():
        if key not in merged and value:
            merged[key] = value
    return merged


def normalize_oracle_dsn(dsn: str) -> str:
    value = (dsn or "").strip()
    for prefix in ("jdbc:oracle:thin:@//", "jdbc:oracle:thin:@"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    if value.startswith("//"):
        value = value[2:]
    return value


def ensure_oracle_client(
    config: dict[str, str],
    *,
    allow_thick_without_lib_dir: bool = True,
) -> None:
    """Initialize Oracle thick mode when configured in .env."""
    global _thick_initialized, _thick_lib_dir

    thick_mode = (config.get("DB_THICK_MODE") or "").strip().lower() in {"1", "true", "yes", "y"}
    lib_dir = (config.get("ORACLE_CLIENT_LIB_DIR") or "").strip()

    if not thick_mode and not lib_dir:
        return

    if lib_dir and not Path(lib_dir).is_dir():
        if thick_mode:
            raise RuntimeError(
                f"DB_THICK_MODE is enabled but ORACLE_CLIENT_LIB_DIR does not exist: {lib_dir}"
            )
        return

    if _thick_initialized and lib_dir == (_thick_lib_dir or ""):
        return
    if _thick_initialized and not lib_dir:
        return

    try:
        if lib_dir:
            oracledb.init_oracle_client(lib_dir=lib_dir)
        elif thick_mode and allow_thick_without_lib_dir:
            oracledb.init_oracle_client()
        else:
            return
        _thick_initialized = True
        _thick_lib_dir = lib_dir or None
    except oracledb.ProgrammingError:
        _thick_initialized = True
    except oracledb.DatabaseError as exc:
        if not thick_mode:
            return
        raise RuntimeError(
            "Oracle thick mode failed. Verify ORACLE_CLIENT_LIB_DIR and Instant Client install."
        ) from exc
