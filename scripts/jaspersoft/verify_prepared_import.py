#!/usr/bin/env python3
"""
Inspect a rewritten Jaspersoft import ZIP and verify org roots, datasource
resources, favorites paths, and leftover source identifiers.
"""

from __future__ import annotations

import argparse
import os
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from typing import Iterable, List, Sequence, Tuple


ORG_ROOT_PREFIX = "resources/organizations/organization_1/organizations/"
FAVORITES_ROOT_PREFIX = "favorites/organizations/organization_1/organizations/"
URI_PATTERN = re.compile(r"/organizations/organization_1/organizations/[A-Za-z0-9_./-]+")


@dataclass
class VerificationResult:
    ok: bool
    messages: List[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify a prepared Jaspersoft import ZIP against expected org/datasource values."
    )
    parser.add_argument("--zip", required=True, help="Prepared import ZIP to inspect.")
    parser.add_argument("--target-org", required=True, help="Expected target organization resource ID.")
    parser.add_argument("--target-ds", required=True, help="Expected target datasource resource ID.")
    parser.add_argument("--source-org", help="Optional source org to assert is gone.")
    parser.add_argument("--source-ds", help="Optional source datasource to assert is gone.")
    parser.add_argument(
        "--expect-datasource-overlay",
        action="store_true",
        help="Require the package to contain DataSource/<target_ds>.xml and an index.xml repository resource entry.",
    )
    return parser.parse_args()


def read_text_from_zip(archive: zipfile.ZipFile, name: str) -> str | None:
    try:
        payload = archive.read(name)
    except KeyError:
        return None
    for encoding in ("utf-8", "latin-1"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def collect_names(archive: zipfile.ZipFile) -> List[str]:
    return sorted(archive.namelist())


def collect_repository_uris(text: str) -> List[str]:
    return sorted(set(URI_PATTERN.findall(text)))


def any_name_contains(names: Iterable[str], term: str) -> bool:
    return any(term in name for name in names)


def verify_index_resource(index_text: str, expected_resource: str) -> bool:
    root = ET.fromstring(index_text)
    for module in root.findall("module"):
        if module.get("id") != "repositoryResources":
            continue
        for resource in module.findall("resource"):
            if (resource.text or "").strip() == expected_resource:
                return True
    return False


def verify_zip(
    zip_path: str,
    target_org: str,
    target_ds: str,
    source_org: str | None,
    source_ds: str | None,
    expect_datasource_overlay: bool,
) -> VerificationResult:
    messages: List[str] = []
    ok = True

    with zipfile.ZipFile(zip_path, "r") as archive:
        names = collect_names(archive)
        index_text = read_text_from_zip(archive, "index.xml")
        if index_text is None:
            return VerificationResult(False, ["missing index.xml at ZIP root"])

        org_root = f"{ORG_ROOT_PREFIX}{target_org}/"
        favorites_root = f"{FAVORITES_ROOT_PREFIX}{target_org}/"
        datasource_xml = (
            f"{ORG_ROOT_PREFIX}{target_org}/DataSource/{target_ds}.xml"
        )
        datasource_resource = (
            f"/organizations/organization_1/organizations/{target_org}/DataSource/{target_ds}"
        )

        if any_name_contains(names, org_root):
            messages.append(f"org root present: {org_root}")
        else:
            ok = False
            messages.append(f"missing org root: {org_root}")

        if any_name_contains(names, FAVORITES_ROOT_PREFIX):
            if any_name_contains(names, favorites_root):
                messages.append(f"favorites root present: {favorites_root}")
            else:
                ok = False
                messages.append(f"favorites exist but target org root is missing: {favorites_root}")

        if expect_datasource_overlay:
            if datasource_xml in names:
                messages.append(f"datasource XML present: {datasource_xml}")
            else:
                ok = False
                messages.append(f"missing datasource XML: {datasource_xml}")

            if verify_index_resource(index_text, datasource_resource):
                messages.append(f"index.xml repository resource present: {datasource_resource}")
            else:
                ok = False
                messages.append(f"index.xml missing repository resource: {datasource_resource}")
        else:
            if any("/DataSource/" in name and name.endswith(".xml") for name in names):
                ok = False
                messages.append("unexpected datasource XML found while overlay mode is off")
            else:
                messages.append("datasource resources stripped as expected")

        referenced_uris: List[str] = []
        referenced_target_ds = False
        leftover_hits: List[Tuple[str, str]] = []
        check_terms: Sequence[Tuple[str, str | None]] = (
            ("source org", source_org),
            ("source datasource", source_ds),
        )

        for name in names:
            if name.endswith("/"):
                continue
            text = read_text_from_zip(archive, name)
            if text is None:
                continue

            if target_ds in text:
                referenced_target_ds = True
            referenced_uris.extend(collect_repository_uris(text))

            for label, term in check_terms:
                if term and term in text:
                    leftover_hits.append((label, name))

        if referenced_target_ds:
            messages.append(f"target datasource string found in package contents: {target_ds}")
        else:
            ok = False
            messages.append(f"target datasource string not found in package contents: {target_ds}")

        target_uri_prefix = f"/organizations/organization_1/organizations/{target_org}/"
        uri_sample = sorted(set(referenced_uris))
        if any(uri.startswith(target_uri_prefix) for uri in uri_sample):
            messages.append(f"target repository URIs found: {target_uri_prefix}")
        else:
            ok = False
            messages.append(f"target repository URIs not found: {target_uri_prefix}")

        if source_org and any_name_contains(names, source_org):
            ok = False
            messages.append(f"leftover source org path found in ZIP names: {source_org}")
        if source_ds and any_name_contains(names, source_ds):
            ok = False
            messages.append(f"leftover source datasource path found in ZIP names: {source_ds}")

        if leftover_hits:
            ok = False
            first_label, first_name = leftover_hits[0]
            messages.append(
                f"leftover source identifier found in contents: {first_label} in {first_name}"
            )
        else:
            messages.append("no leftover source identifiers found in readable contents")

    return VerificationResult(ok, messages)


def main() -> int:
    args = parse_args()
    zip_path = os.path.abspath(args.zip)
    if not os.path.isfile(zip_path):
        print(f"ERROR: ZIP not found: {zip_path}")
        return 2

    result = verify_zip(
        zip_path=zip_path,
        target_org=args.target_org,
        target_ds=args.target_ds,
        source_org=args.source_org,
        source_ds=args.source_ds,
        expect_datasource_overlay=args.expect_datasource_overlay,
    )

    print(f"ZIP: {zip_path}")
    print(f"status: {'PASS' if result.ok else 'FAIL'}")
    for message in result.messages:
        print(f"- {message}")

    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
