"""
CI gate for output/config_completeness.json.
Fails build when critical rules exceed thresholds.

Usage:
  python scripts/check_config_completeness_gate.py output/config_completeness.json
"""

import json
import sys
from pathlib import Path


CRITICAL_THRESHOLDS = {
    "contact_letter_missing_template": 0,
    "gl_distributions_without_status": 0,
    "accounts_without_cust_class": 0,
}


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/check_config_completeness_gate.py <config_completeness.json>")
        return 2

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"[FAIL] File not found: {path}")
        return 2

    payload = json.loads(path.read_text(encoding="utf-8"))
    rules = payload.get("rules", {})

    failed = []
    for rule_name, threshold in CRITICAL_THRESHOLDS.items():
        rule = rules.get(rule_name, {})
        applies = bool(rule.get("applies"))
        count = rule.get("count")
        if not applies:
            print(f"[SKIP] {rule_name}: applies=false")
            continue
        if count is None:
            failed.append((rule_name, count, threshold, "count is null"))
            continue
        if int(count) > int(threshold):
            failed.append((rule_name, int(count), int(threshold), "above threshold"))
        else:
            print(f"[PASS] {rule_name}: {count} <= {threshold}")

    if failed:
        print("[FAIL] Critical completeness gate failed:")
        for name, count, threshold, reason in failed:
            print(f"  - {name}: count={count}, threshold={threshold} ({reason})")
        return 1

    print("[PASS] Critical completeness gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
