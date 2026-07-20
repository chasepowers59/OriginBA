#!/usr/bin/env python3
"""Repackage Jaspersoft exports for Origin_DEMO-style tenant-root repository layout."""

from __future__ import annotations

import os
import re
import shutil
import zipfile
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
STANDARD_OFFERING_URI_CORRECTIONS: dict[str, str] = {
    "/SmartCity/Report/Standard_Offering/Cashiering/Payment_Tender/Cashiering_Dashboard": (
        "/SmartCity/Report/Standard_Offering/Cashiering/Payment_Header/Cashiering_Dashboard"
    ),
}

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


RESOURCE_ROOT_TAGS = {
    "adhocDataView",
    "reportUnit",
    "dashboardModelResource",
    "semanticLayerDataSource",
    "contentResource",
    "fileResource",
}


def resource_label(path: str) -> Optional[str]:
    content, _encoding = read_text_file(path)
    if content is None:
        return None
    try:
        root = ET.fromstring(content)
    except ET.ParseError:
        return None
    if root.tag.split("}")[-1] not in RESOURCE_ROOT_TAGS:
        return None
    return (root.findtext("label") or root.findtext("name") or "").strip() or None


def resource_name_from_label(label: str) -> str:
    candidate = label.replace(" - ", "___")
    candidate = re.sub(r"[^\w]+", "_", candidate)
    candidate = re.sub(r"_+", "_", candidate).strip("_")
    return candidate or "Resource"


def copy_resource_tree(source_xml_path: str, dest_xml_path: str) -> None:
    os.makedirs(os.path.dirname(dest_xml_path), exist_ok=True)
    shutil.copy2(source_xml_path, dest_xml_path)
    source_files = source_xml_path[:-4] + "_files"
    dest_files = dest_xml_path[:-4] + "_files"
    if os.path.isdir(source_files):
        if os.path.exists(dest_files):
            shutil.rmtree(dest_files)
        shutil.copytree(source_files, dest_files)


