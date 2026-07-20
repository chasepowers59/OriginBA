"""Analytics portal client branding and theme configuration."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "analytics_portal_client.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "client_id": "demo",
    "organization_name": "Origin Utilities",
    "brand": {
        "name": "OriginBA",
        "product": "Utility Insights",
        "tagline": "Modern analytics for water, electric, and gas utilities",
        "logo_initials": "BA",
        "logo_src": "/brand-icon.svg",
        "connection_label": "Connected",
        "footer": "Trusted snapshot data · refreshed on schedule · ready for council and regulator reporting",
    },
    "theme": {
        "accent_from": "#38bdf8",
        "accent_to": "#6366f1",
        "accent_muted": "#0ea5e9",
        "mesh_glow_1": "rgba(56, 189, 248, 0.12)",
        "mesh_glow_2": "rgba(99, 102, 241, 0.14)",
        "mesh_glow_3": "rgba(14, 165, 233, 0.08)",
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
