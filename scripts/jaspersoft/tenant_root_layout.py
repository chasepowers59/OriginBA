#!/usr/bin/env python3
"""Repackage Jaspersoft exports for Origin_DEMO-style tenant-root repository layout."""

from __future__ import annotations

import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

class ProcessingError(Exception):
    """Raised when tenant-root repackage cannot complete."""


def read_text_file(path: str) -> tuple[Optional[str], Optional[str]]:
    for encoding in ("utf-8", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                return handle.read(), encoding
        except (UnicodeDecodeError, OSError):
            continue
    return None, None


ORGANIZATIONS_ROOT_PARTS = (
    "resources",
    "organizations",
    "organization_1",
    "organizations",
)

PUBLIC_DASHBOARD_TEMPLATE_URI = "/public/templates/actual_size.820.jrxml"

# Development/Snapshots duplicate domains -> canonical workstream domain URIs.
DEVELOPMENT_SNAPSHOT_TO_WORKSTREAM: dict[str, str] = {
    "Development/Snapshots/Billed_Usage/Amount_Billed/Billed_Usage_Snapshot___Domain": (
        "Billing_and_Rates/Billed_Amount/Billed_Usage_Snapshot___Domain"
    ),
    "Development/Snapshots/Billed_Usage/Billed_Usage/Billed_Usage_SQ_Snapshot___Domain": (
        "Billing_and_Rates/Billed_Usage/Billed_Usage_SQ_Snapshot___Domain"
    ),
    "Development/Snapshots/Financial_Transaction/Financial_Transaction/"
    "Financial_Transaction_Snapshot___Domain": (
        "Finance/Financial_Transaction/Financial_Transaction_Snapshot___Domain"
    ),
    "Development/Snapshots/Financial_Transaction/General_Ledger/"
    "FT_and_GL_Snapshot___Domain": "Finance/General_Ledger/FT_and_GL_Snapshot___Domain",
    "Development/Snapshots/Meter_Operations/Measurements/Measurement_Snapshot___Domain": (
        "Meter_Operations/Measurements/Measurement_Snapshot___Domain"
    ),
    "Development/Snapshots/Meter_Operations/Scalar_Usage/Usage_Scalar_Snapshot___Domain": (
        "Meter_Operations/Usage/Usage_Scalar_Snapshot___Domain"
    ),
    "Development/Snapshots/Meter_Operations/Usage_Transactions/"
    "Usage_Transactions_Snapshot___Domain": (
        "Meter_Operations/Usage_Transactions/Usage_Transactions_Snapshot___Domain"
    ),
}

DEFAULT_PUBLIC_TEMPLATE_BUNDLE = (
    Path(__file__).resolve().parents[2]
    / "deploy"
    / "jaspersoft_environment_promotion"
    / "bundled"
    / "public_dashboard_template"
)


def find_org_smartcity_root(work_root: str) -> Tuple[str, str]:
    org_root = os.path.join(work_root, *ORGANIZATIONS_ROOT_PARTS)
    if not os.path.isdir(org_root):
        raise ProcessingError(
            "Tenant-root repackage requires resources/organizations/organization_1/organizations/ "
            f"but it is missing under {work_root}"
        )

    for org_name in sorted(os.listdir(org_root)):
        smartcity_path = os.path.join(org_root, org_name, "SmartCity")
        if os.path.isdir(smartcity_path):
            return org_name, smartcity_path

    raise ProcessingError(
        "Tenant-root repackage could not find SmartCity under any organization folder."
    )


def resolve_smartcity_for_repackage(work_root: str) -> Tuple[Optional[str], str, str, bool]:
    """Return org name (if any), source SmartCity path, destination path, and in-place flag."""
    smartcity_dest = os.path.join(work_root, "resources", "SmartCity")
    if os.path.isdir(smartcity_dest):
        return None, smartcity_dest, smartcity_dest, True

    org_name, smartcity_src = find_org_smartcity_root(work_root)
    return org_name, smartcity_src, smartcity_dest, False


def merge_field_operations_into_workstreams(smartcity_root: str) -> None:
    standard_field_ops = os.path.join(
        smartcity_root, "Report", "Standard_Offering", "Field_Operations"
    )
    workstreams_field_ops = os.path.join(
        smartcity_root, "Report", "Workstreams", "Field_Operations"
    )
    if os.path.isdir(standard_field_ops):
        os.makedirs(workstreams_field_ops, exist_ok=True)
        merge_tree(standard_field_ops, workstreams_field_ops)

    standard_offering = os.path.join(smartcity_root, "Report", "Standard_Offering")
    if os.path.isdir(standard_offering):
        shutil.rmtree(standard_offering)


def merge_workstreams_extensions_into_standard_offering(smartcity_root: str) -> None:
    """Preserve Workstreams-only paths still referenced from Standard_Offering artifacts."""
    workstreams_root = os.path.join(smartcity_root, "Report", "Workstreams")
    standard_root = os.path.join(smartcity_root, "Report", "Standard_Offering")
    workstreams_development = os.path.join(workstreams_root, "Development")
    if os.path.isdir(workstreams_development):
        os.makedirs(standard_root, exist_ok=True)
        merge_tree(
            workstreams_development,
            os.path.join(standard_root, "Development"),
        )


def prefer_standard_offering_tree(smartcity_root: str) -> None:
    merge_workstreams_extensions_into_standard_offering(smartcity_root)

    standard_field_ops = os.path.join(
        smartcity_root, "Report", "Standard_Offering", "Field_Operations"
    )
    workstreams_field_ops = os.path.join(
        smartcity_root, "Report", "Workstreams", "Field_Operations"
    )
    if os.path.isdir(workstreams_field_ops):
        os.makedirs(standard_field_ops, exist_ok=True)
        merge_tree(workstreams_field_ops, standard_field_ops)

    workstreams = os.path.join(smartcity_root, "Report", "Workstreams")
    if os.path.isdir(workstreams):
        shutil.rmtree(workstreams)


def move_tree(source: str, destination: str) -> None:
    if not os.path.isdir(source):
        return
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    if os.path.exists(destination):
        shutil.rmtree(destination)
    shutil.move(source, destination)


def merge_tree(source: str, destination: str) -> None:
    if not os.path.isdir(source):
        return
    os.makedirs(destination, exist_ok=True)
    for entry in os.listdir(source):
        src_path = os.path.join(source, entry)
        dest_path = os.path.join(destination, entry)
        if os.path.isdir(src_path):
            merge_tree(src_path, dest_path)
        else:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            if os.path.exists(dest_path):
                os.remove(dest_path)
            shutil.move(src_path, dest_path)


def remove_organizations_tree(work_root: str) -> None:
    organizations_root = os.path.join(work_root, "resources", "organizations")
    if os.path.isdir(organizations_root):
        shutil.rmtree(organizations_root)


def folder_uri_from_dir(smartcity_root: str, directory: str) -> str:
    relative = os.path.relpath(directory, smartcity_root).replace(os.sep, "/")
    if not relative or relative == ".":
        return "/SmartCity"
    return f"/SmartCity/{relative}"


def parent_uri_from_dir(smartcity_root: str, directory: str) -> str:
    parent_dir = os.path.dirname(directory)
    if parent_dir == smartcity_root:
        return "/"
    return folder_uri_from_dir(smartcity_root, parent_dir)


def write_folder_xml(
    path: str,
    parent_uri: str,
    name: str,
    label: str,
    child_folders: Optional[list[str]] = None,
    child_resources: Optional[list[str]] = None,
) -> None:
    children = ""
    if child_folders:
        children += "".join(f"    <folder>{child}</folder>\n" for child in child_folders)
    if child_resources:
        children += "".join(f"    <resource>{child}</resource>\n" for child in child_resources)
    content = f"""<?xml version="1.0" encoding="UTF-8"?>
<folder exportedWithPermissions="false">
    <parent>{parent_uri}</parent>
    <name>{name}</name>
    <label>{label}</label>
    <creationDate>2026-05-20T00:00:00.000Z</creationDate>
    <updateDate>2026-05-20T00:00:00.000Z</updateDate>
{children}</folder>
"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(content)


def regenerate_tenant_folder_metadata(smartcity_root: str) -> None:
    """Rebuild every .folder.xml from on-disk layout so parents match tenant-root URIs."""
    directories: list[str] = []
    for current_root, dirs, files in os.walk(smartcity_root, topdown=False):
        if dirs or any(name.endswith(".xml") for name in files):
            directories.append(current_root)

    for directory in sorted(directories, key=lambda path: path.count(os.sep)):
        child_folders = sorted(
            name
            for name in os.listdir(directory)
            if os.path.isdir(os.path.join(directory, name)) and not name.endswith("_files")
        )
        child_resources = sorted(
            os.path.splitext(name)[0]
            for name in os.listdir(directory)
            if name.endswith(".xml") and name != ".folder.xml"
        )
        folder_name = os.path.basename(directory)
        label = folder_name.replace("___", " - ").replace("_", " ")
        write_folder_xml(
            os.path.join(directory, ".folder.xml"),
            parent_uri_from_dir(smartcity_root, directory),
            folder_name,
            label,
            child_folders=child_folders or None,
            child_resources=child_resources or None,
        )


def rewrite_development_snapshot_domain_uris(root: str, report_root: str = "Standard_Offering") -> int:
    """Point report artifacts at workstream snapshot domains instead of Development/Snapshots copies."""
    replacements: list[tuple[str, str]] = []
    for dev_suffix, workstream_suffix in DEVELOPMENT_SNAPSHOT_TO_WORKSTREAM.items():
        replacements.append(
            (
                f"/SmartCity/Report/Standard_Offering/{dev_suffix}",
                f"/SmartCity/Report/Standard_Offering/{workstream_suffix}",
            )
        )
        replacements.append(
            (
                f"/SmartCity/Report/Workstreams/{dev_suffix}",
                f"/SmartCity/Report/{report_root}/{workstream_suffix}",
            )
        )
        org_dev_prefix = (
            "/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/"
        )
        replacements.append(
            (
                f"{org_dev_prefix}Workstreams/{dev_suffix}",
                f"{org_dev_prefix}{report_root}/{workstream_suffix}",
            )
        )
        replacements.append(
            (
                f"{org_dev_prefix}Standard_Offering/{dev_suffix}",
                f"{org_dev_prefix}{report_root}/{workstream_suffix}",
            )
        )

    changed_files = 0
    for current_root, _dirs, files in os.walk(root):
        for filename in files:
            if not filename.endswith((".xml", ".data", ".jrxml")):
                continue
            path = os.path.join(current_root, filename)
            if filename == "index.xml":
                continue
            content, _encoding = read_text_file(path)
            if content is None or "Development/Snapshots" not in content:
                continue
            updated = content
            for old, new in replacements:
                updated = updated.replace(old, new)
            if updated != content:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(updated)
                changed_files += 1
    return changed_files


def normalize_report_root_uris(root: str, report_root: str) -> None:
    if report_root == "Standard_Offering":
        replacements = {"/SmartCity/Report/Workstreams/": "/SmartCity/Report/Standard_Offering/"}
    else:
        replacements = {"/SmartCity/Report/Standard_Offering/": "/SmartCity/Report/Workstreams/"}

    for current_root, _dirs, files in os.walk(root):
        for filename in files:
            path = os.path.join(current_root, filename)
            if filename == "index.xml":
                continue
            if f"{os.sep}DataSource{os.sep}" in path and filename.endswith(".xml"):
                continue
            content, _encoding = read_text_file(path)
            if content is None:
                continue
            updated = content
            for old, new in replacements.items():
                updated = updated.replace(old, new)
            if updated != content:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(updated)


def rewrite_datasource_for_tenant_root(work_root: str, target_ds: str) -> None:
    datasource_file = os.path.join(work_root, "resources", "DataSource", f"{target_ds}.xml")
    if not os.path.isfile(datasource_file):
        return

    content, _encoding = read_text_file(datasource_file)
    if content is None:
        return

    if "<folder>" in content:
        start = content.index("<folder>")
        end = content.index("</folder>", start) + len("</folder>")
        updated = content[:start] + "<folder>/DataSource</folder>" + content[end:]
    else:
        updated = content

    with open(datasource_file, "w", encoding="utf-8", newline="") as handle:
        handle.write(updated)

    write_folder_xml(
        os.path.join(work_root, "resources", "DataSource", ".folder.xml"),
        "/",
        "DataSource",
        "DataSource",
    )


def validate_tenant_root_package(work_root: str, report_root: str) -> None:
    forbidden_fragments = (
        "/organizations/organization_1/organizations/",
        "/SmartCity/Report/Workstreams/" if report_root == "Standard_Offering" else "",
    )
    for current_root, _dirs, files in os.walk(work_root):
        for filename in files:
            if not filename.endswith((".xml", ".data")):
                continue
            path = os.path.join(current_root, filename)
            content, _encoding = read_text_file(path)
            if content is None:
                continue
            for fragment in forbidden_fragments:
                if fragment and fragment in content:
                    raise ProcessingError(
                        f"Tenant-root package still contains forbidden URI fragment "
                        f"'{fragment}' in {path}"
                    )


def merge_bundled_public_dashboard_template(
    work_root: str,
    bundle_root: Optional[str] = None,
) -> bool:
    """Bundle shared dashboard JRXML template required by Standard Offering dashboards."""
    bundle = Path(bundle_root or DEFAULT_PUBLIC_TEMPLATE_BUNDLE)
    public_src = bundle / "resources" / "public"
    if not public_src.is_dir():
        return False

    public_dest = Path(work_root) / "resources" / "public"
    merge_tree(str(public_src), str(public_dest))
    write_folder_xml(
        str(public_dest / ".folder.xml"),
        "/",
        "public",
        "public",
        child_folders=["templates"],
    )
    write_folder_xml(
        str(public_dest / "templates" / ".folder.xml"),
        "/public",
        "templates",
        "templates",
        child_resources=["actual_size.820.jrxml"],
    )
    return True


def finalize_tenant_import_index(
    root: str,
    tenant_id: str,
    import_folder_uri: str,
    import_datasource_resource_uri: Optional[str] = None,
    import_repository_resources: Optional[list[str]] = None,
    encrypted: Optional[str] = None,
    keyalias: Optional[str] = None,
    *,
    import_into_existing_tenant: bool = False,
) -> None:
    index_path = os.path.join(root, "index.xml")
    if not os.path.isfile(index_path):
        raise ProcessingError(f"Package index.xml is missing: {index_path}")

    tree = ET.parse(index_path)
    export_root = tree.getroot()

    for module in list(export_root.findall("module")):
        export_root.remove(module)

    repository_module = ET.Element("module", {"id": "repositoryResources"})
    if import_datasource_resource_uri:
        resource_element = ET.SubElement(repository_module, "resource")
        resource_element.text = import_datasource_resource_uri
    for resource_uri in import_repository_resources or []:
        resource_element = ET.SubElement(repository_module, "resource")
        resource_element.text = resource_uri
    folder_element = ET.SubElement(repository_module, "folder")
    folder_element.text = import_folder_uri
    export_root.insert(0, repository_module)

    favorites_module = ET.Element("module", {"id": "favorites"})
    export_root.append(favorites_module)

    properties = {child.get("name"): child for child in export_root.findall("property")}
    if "pathProcessorId" not in properties:
        ET.SubElement(export_root, "property", {"name": "pathProcessorId", "value": "zip"})
    else:
        properties["pathProcessorId"].set("value", "zip")

    # When importing from inside an existing tenant (for example Origin_DEMO),
    # rootTenantId must not name that tenant or JRS treats it as an org import
    # into root and fails with import.organization.into.root.not.allowed.
    if import_into_existing_tenant:
        if "rootTenantId" in properties:
            export_root.remove(properties["rootTenantId"])
    else:
        if "rootTenantId" in properties:
            properties["rootTenantId"].set("value", tenant_id)
        else:
            ET.SubElement(export_root, "property", {"name": "rootTenantId", "value": tenant_id})

    if "jsVersion" not in properties:
        ET.SubElement(export_root, "property", {"name": "jsVersion", "value": "8.1.0 PRO"})

    if encrypted and "encrypted" in properties:
        properties["encrypted"].set("value", encrypted)
    if keyalias and "keyalias" in properties:
        properties["keyalias"].set("value", keyalias)

    tree.write(index_path, encoding="utf-8", xml_declaration=True)


def repackage_to_tenant_root(
    work_root: str,
    tenant_id: str,
    import_folder_uri: str,
    target_ds: str,
    *,
    skip_datasource_import: bool = False,
    use_workstreams_report_root: bool = False,
    import_into_existing_tenant: bool = True,
    target_org: str = "Origin_DEV",
) -> None:
    org_name, smartcity_src, smartcity_dest, already_tenant_root = resolve_smartcity_for_repackage(
        work_root
    )
    report_root = "Workstreams" if use_workstreams_report_root else "Standard_Offering"
    if use_workstreams_report_root:
        merge_field_operations_into_workstreams(smartcity_src)
    else:
        prefer_standard_offering_tree(smartcity_src)

    if not already_tenant_root:
        merge_tree(smartcity_src, smartcity_dest)

    if not skip_datasource_import:
        if org_name:
            datasource_src = os.path.join(
                work_root, *ORGANIZATIONS_ROOT_PARTS, org_name, "DataSource"
            )
        else:
            datasource_src = os.path.join(
                work_root, *ORGANIZATIONS_ROOT_PARTS, target_org, "DataSource"
            )
        datasource_dest = os.path.join(work_root, "resources", "DataSource")
        if os.path.isdir(datasource_src):
            merge_tree(datasource_src, datasource_dest)
        rewrite_datasource_for_tenant_root(work_root, target_ds)

    remove_organizations_tree(work_root)
    normalize_report_root_uris(work_root, report_root)
    rewrite_development_snapshot_domain_uris(work_root, report_root)
    regenerate_tenant_folder_metadata(smartcity_dest)
    include_public_template = merge_bundled_public_dashboard_template(work_root)

    encrypted = None
    keyalias = None
    index_path = os.path.join(work_root, "index.xml")
    if os.path.isfile(index_path):
        tree = ET.parse(index_path)
        export_root = tree.getroot()
        for prop in export_root.findall("property"):
            name = prop.get("name")
            if name == "encrypted":
                encrypted = prop.get("value")
            if name == "keyalias":
                keyalias = prop.get("value")

    datasource_uri = None if skip_datasource_import else f"/DataSource/{target_ds}"
    extra_resources = (
        [PUBLIC_DASHBOARD_TEMPLATE_URI] if include_public_template else []
    )
    finalize_tenant_import_index(
        work_root,
        tenant_id,
        import_folder_uri,
        import_datasource_resource_uri=datasource_uri,
        import_repository_resources=extra_resources,
        encrypted=encrypted,
        keyalias=keyalias,
        import_into_existing_tenant=import_into_existing_tenant,
    )
    validate_tenant_root_package(work_root, report_root)
