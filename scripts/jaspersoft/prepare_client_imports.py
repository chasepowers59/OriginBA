#!/usr/bin/env python3
"""
Rewrite a Jaspersoft repository export package for one or more target client
organizations.

The script:
- extracts a source ZIP or copies an extracted source folder
- rewrites source org and datasource references in readable files
- renames file and directory paths containing the source org or datasource
- removes datasource resources by default
- optionally overlays a target datasource export
- validates the rewritten package
- emits one import ZIP per target organization
"""

from __future__ import annotations

import argparse
import csv
import os
import shutil
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from uuid import uuid4


TEXT_ENCODINGS: Sequence[str] = ("utf-8", "latin-1")
ORG_ROOT_PARTS: Sequence[str] = (
    "resources",
    "organizations",
    "organization_1",
    "organizations",
)
FAVORITES_ROOT_PARTS: Sequence[str] = (
    "favorites",
    "organizations",
    "organization_1",
    "organizations",
)


class ProcessingError(Exception):
    """Raised when a target package cannot be produced safely."""


@dataclass
class TargetSummary:
    target_org: str
    target_ds: str
    files_edited: int = 0
    text_replacements: int = 0
    path_renames: int = 0
    datasource_files_removed: int = 0
    datasource_dirs_removed: int = 0
    datasource_files_added: int = 0
    leftover_path_matches: List[str] = field(default_factory=list)
    leftover_content_matches: List[Tuple[str, str]] = field(default_factory=list)
    output_zip: Optional[str] = None
    success: bool = False
    failure_reason: Optional[str] = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare one import ZIP per target Jaspersoft organization."
    )
    source_group = parser.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--source-zip",
        help="Path to the source Jasper export ZIP.",
    )
    source_group.add_argument(
        "--source-extract",
        help="Path to an extracted Jasper export folder.",
    )
    parser.add_argument(
        "--mapping",
        required=True,
        help="CSV file with rows target_org,target_datasource.",
    )
    parser.add_argument(
        "--src-org",
        required=True,
        help="Source organization name in the package.",
    )
    parser.add_argument(
        "--src-ds",
        required=True,
        help="Source datasource name in the package.",
    )
    parser.add_argument(
        "--outdir",
        required=True,
        help="Directory where rewritten import ZIPs should be written.",
    )
    parser.add_argument(
        "--datasource-export-dir",
        help=(
            "Optional directory containing one datasource export ZIP or folder "
            "per target. When provided, the matching target datasource export "
            "is injected into each package."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and report actions without writing output ZIPs.",
    )
    return parser.parse_args()


def read_mapping(path: str) -> List[Tuple[str, str]]:
    entries: List[Tuple[str, str]] = []
    with open(path, "r", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        for row_number, row in enumerate(reader, start=1):
            if not row or all(not cell.strip() for cell in row):
                continue
            target_org = row[0].strip()
            if not target_org:
                raise ProcessingError(
                    f"Mapping row {row_number} is missing a target organization."
                )
            target_ds = row[1].strip() if len(row) > 1 and row[1].strip() else f"{target_org}_DS"
            entries.append((target_org, target_ds))
    if not entries:
        raise ProcessingError("Mapping file does not contain any target rows.")
    return entries


def prepare_source_tree(args: argparse.Namespace, base_temp_dir: str) -> str:
    source_root = base_temp_dir

    if args.source_zip:
        source_zip = os.path.abspath(args.source_zip)
        if not os.path.isfile(source_zip):
            raise ProcessingError(f"Source ZIP is missing: {source_zip}")
        with zipfile.ZipFile(source_zip, "r") as archive:
            archive.extractall(source_root)
        return source_root

    source_extract = os.path.abspath(args.source_extract)
    if not os.path.isdir(source_extract):
        raise ProcessingError(f"Source extract folder is missing: {source_extract}")
    shutil.copytree(source_extract, source_root, dirs_exist_ok=True)
    return source_root


def normalize_identifier(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def discover_datasource_export_identity(root: str) -> Tuple[str, str]:
    for current_root, _dirs, files in os.walk(root):
        if os.path.basename(current_root).lower() != "datasource":
            continue
        for filename in files:
            if not filename.lower().endswith(".xml") or filename == ".folder.xml":
                continue
            datasource_name = os.path.splitext(filename)[0]
            path_parts = current_root.split(os.sep)
            if len(path_parts) < len(ORG_ROOT_PARTS) + 2:
                continue
            if tuple(path_parts[-(len(ORG_ROOT_PARTS) + 2):-2]) != ORG_ROOT_PARTS:
                continue
            org_name = path_parts[-2]
            return org_name, datasource_name

    raise ProcessingError(
        "Datasource export does not contain a recognizable DataSource/<name>.xml resource: "
        f"{root}"
    )


def zip_contains_target_datasource(zip_path: str, target_org: str, target_ds: str) -> bool:
    normalized_target_org = normalize_identifier(target_org)
    normalized_target_ds = normalize_identifier(target_ds)

    with zipfile.ZipFile(zip_path, "r") as archive:
        for name in archive.namelist():
            parts = name.split("/")
            if len(parts) < len(ORG_ROOT_PARTS) + 3:
                continue
            if tuple(parts[-(len(ORG_ROOT_PARTS) + 3):-3]) != ORG_ROOT_PARTS:
                continue
            if parts[-1] == ".folder.xml" or not parts[-1].lower().endswith(".xml"):
                continue
            if parts[-2] != "DataSource":
                continue
            org_name = parts[-3]
            datasource_name = os.path.splitext(parts[-1])[0]
            if (
                normalize_identifier(org_name) == normalized_target_org
                or normalize_identifier(datasource_name) == normalized_target_ds
            ):
                return True
    return False


def find_named_input(base_dir: str, target_org: str, target_ds: str) -> str:
    if not os.path.isdir(base_dir):
        raise ProcessingError(f"Datasource export directory is missing: {base_dir}")

    entries = {entry.lower(): entry for entry in os.listdir(base_dir)}
    candidate_names = [
        target_ds,
        target_org,
        f"{target_ds}.zip",
        f"{target_org}.zip",
    ]
    for candidate in candidate_names:
        match = entries.get(candidate.lower())
        if match:
            return os.path.join(base_dir, match)

    for entry in os.listdir(base_dir):
        candidate_path = os.path.join(base_dir, entry)
        if os.path.isdir(candidate_path):
            try:
                candidate_org, candidate_ds = discover_datasource_export_identity(candidate_path)
            except ProcessingError:
                continue
            if (
                normalize_identifier(candidate_org) == normalize_identifier(target_org)
                or normalize_identifier(candidate_ds) == normalize_identifier(target_ds)
            ):
                return candidate_path
            continue

        if zipfile.is_zipfile(candidate_path) and zip_contains_target_datasource(
            candidate_path, target_org, target_ds
        ):
            return candidate_path

    raise ProcessingError(
        f"No datasource export found for target '{target_org}' / '{target_ds}' in {base_dir}. "
        f"Expected a ZIP or folder named '{target_ds}' or '{target_org}'."
    )


def prepare_overlay_tree(input_path: str, base_temp_dir: str) -> str:
    overlay_root = base_temp_dir
    if os.path.isdir(input_path):
        shutil.copytree(input_path, overlay_root, dirs_exist_ok=True)
        return overlay_root

    if zipfile.is_zipfile(input_path):
        with zipfile.ZipFile(input_path, "r") as archive:
            archive.extractall(overlay_root)
        return overlay_root

    raise ProcessingError(f"Unsupported datasource export input: {input_path}")


def make_workspace_dir(parent: str, prefix: str) -> str:
    os.makedirs(parent, exist_ok=True)
    path = os.path.join(parent, f"{prefix}_{uuid4().hex[:8]}")
    os.makedirs(path, exist_ok=False)
    return path


def read_text_file(path: str) -> Tuple[Optional[str], Optional[str]]:
    for encoding in TEXT_ENCODINGS:
        try:
            with open(path, "r", encoding=encoding) as handle:
                return handle.read(), encoding
        except UnicodeDecodeError:
            continue
        except OSError:
            return None, None
    return None, None


def replace_content_references(root: str, replacements: Dict[str, str]) -> Tuple[int, int]:
    files_edited = 0
    total_replacements = 0

    for current_root, _dirs, files in os.walk(root):
        for filename in files:
            path = os.path.join(current_root, filename)
            content, _encoding = read_text_file(path)
            if content is None:
                continue

            updated = content
            replacement_count = 0
            for old, new in sorted(
                replacements.items(), key=lambda pair: len(pair[0]), reverse=True
            ):
                if old == new:
                    continue
                replacement_count += updated.count(old)
                updated = updated.replace(old, new)

            if replacement_count:
                with open(path, "w", encoding="utf-8", newline="") as handle:
                    handle.write(updated)
                files_edited += 1
                total_replacements += replacement_count

    return files_edited, total_replacements


def rename_paths(root: str, old: str, new: str) -> int:
    if old == new:
        return 0

    rename_count = 0
    for current_root, dirs, files in os.walk(root, topdown=False):
        for filename in files:
            if old not in filename:
                continue
            old_path = os.path.join(current_root, filename)
            new_path = os.path.join(current_root, filename.replace(old, new))
            if os.path.exists(new_path):
                raise ProcessingError(
                    f"Rename collision detected for file: {old_path} -> {new_path}"
                )
            shutil.move(old_path, new_path)
            rename_count += 1

        for dirname in dirs:
            if old not in dirname:
                continue
            old_path = os.path.join(current_root, dirname)
            new_path = os.path.join(current_root, dirname.replace(old, new))
            if os.path.exists(new_path):
                raise ProcessingError(
                    f"Rename collision detected for directory: {old_path} -> {new_path}"
                )
            shutil.move(old_path, new_path)
            rename_count += 1

    return rename_count


def remove_datasource_directories(root: str) -> Tuple[int, int]:
    datasource_dirs: List[str] = []
    for current_root, dirs, _files in os.walk(root):
        for dirname in dirs:
            if dirname.lower() == "datasource":
                datasource_dirs.append(os.path.join(current_root, dirname))

    removed_files = 0
    removed_dirs = 0
    for path in sorted(datasource_dirs, key=lambda value: value.count(os.sep), reverse=True):
        if not os.path.isdir(path):
            continue
        for _walk_root, dirs, files in os.walk(path):
            removed_files += len(files)
            removed_dirs += len(dirs)
        shutil.rmtree(path)
        removed_dirs += 1

    return removed_files, removed_dirs


def datasource_resource_uri(target_org: str, target_ds: str) -> str:
    return f"/organizations/organization_1/organizations/{target_org}/DataSource/{target_ds}"


def merge_repository_resource(index_path: str, resource_uri: str) -> None:
    if not os.path.isfile(index_path):
        raise ProcessingError(f"Package index.xml is missing: {index_path}")

    tree = ET.parse(index_path)
    export_root = tree.getroot()
    repository_module = None
    for module in export_root.findall("module"):
        if module.get("id") == "repositoryResources":
            repository_module = module
            break

    if repository_module is None:
        repository_module = ET.Element("module", {"id": "repositoryResources"})
        export_root.insert(0, repository_module)

    existing_resources = {resource.text for resource in repository_module.findall("resource")}
    if resource_uri not in existing_resources:
        resource_element = ET.Element("resource")
        resource_element.text = resource_uri
        repository_module.append(resource_element)

    tree.write(index_path, encoding="utf-8", xml_declaration=True)


def inject_target_datasource(
    work_root: str,
    overlay_root: str,
    target_org: str,
    target_ds: str,
) -> int:
    source_file = os.path.join(
        overlay_root,
        *ORG_ROOT_PARTS,
        target_org,
        "DataSource",
        f"{target_ds}.xml",
    )
    if not os.path.isfile(source_file):
        raise ProcessingError(
            "Target datasource export does not contain the expected datasource XML: "
            f"{source_file}"
        )

    source_dir = os.path.dirname(source_file)
    dest_dir = os.path.join(work_root, *ORG_ROOT_PARTS, target_org, "DataSource")
    os.makedirs(os.path.dirname(dest_dir), exist_ok=True)
    shutil.copytree(source_dir, dest_dir, dirs_exist_ok=True)

    copied_files = 0
    for _walk_root, _dirs, files in os.walk(source_dir):
        copied_files += len(files)

    merge_repository_resource(
        os.path.join(work_root, "index.xml"),
        datasource_resource_uri(target_org, target_ds),
    )
    return copied_files


def collect_leftover_matches(root: str, terms: Iterable[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
    remaining_terms = [term for term in terms if term]
    found_paths: List[str] = []
    found_contents: List[Tuple[str, str]] = []

    if not remaining_terms:
        return found_paths, found_contents

    for current_root, dirs, files in os.walk(root):
        for name in dirs + files:
            for term in remaining_terms:
                if term in name:
                    found_paths.append(os.path.join(current_root, name))

        for filename in files:
            path = os.path.join(current_root, filename)
            content, _encoding = read_text_file(path)
            if content is None:
                continue
            for term in remaining_terms:
                if term in content:
                    found_contents.append((path, term))

    return found_paths, found_contents


def ensure_required_structure(root: str, source_org: str, target_org: str) -> None:
    org_root = os.path.join(root, *ORG_ROOT_PARTS, target_org)
    if not os.path.isdir(org_root):
        raise ProcessingError(f"Missing rewritten organization root: {org_root}")

    file_count = 0
    for _walk_root, _dirs, files in os.walk(root):
        file_count += len(files)
    if file_count == 0:
        raise ProcessingError("Rewritten package is empty.")

    favorites_root = os.path.join(root, *FAVORITES_ROOT_PARTS)
    if os.path.isdir(favorites_root):
        favorite_org_dirs = [
            name
            for name in os.listdir(favorites_root)
            if os.path.isdir(os.path.join(favorites_root, name))
        ]
        if favorite_org_dirs:
            if target_org not in favorite_org_dirs:
                raise ProcessingError(
                    f"Favorites exist but do not include target organization '{target_org}'."
                )
            if source_org != target_org and source_org in favorite_org_dirs:
                raise ProcessingError(
                    f"Favorites still contain source organization '{source_org}'."
                )


def ensure_datasource_removed(root: str) -> None:
    for current_root, dirs, files in os.walk(root):
        for dirname in dirs:
            if dirname.lower() == "datasource":
                raise ProcessingError(
                    "Datasource directory still present after stripping: "
                    f"{os.path.join(current_root, dirname)}"
                )
        for filename in files:
            path = os.path.join(current_root, filename)
            if f"{os.sep}DataSource{os.sep}" in path and filename.lower().endswith(".xml"):
                raise ProcessingError(f"Datasource XML still present after stripping: {path}")


def ensure_target_datasource_file_present(root: str, target_org: str, target_ds: str) -> None:
    datasource_file = os.path.join(
        root,
        *ORG_ROOT_PARTS,
        target_org,
        "DataSource",
        f"{target_ds}.xml",
    )
    if not os.path.isfile(datasource_file):
        raise ProcessingError(f"Expected target datasource XML is missing: {datasource_file}")


def ensure_index_has_resource(root: str, resource_uri: str) -> None:
    index_path = os.path.join(root, "index.xml")
    if not os.path.isfile(index_path):
        raise ProcessingError(f"Package index.xml is missing: {index_path}")

    tree = ET.parse(index_path)
    export_root = tree.getroot()
    for module in export_root.findall("module"):
        if module.get("id") != "repositoryResources":
            continue
        for resource in module.findall("resource"):
            if resource.text == resource_uri:
                return

    raise ProcessingError(f"Package index.xml is missing repository resource entry: {resource_uri}")


def ensure_target_datasource_present(root: str, target_ds: str) -> None:
    if not target_ds:
        return

    for current_root, _dirs, files in os.walk(root):
        for filename in files:
            path = os.path.join(current_root, filename)
            content, _encoding = read_text_file(path)
            if content is None:
                continue
            if target_ds in content:
                return

    raise ProcessingError(
        f"Target datasource '{target_ds}' was not found in any rewritten file contents."
    )


def zip_directory(root: str, output_zip: str) -> None:
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as archive:
        for current_root, dirs, files in os.walk(root):
            dirs.sort()
            files.sort()
            for filename in files:
                full_path = os.path.join(current_root, filename)
                relative_path = os.path.relpath(full_path, root)
                archive.write(full_path, relative_path)


def summarize_result(summary: TargetSummary) -> None:
    print(f"\n--- {summary.target_org} ({summary.target_ds}) ---")
    print(f"status: {'SUCCESS' if summary.success else 'FAILED'}")
    print(f"files edited: {summary.files_edited}")
    print(f"text replacements: {summary.text_replacements}")
    print(f"path renames: {summary.path_renames}")
    print(f"datasource files removed: {summary.datasource_files_removed}")
    print(f"datasource dirs removed: {summary.datasource_dirs_removed}")
    print(f"datasource files added: {summary.datasource_files_added}")
    print(f"leftover path matches: {len(summary.leftover_path_matches)}")
    print(f"leftover content matches: {len(summary.leftover_content_matches)}")
    if summary.output_zip:
        print(f"output zip: {summary.output_zip}")
    if summary.failure_reason:
        print(f"failure reason: {summary.failure_reason}")


def process_target(
    source_root: str,
    outdir: str,
    source_org: str,
    source_ds: str,
    target_org: str,
    target_ds: str,
    datasource_export_dir: Optional[str],
    dry_run: bool,
) -> TargetSummary:
    summary = TargetSummary(target_org=target_org, target_ds=target_ds)
    work_root = make_workspace_dir(os.path.join(outdir, "_tmp"), f"work_{target_org}")
    overlay_root: Optional[str] = None

    try:
        shutil.copytree(source_root, work_root, dirs_exist_ok=True)

        replacements = {
            source_org: target_org,
            source_ds: target_ds,
        }
        files_edited, text_replacements = replace_content_references(work_root, replacements)
        summary.files_edited = files_edited
        summary.text_replacements = text_replacements

        summary.path_renames += rename_paths(work_root, source_ds, target_ds)
        summary.path_renames += rename_paths(work_root, source_org, target_org)

        removed_files, removed_dirs = remove_datasource_directories(work_root)
        summary.datasource_files_removed = removed_files
        summary.datasource_dirs_removed = removed_dirs

        if datasource_export_dir:
            datasource_input = find_named_input(datasource_export_dir, target_org, target_ds)
            overlay_root = make_workspace_dir(os.path.join(outdir, "_tmp"), f"datasource_{target_org}")
            prepare_overlay_tree(datasource_input, overlay_root)
            overlay_org, overlay_ds = discover_datasource_export_identity(overlay_root)
            replace_content_references(
                overlay_root,
                {
                    overlay_org: target_org,
                    overlay_ds: target_ds,
                },
            )
            rename_paths(overlay_root, overlay_ds, target_ds)
            rename_paths(overlay_root, overlay_org, target_org)
            summary.datasource_files_added = inject_target_datasource(
                work_root,
                overlay_root,
                target_org,
                target_ds,
            )

        ensure_required_structure(work_root, source_org, target_org)
        if datasource_export_dir:
            ensure_target_datasource_file_present(work_root, target_org, target_ds)
            ensure_index_has_resource(work_root, datasource_resource_uri(target_org, target_ds))
        else:
            ensure_datasource_removed(work_root)
        ensure_target_datasource_present(work_root, target_ds)

        validation_terms: List[str] = []
        if source_org != target_org:
            validation_terms.append(source_org)
        if source_ds != target_ds:
            validation_terms.append(source_ds)

        leftover_paths, leftover_contents = collect_leftover_matches(work_root, validation_terms)
        summary.leftover_path_matches = leftover_paths
        summary.leftover_content_matches = leftover_contents
        if leftover_paths or leftover_contents:
            problems: List[str] = []
            if leftover_paths:
                problems.append(
                    f"{len(leftover_paths)} leftover path matches (first: {leftover_paths[0]})"
                )
            if leftover_contents:
                first_path, first_term = leftover_contents[0]
                problems.append(
                    f"{len(leftover_contents)} leftover content matches "
                    f"(first: {first_term} in {first_path})"
                )
            raise ProcessingError("; ".join(problems))

        if not dry_run:
            output_zip = os.path.join(outdir, f"{target_org}_import.zip")
            if os.path.exists(output_zip):
                os.remove(output_zip)
            zip_directory(work_root, output_zip)
            summary.output_zip = output_zip

        summary.success = True
        return summary
    except ProcessingError as exc:
        summary.failure_reason = str(exc)
        return summary
    finally:
        if overlay_root:
            shutil.rmtree(overlay_root, ignore_errors=True)
        shutil.rmtree(work_root, ignore_errors=True)


def main() -> int:
    args = parse_args()
    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)

    try:
        mapping = read_mapping(os.path.abspath(args.mapping))
    except ProcessingError as exc:
        print(f"ERROR: {exc}")
        return 2

    batch_temp_dir = make_workspace_dir(os.path.join(outdir, "_tmp"), "jrs_source")
    summaries: List[TargetSummary] = []

    try:
        try:
            source_root = prepare_source_tree(args, batch_temp_dir)
        except (ProcessingError, zipfile.BadZipFile) as exc:
            print(f"ERROR: {exc}")
            return 2

        print("Will produce packages for:", ", ".join(target_org for target_org, _ in mapping))
        for target_org, target_ds in mapping:
            summary = process_target(
                source_root=source_root,
                outdir=outdir,
                source_org=args.src_org,
                source_ds=args.src_ds,
                target_org=target_org,
                target_ds=target_ds,
                datasource_export_dir=(
                    os.path.abspath(args.datasource_export_dir)
                    if args.datasource_export_dir
                    else None
                ),
                dry_run=args.dry_run,
            )
            summarize_result(summary)
            summaries.append(summary)
    finally:
        shutil.rmtree(batch_temp_dir, ignore_errors=True)

    success_count = sum(1 for summary in summaries if summary.success)
    failure_count = len(summaries) - success_count
    print("\n=== Batch Summary ===")
    print(f"successful targets: {success_count}")
    print(f"failed targets: {failure_count}")
    if not args.dry_run:
        print(f"output directory: {outdir}")

    return 0 if failure_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
