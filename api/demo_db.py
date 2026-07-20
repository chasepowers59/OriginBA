"""
Oracle connection for the analytics portal.

Priority per organization: portal encrypted vault → org-specific .env → DEMO_* fallback.
"""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import oracledb

from api.oracle_client import ensure_oracle_client, load_env_file, normalize_oracle_dsn


ROOT = Path(__file__).resolve().parent.parent


def load_env() -> dict[str, str]:
    return load_env_file(ROOT / ".env")


def _ensure_thick_mode(*, lib_dir: str = "", thick_mode: bool = False) -> None:
    ensure_oracle_client(
        {
            "DB_THICK_MODE": "true" if thick_mode else "",
            "ORACLE_CLIENT_LIB_DIR": lib_dir,
        }
    )


def env_connection_config(organization_id: str | None = None) -> tuple[str, str, str, str, bool]:
    if organization_id:
        from api.organizations import org_env_connection_config

        org_cfg = org_env_connection_config(organization_id)
        if org_cfg:
            return org_cfg

    config = load_env()
    user = config.get("DEMO_DB_USER") or config.get("DB_USER") or config.get("ORACLE_USER")
    password = config.get("DEMO_DB_PASSWORD") or config.get("DB_PASSWORD") or config.get("ORACLE_PASSWORD")
    dsn = config.get("DEMO_ORACLE_DSN") or config.get("DEMO_DB_CONNECT_STRING")
    lib_dir = (config.get("ORACLE_CLIENT_LIB_DIR") or "").strip()
    thick_mode = (config.get("DB_THICK_MODE") or "").strip().lower() in {"1", "true", "yes", "y"}
    if not user or not password or not dsn:
        raise RuntimeError(
            "Missing demo DB config. Set DEMO_DB_USER, DEMO_DB_PASSWORD, and DEMO_ORACLE_DSN in .env"
        )
    return user, password, dsn, lib_dir, thick_mode


def env_configured(organization_id: str | None = None) -> bool:
    try:
        env_connection_config(organization_id)
        return True
    except RuntimeError:
        return False


def env_connection_config_masked(organization_id: str | None = None) -> dict[str, Any]:
    from api.data_source_store import mask_dsn, mask_user

    user, _password, dsn, lib_dir, thick_mode = env_connection_config(organization_id)
    return {
        "user_masked": mask_user(user),
        "dsn_masked": mask_dsn(dsn),
        "thick_mode": thick_mode,
        "has_oracle_client_lib_dir": bool(lib_dir),
    }


def active_connection_config(organization_id: str) -> tuple[str, str, str, str, bool]:
    from api.data_source_store import load_config

    vault = load_config(organization_id)
    if vault:
        return (
            vault.user,
            vault.password,
            vault.dsn,
            vault.oracle_client_lib_dir,
            vault.thick_mode,
        )
    return env_connection_config(organization_id)


def demo_connection_config(organization_id: str) -> tuple[str, str, str]:
    user, password, dsn, _lib, _thick = active_connection_config(organization_id)
    return user, password, dsn


def demo_configured(organization_id: str | None = None) -> bool:
    if not organization_id:
        return False
    from api.data_source_store import load_config

    if load_config(organization_id) is not None:
        return True
    return env_configured(organization_id)


def test_oracle_connection(config: Any) -> dict[str, Any]:
    """Test connectivity; does not persist credentials."""
    _ensure_thick_mode(
        lib_dir=getattr(config, "oracle_client_lib_dir", "") or "",
        thick_mode=bool(getattr(config, "thick_mode", False)),
    )
    conn = oracledb.connect(
        user=config.user,
        password=config.password,
        dsn=normalize_oracle_dsn(config.dsn),
    )
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM DUAL")
            cur.fetchone()
        return {"message": "Connection successful."}
    finally:
        conn.close()


@contextmanager
def demo_connection(organization_id: str) -> Iterator[Any]:
    user, password, dsn, lib_dir, thick_mode = active_connection_config(organization_id)
    _ensure_thick_mode(lib_dir=lib_dir, thick_mode=thick_mode)
    conn = oracledb.connect(user=user, password=password, dsn=normalize_oracle_dsn(dsn))
    try:
        yield conn
    finally:
        conn.close()


def execute_query(
    sql: str,
    binds: dict[str, Any] | None = None,
    *,
    organization_id: str,
    max_rows: int = 5000,
) -> tuple[list[str], list[list[Any]]]:
    binds = binds or {}
    with demo_connection(organization_id) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, binds)
            if cur.description is None:
                return [], []
            columns = [col[0] for col in cur.description]
            rows = cur.fetchmany(max_rows)
            return columns, [list(row) for row in rows]
