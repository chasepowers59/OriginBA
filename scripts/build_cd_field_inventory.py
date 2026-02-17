"""
Build inventory of code-domain fields (_CD / _FLG / _TYPE) used in SQL and JRXML.
Outputs:
  - output/cd_field_inventory.json

Usage:
  python scripts/build_cd_field_inventory.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCAN_DIRS = [ROOT / "sql", ROOT / "reports", ROOT / "pipeline"]
OUTPUT = ROOT / "output" / "cd_field_inventory.json"

TOKEN_RE = re.compile(r"\b([A-Z][A-Z0-9_]*(?:_CD|_FLG|_TYPE_CD|_STATUS_FLG))\b", re.IGNORECASE)

# Canonical lookup mapping for this environment.
LOOKUP_MAP = {
    "COLL_CL_CD": {"source_table": "CISADM.CI_COLL_CL_L", "join": "COLL_CL_CD + LANGUAGE_CD='EN'", "descr_col": "DESCR"},
    "CC_CL_CD": {"source_table": "CISADM.CI_CC_CL_L", "join": "CC_CL_CD + LANGUAGE_CD='EN'", "descr_col": "DESCR"},
    "CC_TYPE_CD": {"source_table": "CISADM.CI_CC_TYPE_L", "join": "CC_CL_CD + CC_TYPE_CD + LANGUAGE_CD='EN'", "descr_col": "DESCR"},
    "ALERT_TYPE_CD": {"source_table": "CISADM.CI_ALERT_TYPE_L", "join": "ALERT_TYPE_CD + LANGUAGE_CD='EN'", "descr_col": "DESCR80"},
    "TENDER_TYPE_CD": {"source_table": "CISADM.CI_TENDER_TYPE_L", "join": "TENDER_TYPE_CD + LANGUAGE_CD='EN'", "descr_col": "DESCR"},
    "BSEG_STAT_FLG": {"source_table": "CISADM.CI_LOOKUP_VAL", "join": "TRIM(FIELD_NAME)='BSEG_STAT_FLG' + TRIM(FIELD_VALUE)=value", "descr_col": "VALUE_NAME"},
    "BILL_STAT_FLG": {"source_table": "CISADM.CI_LOOKUP_VAL", "join": "TRIM(FIELD_NAME)='BILL_STAT_FLG' + TRIM(FIELD_VALUE)=value", "descr_col": "VALUE_NAME"},
    "CONTACT_METH_FLG": {"source_table": "CISADM.CI_LOOKUP_VAL", "join": "TRIM(FIELD_NAME)='CONTACT_METH_FLG' + TRIM(FIELD_VALUE)=value", "descr_col": "VALUE_NAME"},
    "SA_STATUS_FLG": {"source_table": "CISADM.CI_LOOKUP_VAL", "join": "TRIM(FIELD_NAME)='SA_STATUS_FLG' + TRIM(FIELD_VALUE)=value", "descr_col": "VALUE_NAME"},
    "TNDR_STATUS_FLG": {"source_table": "CISADM.CI_LOOKUP_VAL", "join": "TRIM(FIELD_NAME)='TNDR_STATUS_FLG' + TRIM(FIELD_VALUE)=value", "descr_col": "VALUE_NAME"},
}


def _iter_files():
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for p in d.rglob("*"):
            if p.suffix.lower() in {".sql", ".jrxml", ".py"}:
                yield p


def main() -> int:
    inventory: dict[str, dict] = {}
    for path in _iter_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        for m in TOKEN_RE.finditer(text):
            token = m.group(1).upper()
            rec = inventory.setdefault(token, {"files": [], "lookup": LOOKUP_MAP.get(token)})
            rec["files"].append(str(path.relative_to(ROOT)).replace("\\", "/"))

    # Deduplicate/sort.
    for rec in inventory.values():
        rec["files"] = sorted(set(rec["files"]))

    payload = {
        "source_of_truth": [
            "output/workstream_reporting_dictionary.json",
            "Domain Designs.xlsx",
            "output/domain_designs_metadata.json",
        ],
        "fields": dict(sorted(inventory.items(), key=lambda kv: kv[0])),
    }
    OUTPUT.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
