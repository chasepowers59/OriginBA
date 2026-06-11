#!/usr/bin/env python3
"""
Validate JRXML reports for Studio/Server 9.x schema ordering and repo conventions.

Usage:
  python3 scripts/validate_jrxml_schema.py
  python3 scripts/validate_jrxml_schema.py reports/field_activity_operational_intelligence.jrxml
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple


ROOT = Path(__file__).resolve().parents[1]
JR_NS = {"jr": "http://jasperreports.sourceforge.net/jasperreports"}
FORBIDDEN_CHART_TAGS = {"seriesColor"}
EXPECTED_MAIN_ORDER = [
    "property",
    "style",
    "template",
    "subDataset",
    "parameter",
    "queryString",
    "field",
    "sortField",
    "variable",
    "filterExpression",
    "group",
    "background",
    "title",
    "pageHeader",
    "columnHeader",
    "detail",
    "columnFooter",
    "pageFooter",
    "summary",
    "noData",
]


def _strip_ns(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _find_jrxml_files(paths: Iterable[Path]) -> List[Path]:
    files: List[Path] = []
    for path in paths:
        if path.is_file() and path.suffix.lower() == ".jrxml":
            files.append(path.resolve())
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.jrxml")))
    return files


def _load_input_control_ids(report_path: Path) -> Tuple[Optional[Path], Set[str]]:
    rel = report_path.relative_to(ROOT)
    if rel.parts[0] != "reports":
        return None, set()
    stem = report_path.stem
    ic_path = ROOT / "server" / "input_controls" / f"{stem}_input_controls.json"
    if not ic_path.exists():
        return ic_path, set()
    payload = json.loads(ic_path.read_text(encoding="utf-8"))
    controls = payload.get("controls") or payload.get("inputControls") or []
    ids = set()
    for control in controls:
        cid = control.get("id") or control.get("name")
        if cid:
            ids.add(str(cid))
    return ic_path, ids


def _validate_element_order(root: ET.Element) -> List[str]:
    issues: List[str] = []
    child_tags = [_strip_ns(child.tag) for child in list(root)]
    if not child_tags:
        return issues

    positions = {tag: idx for idx, tag in enumerate(EXPECTED_MAIN_ORDER)}
    last_pos = -1
    for tag in child_tags:
        if tag not in positions:
            continue
        pos = positions[tag]
        if pos < last_pos:
            issues.append(f"Element order violation: `{tag}` appears out of schema order.")
        last_pos = max(last_pos, pos)

    if "pageFooter" in child_tags and "summary" in child_tags:
        if child_tags.index("pageFooter") > child_tags.index("summary"):
            issues.append("`pageFooter` must appear before `summary`.")

    if "filterExpression" in child_tags and "group" in child_tags:
        if child_tags.index("filterExpression") > child_tags.index("group"):
            issues.append("`filterExpression` must appear before `group`.")

    return issues


def _validate_domain_query(root: ET.Element) -> List[str]:
    issues: List[str] = []
    query = root.find("jr:queryString", JR_NS)
    if query is None:
        return issues
    language = (query.get("language") or "").lower()
    if language != "domain":
        return issues
    cdata = query.text or ""
    if "<queryField" not in cdata and "<queryField " not in cdata:
        issues.append("Domain report has empty or missing `<queryFields>`.")
    return issues


def _validate_forbidden_chart_tags(root: ET.Element) -> List[str]:
    issues: List[str] = []
    for elem in root.iter():
        tag = _strip_ns(elem.tag)
        if tag in FORBIDDEN_CHART_TAGS:
            issues.append(f"Forbidden chart tag `<{tag}>` found.")
    return issues


def _validate_parameters(root: ET.Element, report_path: Path) -> List[str]:
    issues: List[str] = []
    ic_path, control_ids = _load_input_control_ids(report_path)
    if ic_path is None or not ic_path.exists():
        return issues

    skip_names = {"LOGGEDINUSER", "LOGGEDINUSERNAME", "CLIENT_NAME"}
    declared: Set[str] = set()
    for param in root.findall("jr:parameter", JR_NS):
        name = param.get("name") or ""
        if not name:
            continue
        if name.upper() in skip_names:
            continue
        if (param.get("isForPrompting") or "true").lower() == "false":
            continue
        if param.find("jr:defaultValueExpression", JR_NS) is not None:
            continue
        declared.add(name)

    missing_controls = sorted(name for name in declared if name not in control_ids)
    if missing_controls:
        issues.append(
            f"Missing input controls in {ic_path.relative_to(ROOT)}: {', '.join(missing_controls)}"
        )
    return issues


def validate_jrxml(path: Path) -> List[str]:
    issues: List[str] = []
    try:
        tree = ET.parse(path)
    except ET.ParseError as exc:
        return [f"XML parse error: {exc}"]

    root = tree.getroot()
    if _strip_ns(root.tag) != "jasperReport":
        return ["Root element is not jasperReport."]

    issues.extend(_validate_element_order(root))
    issues.extend(_validate_domain_query(root))
    issues.extend(_validate_forbidden_chart_tags(root))
    issues.extend(_validate_parameters(root, path))
    return issues


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "paths",
        nargs="*",
        default=["reports"],
        help="JRXML files or directories to validate (default: reports/)",
    )
    args = parser.parse_args()

    targets = [ROOT / p for p in args.paths]
    files = _find_jrxml_files(targets)
    if not files:
        print("[FAIL] No JRXML files found.")
        return 1

    failures = 0
    for path in files:
        rel = path.relative_to(ROOT)
        issues = validate_jrxml(path)
        if issues:
            failures += 1
            print(f"[FAIL] {rel}")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print(f"[PASS] {rel}")

    if failures:
        print(f"[FAIL] JRXML validation failed for {failures} file(s).")
        return 1
    print("[PASS] JRXML validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
