"""
Ensure key JRXML reports include required code-description enrichment fields.

Usage:
  python scripts/check_report_lookup_coverage.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIREMENTS = {
    "reports/collections_prioritization.jrxml": [
        "COLL_CL_DESCR",
        "CI_COLL_CL_L",
    ],
    "reports/customer_contact_letter.jrxml": [
        "CC_TYPE_DESCR",
        "CC_CL_DESCR",
        "CONTACT_METH_DESCR",
        "CI_CC_TYPE_L",
        "CI_CC_CL_L",
    ],
    "reports/billing_master.jrxml": [
        "BILL_STATUS_DESCR",
        "CI_LOOKUP_VAL",
        "BILL_STAT_FLG",
    ],
    "reports/subreports/line_items.jrxml": [
        "BSEG_STAT_LU",
        "BSEG_STAT_FLG",
    ],
}


def _extract_query(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<queryString[^>]*>\s*<!\[CDATA\[(.*?)\]\]>\s*</queryString>", text, re.S)
    if not m:
        return ""
    return m.group(1).upper()


def main() -> int:
    failures = []
    for rel, needles in REQUIREMENTS.items():
        p = ROOT / rel
        if not p.exists():
            failures.append((rel, "file not found"))
            print(f"[FAIL] {rel}: file not found")
            continue
        q = _extract_query(p)
        if not q:
            failures.append((rel, "queryString CDATA not found"))
            print(f"[FAIL] {rel}: queryString CDATA not found")
            continue
        missing = [n for n in needles if n.upper() not in q]
        if missing:
            failures.append((rel, ", ".join(missing)))
            print(f"[FAIL] {rel}: missing lookup tokens: {', '.join(missing)}")
        else:
            print(f"[PASS] {rel}: lookup coverage requirements met.")

    if failures:
        print(f"[FAIL] Report lookup coverage failed for {len(failures)} file(s).")
        return 1
    print("[PASS] Report lookup coverage passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