def rename_resource_identity(xml_path: str, old_name: str, new_name: str) -> None:
    """Align copied resource XML and sidecar folders with a unique repository name."""
    if old_name == new_name:
        return
    content, _encoding = read_text_file(xml_path)
    if content is None:
        return
    updated = content.replace(old_name, new_name)
    with open(xml_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(updated)

    sidecar_root = xml_path[:-4] + "_files"
    if os.path.isdir(sidecar_root):
        for current_root, _dirs, files in os.walk(sidecar_root):
            for filename in files:
                path = os.path.join(current_root, filename)
                payload, enc = read_text_file(path)
                if payload is None or old_name not in payload:
                    continue
                rewritten = payload.replace(old_name, new_name)
                with open(path, "w", encoding=enc or "utf-8", newline="") as handle:
                    handle.write(rewritten)


def reconcile_workstreams_resource_collisions(smartcity_root: str) -> dict[str, str]:
    """Preserve Workstreams resources that share a filename with a different Standard_Offering object."""
    uri_remap: dict[str, str] = {}
    workstreams_root = os.path.join(smartcity_root, "Report", "Workstreams")
    standard_root = os.path.join(smartcity_root, "Report", "Standard_Offering")
    if not os.path.isdir(workstreams_root) or not os.path.isdir(standard_root):
        return uri_remap

    for current_root, _dirs, files in os.walk(workstreams_root):
        for filename in files:
            if not filename.endswith(".xml") or filename == ".folder.xml":
                continue
            workstreams_xml = os.path.join(current_root, filename)
            workstreams_label = resource_label(workstreams_xml)
            if not workstreams_label:
                continue
            relative = os.path.relpath(workstreams_xml, workstreams_root)
            standard_xml = os.path.join(standard_root, relative)
            if not os.path.isfile(standard_xml):
                continue
            standard_label = resource_label(standard_xml)
            if not standard_label or standard_label == workstreams_label:
                continue

            relative_dir = os.path.dirname(relative)
            unique_name = resource_name_from_label(workstreams_label)
            if unique_name == os.path.splitext(filename)[0]:
                unique_name = f"{unique_name}__Workstreams"
            dest_xml = os.path.join(standard_root, relative_dir, f"{unique_name}.xml")
            if os.path.exists(dest_xml):
                continue

            old_name = os.path.splitext(filename)[0]
            copy_resource_tree(workstreams_xml, dest_xml)
            rename_resource_identity(dest_xml, old_name, unique_name)
            workstreams_uri = folder_uri_from_dir(
                smartcity_root,
                os.path.join(workstreams_root, relative_dir),
            ) + f"/{os.path.splitext(filename)[0]}"
            standard_uri = folder_uri_from_dir(
                smartcity_root,
                os.path.join(standard_root, relative_dir),
            ) + f"/{unique_name}"
            uri_remap[workstreams_uri] = standard_uri

    return uri_remap


def apply_uri_replacements(root: str, replacements: dict[str, str]) -> int:
    if not replacements:
        return 0
    changed_files = 0
    for current_root, _dirs, files in os.walk(root):
        for filename in files:
            if not filename.endswith((".xml", ".data", ".jrxml", "layout")):
                continue
            path = os.path.join(current_root, filename)
            if filename == "index.xml":
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
                changed_files += 1
    return changed_files


def merge_workstreams_extensions_into_standard_offering(smartcity_root: str) -> None:
    """No-op: Development/Snapshots domains are never promoted into Standard_Offering."""
    return


def prefer_standard_offering_tree(smartcity_root: str) -> dict[str, str]:
    merge_workstreams_extensions_into_standard_offering(smartcity_root)
    uri_remap = reconcile_workstreams_resource_collisions(smartcity_root)

    standard_root = os.path.join(smartcity_root, "Report", "Standard_Offering")
    workstreams = os.path.join(smartcity_root, "Report", "Workstreams")
    if os.path.isdir(workstreams):
        os.makedirs(standard_root, exist_ok=True)
        # Preserve Workstreams-only dependencies after URI normalization rewrites
        # /Workstreams/... references to /Standard_Offering/...
        copy_tree_missing(workstreams, standard_root)

    workstreams = os.path.join(smartcity_root, "Report", "Workstreams")
    if os.path.isdir(workstreams):
        shutil.rmtree(workstreams)
    return uri_remap


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


def copy_tree_missing(source: str, destination: str) -> None:
    """Copy files from source into destination without overwriting existing targets."""
    if not os.path.isdir(source):
        return
    os.makedirs(destination, exist_ok=True)
    for entry in os.listdir(source):
        src_path = os.path.join(source, entry)
        dest_path = os.path.join(destination, entry)
        if os.path.isdir(src_path):
            copy_tree_missing(src_path, dest_path)
        elif not os.path.exists(dest_path):
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(src_path, dest_path)


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


def apply_standard_offering_uri_corrections(root: str) -> int:
    return apply_uri_replacements(root, STANDARD_OFFERING_URI_CORRECTIONS)


def remove_superseded_development_snapshot_tree(work_root: str) -> None:
    """Drop Development/Snapshots copies after URIs point at workstream domains."""
    for report_root in ("Standard_Offering", "Workstreams"):
        development_root = os.path.join(
            work_root,
            "resources",
            "SmartCity",
            "Report",
            report_root,
            "Development",
        )
        if os.path.isdir(development_root):
            shutil.rmtree(development_root)


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


def bundled_public_dashboard_template_files(
    bundle_root: Optional[str] = None,
) -> tuple[Path, Path]:
    bundle = Path(bundle_root or DEFAULT_PUBLIC_TEMPLATE_BUNDLE)
    template_dir = bundle / "resources" / "public" / "templates"
    template_xml = template_dir / "actual_size.820.jrxml.xml"
    template_data = template_dir / "actual_size.820.jrxml.data"
    return template_xml, template_data


def merge_bundled_public_dashboard_template(
    work_root: str,
    bundle_root: Optional[str] = None,
) -> bool:
    """Bundle shared dashboard JRXML template required by Standard Offering dashboards."""
    template_xml, template_data = bundled_public_dashboard_template_files(bundle_root)
    if not template_xml.is_file() or not template_data.is_file():
        raise ProcessingError(
            "Bundled public dashboard template is missing required files: "
            f"{template_xml} and {template_data}. "
            "Restore them under deploy/jaspersoft_environment_promotion/bundled/"
            "public_dashboard_template/ before building tenant-root import ZIPs."
        )

    public_dest = Path(work_root) / "resources" / "public"
    templates_dest = public_dest / "templates"
    templates_dest.mkdir(parents=True, exist_ok=True)
    # Copy from the canonical bundle; merge_tree moves files and would drain the repo store.
    shutil.copy2(template_xml, templates_dest / template_xml.name)
    shutil.copy2(template_data, templates_dest / template_data.name)
    write_folder_xml(
        str(public_dest / ".folder.xml"),
        "/",
        "public",
        "public",
        child_folders=["templates"],
    )
    write_folder_xml(
        str(templates_dest / ".folder.xml"),
        "/public",
        "templates",
        "templates",
        child_resources=["actual_size.820.jrxml"],
    )
    dest_xml = templates_dest / template_xml.name
    dest_data = templates_dest / template_data.name
    if not dest_xml.is_file() or not dest_data.is_file():
        raise ProcessingError(
            "Public dashboard template bundle did not copy into the package: "
            f"{dest_xml} and {dest_data}"
        )
    return True


def read_export_index_metadata(index_path: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
    """Return keyalias, encrypted, and jsVersion from a Jaspersoft export index.xml."""
    if not os.path.isfile(index_path):
        return None, None, None
    tree = ET.parse(index_path)
    export_root = tree.getroot()
    values: dict[str, Optional[str]] = {
        "keyalias": None,
        "encrypted": None,
        "jsVersion": None,
    }
    for prop in export_root.findall("property"):
        name = prop.get("name")
        if name in values:
            values[name] = prop.get("value")
    return values["keyalias"], values["encrypted"], values["jsVersion"]


def ensure_favorites_directory(root: str) -> None:
    favorites_dir = os.path.join(root, "favorites")
    os.makedirs(favorites_dir, exist_ok=True)


def is_tenant_root_export(work_root: str) -> bool:
    return os.path.isdir(os.path.join(work_root, "resources", "SmartCity"))


def patch_source_export_index(
    index_path: str,
    *,
    import_folder_uri: str,
    import_datasource_resource_uri: Optional[str] = None,
    import_repository_resources: Optional[list[str]] = None,
    import_into_existing_tenant: bool = True,
    keyalias: Optional[str] = None,
    encrypted: Optional[str] = None,
) -> None:
    """Patch a server export index.xml in place instead of rebuilding it from scratch."""
    original = read_text_file(index_path)[0]
    if original is None:
        raise ProcessingError(f"Package index.xml is unreadable: {index_path}")

    declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    if original.startswith("<?xml"):
        declaration = original[: original.index(">") + 2]

    root = ET.fromstring(original)
    for prop in list(root.findall("property")):
        name = prop.get("name")
        if name == "rootTenantId" and import_into_existing_tenant:
            root.remove(prop)
        elif name == "keyalias" and keyalias:
            prop.set("value", keyalias)
        elif name == "encrypted" and encrypted:
            prop.set("value", encrypted)

    repo_module = next(
        (module for module in root.findall("module") if module.get("id") == "repositoryResources"),
        None,
    )
    if repo_module is None:
        repo_module = ET.SubElement(root, "module", {"id": "repositoryResources"})

    existing_resources = {(node.text or "").strip() for node in repo_module.findall("resource")}
    resource_uris: list[str] = []
    if import_datasource_resource_uri:
        resource_uris.append(import_datasource_resource_uri)
    resource_uris.extend(import_repository_resources or [])
    insert_at = 0
    for uri in resource_uris:
        if uri in existing_resources:
            continue
        resource_element = ET.Element("resource")
        resource_element.text = uri
        repo_module.insert(insert_at, resource_element)
        insert_at += 1
        existing_resources.add(uri)

    folder_uris = {(node.text or "").strip() for node in repo_module.findall("folder")}
    if import_folder_uri not in folder_uris:
        folder_element = ET.SubElement(repo_module, "folder")
        folder_element.text = import_folder_uri

    if not any(module.get("id") == "favorites" for module in root.findall("module")):
        ET.SubElement(root, "module", {"id": "favorites"})

    with open(index_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(declaration + ET.tostring(root, encoding="unicode"))


def zip_from_source_order(
    source_zip: str,
    work_root: str,
    output_zip: str,
    *,
    source_ds: str,
    target_ds: str,
) -> None:
    """Write a ZIP using the source export entry order to stay JRS-compatible."""
    work_path = os.path.abspath(work_root)
    source_ds_entry = f"resources/DataSource/{source_ds}.xml"
    target_ds_entry = f"resources/DataSource/{target_ds}.xml"
    written: set[str] = set()

    with zipfile.ZipFile(source_zip, "r") as source_archive, zipfile.ZipFile(
        output_zip, "w", zipfile.ZIP_DEFLATED
    ) as output_archive:
        for entry_name in source_archive.namelist():
            if entry_name == "index.xml":
                continue
            if entry_name == source_ds_entry:
                mapped_name = target_ds_entry
                local_path = os.path.join(work_path, mapped_name)
                if os.path.isfile(local_path):
                    output_archive.write(local_path, mapped_name)
                    written.add(mapped_name)
                continue

            local_path = os.path.join(work_path, entry_name)
            if os.path.isfile(local_path):
                output_archive.write(local_path, entry_name)
                written.add(entry_name)
                continue

            if entry_name.endswith("/"):
                directory_path = os.path.join(work_path, entry_name.rstrip("/"))
                if os.path.isdir(directory_path):
                    zip_info = zipfile.ZipInfo(entry_name)
                    zip_info.compress_type = zipfile.ZIP_DEFLATED
                    output_archive.writestr(zip_info, b"")
                    written.add(entry_name)

        extras: list[str] = []
        for current_root, _dirs, files in os.walk(work_path):
            for filename in files:
                full_path = os.path.join(current_root, filename)
                relative_path = os.path.relpath(full_path, work_path).replace(os.sep, "/")
                if relative_path not in written and relative_path != "index.xml":
                    extras.append(relative_path)
        for relative_path in sorted(extras):
            output_archive.write(os.path.join(work_path, relative_path), relative_path)
            written.add(relative_path)

        for dir_entry in ("resources/", "favorites/"):
            if dir_entry in written:
                continue
            directory_path = os.path.join(work_path, dir_entry.rstrip("/"))
            if os.path.isdir(directory_path):
                zip_info = zipfile.ZipInfo(dir_entry)
                zip_info.compress_type = zipfile.ZIP_DEFLATED
                output_archive.writestr(zip_info, b"")
                written.add(dir_entry)

        index_path = os.path.join(work_path, "index.xml")
        if os.path.isfile(index_path):
            output_archive.write(index_path, "index.xml")


def promote_tenant_root_export_light_touch(
    work_root: str,
    import_folder_uri: str,
    target_ds: str,
    *,
    skip_datasource_import: bool = False,
    import_into_existing_tenant: bool = True,
    datasource_export_index_path: Optional[str] = None,
    use_canonical_index_encryption: bool = False,
) -> None:
    """Minimally promote an already tenant-root export without rebuilding folder metadata."""
    if not is_tenant_root_export(work_root):
        raise ProcessingError("Light-touch promotion requires an existing tenant-root SmartCity tree.")

    smartcity_root = os.path.join(work_root, "resources", "SmartCity")
    if os.path.isdir(smartcity_root):
        workstreams_root = os.path.join(smartcity_root, "Report", "Workstreams")
        if os.path.isdir(workstreams_root):
            collision_uri_remap = prefer_standard_offering_tree(smartcity_root)
            if collision_uri_remap:
                normalized_remap = {
                    old.replace("/SmartCity/Report/Workstreams/", "/SmartCity/Report/Standard_Offering/"): new
                    for old, new in collision_uri_remap.items()
                }
                apply_uri_replacements(work_root, normalized_remap)
        normalize_report_root_uris(work_root, "Standard_Offering")
        apply_standard_offering_uri_corrections(work_root)

    if not skip_datasource_import:
        rewrite_datasource_for_tenant_root(work_root, target_ds)

    template_xml = os.path.join(
        work_root, "resources", "public", "templates", "actual_size.820.jrxml.xml"
    )
    include_public_template = os.path.isfile(template_xml)
    if not include_public_template:
        include_public_template = merge_bundled_public_dashboard_template(work_root)

    datasource_uri = None if skip_datasource_import else f"/DataSource/{target_ds}"
    extra_resources = [PUBLIC_DASHBOARD_TEMPLATE_URI] if include_public_template else []
    if use_canonical_index_encryption and datasource_export_index_path:
        ds_keyalias, ds_encrypted, ds_js_version = read_export_index_metadata(
            datasource_export_index_path
        )
        if not ds_keyalias or not ds_encrypted:
            raise ProcessingError(
                "Canonical datasource export index is missing keyalias/encrypted metadata."
            )
        finalize_tenant_import_index(
            work_root,
            tenant_id="",
            import_folder_uri=import_folder_uri,
            import_datasource_resource_uri=datasource_uri,
            import_repository_resources=extra_resources,
            keyalias=ds_keyalias,
            encrypted=ds_encrypted,
            js_version=ds_js_version,
            import_into_existing_tenant=import_into_existing_tenant,
        )
    else:
        finalize_tenant_import_index(
            work_root,
            tenant_id="",
            import_folder_uri=import_folder_uri,
            import_datasource_resource_uri=datasource_uri,
            import_repository_resources=extra_resources,
            import_into_existing_tenant=import_into_existing_tenant,
        )
    ensure_favorites_directory(work_root)


def render_jrs_export_index_xml(
    *,
    keyalias: str,
    encrypted: str,
    js_version: str,
    import_folder_uri: str,
    import_datasource_resource_uri: Optional[str] = None,
    import_repository_resources: Optional[list[str]] = None,
    tenant_id: Optional[str] = None,
    import_into_existing_tenant: bool = False,
) -> str:
    """Render index.xml in the compact format emitted by JasperReports Server exports."""
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>\n',
        "<export>",
        f'<property name="keyalias" value="{keyalias}"/>',
        '<module id="repositoryResources">',
    ]
    if import_datasource_resource_uri:
        parts.append(f"<resource>{import_datasource_resource_uri}</resource>")
    for resource_uri in import_repository_resources or []:
        parts.append(f"<resource>{resource_uri}</resource>")
    parts.append(f"<folder>{import_folder_uri}</folder>")
    parts.extend(
        [
            "</module>",
            '<module id="favorites"/>',
            '<property name="pathProcessorId" value="zip"/>',
        ]
    )
    if tenant_id and not import_into_existing_tenant:
        parts.append(f'<property name="rootTenantId" value="{tenant_id}"/>')
    parts.extend(
        [
            f'<property name="jsVersion" value="{js_version}"/>',
            f'<property name="encrypted" value="{encrypted}"/>',
            "</export>",
        ]
    )
    return "".join(parts)


def finalize_tenant_import_index(
    root: str,
    tenant_id: str,
    import_folder_uri: str,
    import_datasource_resource_uri: Optional[str] = None,
    import_repository_resources: Optional[list[str]] = None,
    encrypted: Optional[str] = None,
    keyalias: Optional[str] = None,
    js_version: Optional[str] = None,
    *,
    import_into_existing_tenant: bool = False,
) -> None:
    index_path = os.path.join(root, "index.xml")
    if not os.path.isfile(index_path):
        raise ProcessingError(f"Package index.xml is missing: {index_path}")

    existing_keyalias, existing_encrypted, existing_js_version = read_export_index_metadata(index_path)
    resolved_keyalias = keyalias or existing_keyalias
    resolved_encrypted = encrypted or existing_encrypted
    resolved_js_version = js_version or existing_js_version or "8.1.0 PRO"
    if not resolved_keyalias or not resolved_encrypted:
        raise ProcessingError(
            "Package index.xml is missing required export metadata (keyalias and encrypted). "
            "Use the canonical datasource export index for the target environment."
        )

    index_xml = render_jrs_export_index_xml(
        keyalias=resolved_keyalias,
        encrypted=resolved_encrypted,
        js_version=resolved_js_version,
        import_folder_uri=import_folder_uri,
        import_datasource_resource_uri=import_datasource_resource_uri,
        import_repository_resources=import_repository_resources,
        tenant_id=tenant_id,
        import_into_existing_tenant=import_into_existing_tenant,
    )
    with open(index_path, "w", encoding="utf-8", newline="") as handle:
        handle.write(index_xml)
    ensure_favorites_directory(root)


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
    datasource_export_index_path: Optional[str] = None,
) -> None:
    org_name, smartcity_src, smartcity_dest, already_tenant_root = resolve_smartcity_for_repackage(
        work_root
    )
    report_root = "Workstreams" if use_workstreams_report_root else "Standard_Offering"
    collision_uri_remap: dict[str, str] = {}
    if use_workstreams_report_root:
        merge_field_operations_into_workstreams(smartcity_src)
    else:
        collision_uri_remap = prefer_standard_offering_tree(smartcity_src)

    if not already_tenant_root:
        merge_tree(smartcity_src, smartcity_dest)

    if collision_uri_remap:
        apply_uri_replacements(work_root, collision_uri_remap)

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
    if collision_uri_remap:
        normalized_remap = {
            old.replace("/SmartCity/Report/Workstreams/", "/SmartCity/Report/Standard_Offering/"): new
            for old, new in collision_uri_remap.items()
        }
        apply_uri_replacements(work_root, normalized_remap)
    apply_standard_offering_uri_corrections(work_root)
    rewrite_development_snapshot_domain_uris(work_root, report_root)
    remove_superseded_development_snapshot_tree(work_root)
    regenerate_tenant_folder_metadata(smartcity_dest)
    include_public_template = merge_bundled_public_dashboard_template(work_root)

    # Preserve the source export's encryption envelope for content packages. Swapping in
    # the canonical datasource index keyalias/encrypted invalidates the catalog seal and
    # JRS rejects the ZIP before import ("not valid JasperReports Server export file").
    keyalias, encrypted, js_version = read_export_index_metadata(os.path.join(work_root, "index.xml"))
    if not keyalias or not encrypted:
        if datasource_export_index_path and os.path.isfile(datasource_export_index_path):
            keyalias, encrypted, js_version = read_export_index_metadata(datasource_export_index_path)

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
        js_version=js_version,
        import_into_existing_tenant=import_into_existing_tenant,
    )
    validate_tenant_root_package(work_root, report_root)
