#!/usr/bin/env python3
"""Load Jaspersoft environment promotion profiles for datasource-only rewrites."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict


DEFAULT_PROFILES_PATH = (
    Path(__file__).resolve().parents[2]
    / "deploy"
    / "jaspersoft_environment_promotion"
    / "environment_profiles.json"
)


class ProfileError(Exception):
    """Raised when an environment profile cannot be loaded."""


@dataclass(frozen=True)
class DatasourceProfile:
    label: str
    description: str
    driver: str
    connection_url: str
    connection_user: str
    connection_password: str


@dataclass(frozen=True)
class EnvironmentProfile:
    environment_id: str
    label: str
    src_org: str
    src_ds: str
    target_org: str
    target_ds: str
    output_zip_stem: str
    datasource: DatasourceProfile
    repository_uri_style: str = "full"
    map_standard_offering_to_workstreams: bool = False
    index_module_folder_uri: str | None = None
    import_module_folder_uri: str | None = None
    skip_datasource_import: bool = False
    repository_layout: str = "organizations_tree"
    tenant_id: str | None = None
    import_into_existing_tenant: bool = True

    @property
    def output_zip_name(self) -> str:
        return f"{self.output_zip_stem}_import.zip"

    @property
    def use_org_relative_uris(self) -> bool:
        return self.repository_uri_style == "org_relative"


def load_profiles(path: str | Path | None = None) -> Dict[str, EnvironmentProfile]:
    profiles_path = Path(path) if path else DEFAULT_PROFILES_PATH
    if not profiles_path.is_file():
        raise ProfileError(f"Environment profiles file is missing: {profiles_path}")

    with profiles_path.open("r", encoding="utf-8") as handle:
        raw = json.load(handle)

    if not isinstance(raw, dict):
        raise ProfileError(f"Environment profiles file must contain a JSON object: {profiles_path}")

    profiles: Dict[str, EnvironmentProfile] = {}
    for environment_id, payload in raw.items():
        profiles[environment_id] = _parse_profile(environment_id, payload)
    return profiles


def load_profile(environment_id: str, path: str | Path | None = None) -> EnvironmentProfile:
    profiles = load_profiles(path)
    if environment_id not in profiles:
        known = ", ".join(sorted(profiles))
        raise ProfileError(
            f"Unknown environment '{environment_id}'. Known environments: {known or '(none)'}"
        )
    return profiles[environment_id]


def _parse_profile(environment_id: str, payload: Any) -> EnvironmentProfile:
    if not isinstance(payload, dict):
        raise ProfileError(f"Profile '{environment_id}' must be a JSON object.")

    required = ("src_org", "src_ds", "target_org", "target_ds", "datasource")
    missing = [key for key in required if key not in payload]
    if missing:
        raise ProfileError(f"Profile '{environment_id}' is missing keys: {', '.join(missing)}")

    datasource_payload = payload["datasource"]
    if not isinstance(datasource_payload, dict):
        raise ProfileError(f"Profile '{environment_id}' datasource must be a JSON object.")

    datasource_required = (
        "driver",
        "connectionUrl",
        "connectionUser",
        "connectionPassword",
    )
    datasource_missing = [key for key in datasource_required if key not in datasource_payload]
    if datasource_missing:
        raise ProfileError(
            f"Profile '{environment_id}' datasource is missing keys: "
            f"{', '.join(datasource_missing)}"
        )

    target_ds = str(payload["target_ds"])
    output_zip_stem = str(payload.get("output_zip_stem") or _default_zip_stem(target_ds))
    label = str(payload.get("label") or environment_id)

    repository_uri_style = str(payload.get("repository_uri_style") or "full")
    if repository_uri_style not in {"full", "org_relative"}:
        raise ProfileError(
            f"Profile '{environment_id}' repository_uri_style must be 'full' or 'org_relative'."
        )

    repository_layout = str(payload.get("repository_layout") or "organizations_tree")
    if repository_layout not in {"organizations_tree", "tenant_root"}:
        raise ProfileError(
            f"Profile '{environment_id}' repository_layout must be "
            "'organizations_tree' or 'tenant_root'."
        )

    tenant_id = str(payload["tenant_id"]) if payload.get("tenant_id") else None
    if repository_layout == "tenant_root" and not tenant_id:
        raise ProfileError(
            f"Profile '{environment_id}' requires tenant_id when repository_layout is tenant_root."
        )

    return EnvironmentProfile(
        environment_id=environment_id,
        label=label,
        src_org=str(payload["src_org"]),
        src_ds=str(payload["src_ds"]),
        target_org=str(payload["target_org"]),
        target_ds=target_ds,
        output_zip_stem=output_zip_stem,
        repository_uri_style=repository_uri_style,
        map_standard_offering_to_workstreams=bool(
            payload.get("map_standard_offering_to_workstreams", False)
        ),
        index_module_folder_uri=(
            str(payload["index_module_folder_uri"])
            if payload.get("index_module_folder_uri")
            else None
        ),
        import_module_folder_uri=(
            str(payload["import_module_folder_uri"])
            if payload.get("import_module_folder_uri")
            else None
        ),
        skip_datasource_import=bool(payload.get("skip_datasource_import", False)),
        repository_layout=repository_layout,
        tenant_id=tenant_id,
        import_into_existing_tenant=bool(
            payload.get("import_into_existing_tenant", True)
        ),
        datasource=DatasourceProfile(
            label=str(datasource_payload.get("label") or target_ds),
            description=str(
                datasource_payload.get("description")
                or f"JDBC datasource for {label}."
            ),
            driver=str(datasource_payload["driver"]),
            connection_url=str(datasource_payload["connectionUrl"]),
            connection_user=str(datasource_payload["connectionUser"]),
            connection_password=str(datasource_payload["connectionPassword"]),
        ),
    )


def _default_zip_stem(target_ds: str) -> str:
    if target_ds.endswith("_DS"):
        return target_ds[:-3]
    return target_ds
