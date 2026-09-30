"""Analytics portal client branding and theme configuration."""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.organizations import get_organization

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "analytics_portal_client.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "client_id": "demo",
    "organization_name": "Origin Utilities",
    "brand": {
        "name": "OriginBA",
        "product": "OriginBA",
        "tagline": "Governed analytics for water, electric and gas utilities",
        "logo_initials": "BA",
        "logo_src": "/brand-icon.svg",
        "connection_label": "Connected",
        "footer": "Built on the Origin reporting layer · every figure traceable to its source in your CIS",
    },
    "theme": {
        "accent_from": "#3BAFE2",
        "accent_to": "#1348AB",
        "accent_muted": "#006FAC",
        "mesh_glow_1": "rgba(59, 175, 226, 0.12)",
        "mesh_glow_2": "rgba(19, 72, 171, 0.14)",
        "mesh_glow_3": "rgba(0, 111, 172, 0.08)",
    },
}


@lru_cache(maxsize=1)
def load_portal_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    merged = DEFAULT_CONFIG.copy()
    merged.update({k: v for k, v in data.items() if k != "brand" and k != "theme"})
    brand = {**DEFAULT_CONFIG["brand"], **data.get("brand", {})}
    if "connection_label" not in brand and brand.get("demo_label"):
        brand["connection_label"] = brand.pop("demo_label")
    merged["brand"] = brand
    merged["theme"] = {**DEFAULT_CONFIG["theme"], **data.get("theme", {})}
    return merged


# ------------------------------------------------------------- per-organization brand
# An organization's record may carry "branding": {"brand": {...}, "theme": {...}}, merged
# over the default for that organization only (tests/test_org_branding.py). Only keys the
# default has are taken; colours must be hex or rgb(a); a logo must be a path the portal
# serves itself, so a config file cannot make the browser load from elsewhere.
_COLOUR = re.compile(r"^(#[0-9a-fA-F]{3,8}|rgba?\(\s*[0-9.]+\s*,\s*[0-9.]+\s*,\s*[0-9.]+\s*(,\s*[0-9.]+\s*)?\))$")
PUBLIC_DIR = ROOT / "apps" / "analytics-portal" / "public"


def _served_here(path: str) -> bool:
    return path.startswith("/") and not path.startswith("//") and ".." not in path


def config_for_organization(organization_id: str | None) -> dict[str, Any]:
    base = load_portal_config()
    config = {**base, "brand": dict(base["brand"]), "theme": dict(base["theme"])}
    org = get_organization(organization_id) if organization_id else None
    if not org:
        return config
    config["organization_id"] = organization_id
    config["organization_name"] = org["display_name"]
    branding = org.get("branding") or {}
    for key, value in (branding.get("brand") or {}).items():
        if key in config["brand"] and isinstance(value, str) and value.strip() \
                and (key != "logo_src" or _served_here(value)):
            config["brand"][key] = value.strip()
    for key, value in (branding.get("theme") or {}).items():
        if key in config["theme"] and isinstance(value, str) and _COLOUR.match(value.strip()):
            config["theme"][key] = value.strip()
    return config


def pdf_logo_path(organization_id: str | None) -> Path | None:
    """The organization's own logo for PDFs, when it set one that is a PNG the portal serves."""
    org = get_organization(organization_id) if organization_id else None
    src = (((org or {}).get("branding") or {}).get("brand") or {}).get("logo_src") or ""
    if not (isinstance(src, str) and _served_here(src) and src.lower().endswith(".png")):
        return None
    path = PUBLIC_DIR / src.lstrip("/")
    return path if path.is_file() else None
