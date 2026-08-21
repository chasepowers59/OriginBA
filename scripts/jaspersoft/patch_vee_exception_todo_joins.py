#!/usr/bin/env python3
"""
Relax the To Do join subtree in VEE Exception domains to left outer joins.

The shipped VEE Exception domain inner-joins the To Do chain
(CI_TD_DRLKEY -> CI_TD_DRLKEY_TY -> CI_TD_ENTRY -> lookups) onto
D1_INIT_MSRMT_DATA. Clients that do not raise IMD To Do entries lose the entire
exception population as soon as an Ad Hoc view selects any To Do field
(measured on Newark TEST: 475,842 exceptions -> 0 rows).

Operates on a tenant-root Standard Offering export ZIP (or an already extracted
directory) and is idempotent.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

SCHEMA_GLOB = "**/VEE_Exception___Domain_files/schema.data"

# (left alias, right alias) pairs that make up the optional To Do subtree.
TODO_JOIN_PAIRS = {
    ("D1_INIT_MSRMT_DATA", "CI_TD_DRLKEY"),
    ("CI_TD_DRLKEY", "CI_TD_DRLKEY_TY"),
    ("CI_TD_DRLKEY_TY", "CI_TD_ENTRY"),
    ("CI_TD_DRLKEY", "CI_TD_ENTRY"),
    ("CI_TD_ENTRY", "CI_ROLE_L"),
    ("CI_TD_ENTRY", "CI_TD_TYPE_L"),
    ("CI_TD_ENTRY", "CI_LOOKUP_VAL_L_5"),
    ("CI_TD_ENTRY", "CI_LOOKUP_VAL_L_6"),
}

JOIN_TAG = re.compile(r"<join\b[^>]*>")
ATTR = re.compile(r'(\w+)="([^"]*)"')


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Standard Offering export ZIP or extracted directory.")
    parser.add_argument("--output", help="Patched ZIP path (required when --source is a ZIP).")
    parser.add_argument("--dry-run", action="store_true", help="Report changes without writing.")
    return parser.parse_args()


def patch_schema(path: Path, dry_run: bool) -> int:
    text = path.read_text(encoding="utf-8")
    changed = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal changed
        tag = match.group(0)
        attrs = dict(ATTR.findall(tag))
        pair = (attrs.get("left", ""), attrs.get("right", ""))
        if pair not in TODO_JOIN_PAIRS or attrs.get("type") != "inner":
            return tag
        changed += 1
        return tag.replace('type="inner"', 'type="leftOuter"')

    patched = JOIN_TAG.sub(replace, text)
    if changed and not dry_run:
        path.write_text(patched, encoding="utf-8")
    return changed


def patch_tree(root: Path, dry_run: bool) -> int:
    schemas = sorted(root.glob(SCHEMA_GLOB))
    if not schemas:
        print(f"No VEE Exception domain schema found under {root}", file=sys.stderr)
        return -1

    total = 0
    for schema in schemas:
        count = patch_schema(schema, dry_run)
        total += count
        rel = schema.relative_to(root)
        state = "already left outer" if count == 0 else f"{count} joins relaxed"
        print(f"  {rel}: {state}")
    return total


def rezip(root: Path, output: Path) -> None:
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(root.rglob("*")):
            zf.write(item, item.relative_to(root).as_posix())


def main() -> int:
    args = parse_args()
    source = Path(args.source).expanduser().resolve()

    if source.is_dir():
        total = patch_tree(source, args.dry_run)
        return 0 if total >= 0 else 1

    if not source.is_file():
        print(f"Source not found: {source}", file=sys.stderr)
        return 1
    if not args.output:
        print("--output is required when --source is a ZIP", file=sys.stderr)
        return 1

    output = Path(args.output).expanduser().resolve()
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "export"
        with zipfile.ZipFile(source) as zf:
            zf.extractall(root)

        total = patch_tree(root, args.dry_run)
        if total < 0:
            return 1
        print(f"total joins relaxed: {total}")

        if args.dry_run:
            return 0
        staged = Path(tmp) / "patched.zip"
        rezip(root, staged)
        shutil.move(str(staged), output)

    print(f"patched export: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
