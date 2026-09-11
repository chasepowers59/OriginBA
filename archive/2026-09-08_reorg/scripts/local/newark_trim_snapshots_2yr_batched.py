#!/usr/bin/env python3
"""Newark TEST: purge snapshot rows older than 24 months in yearly batches.

Runs one table at a time (safer for DB load). Commits after each year.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

CLIENT = "newark"
KEEP_MONTHS = 24
OUT = Path("deploy/snapshot_rollout_logs/newark/trim_2yr_20260805")
ENV = {**os.environ, "DB_CALL_TIMEOUT_MS": "3600000"}
RUNNER = [
    "python3",
    "scripts/local/run_client_oracle_sql.py",
    "--client",
    CLIENT,
]


def run(sql: str, label: str, fmt: str = "table") -> list[dict]:
    print(f"=== {label} ===", flush=True)
    r = subprocess.run(
        RUNNER + ["--format", fmt, "--sql", sql],
        capture_output=True,
        text=True,
        env=ENV,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{label}.stdout.txt").write_text(r.stdout + "\n" + r.stderr)
    print((r.stdout or r.stderr)[-500:], flush=True)
    if r.returncode != 0:
        raise SystemExit(f"FAILED: {label}")
    if fmt != "json" or "[" not in r.stdout:
        return []
    return json.loads(r.stdout[r.stdout.find("[") : r.stdout.rfind("]") + 1])


def year_starts(first: date, keep_start: date):
    y = first.year
    while date(y, 1, 1) < keep_start:
        yield date(y, 1, 1)
        y += 1


def purge_expr(name: str, table: str, expr: str, ts: bool) -> None:
    rows = run(
        f"""
SELECT TO_CHAR(MIN({expr}),'YYYY-MM-DD') mn,
       TO_CHAR(ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}),'YYYY-MM-DD') keep_start,
       COUNT(*) purge_est
FROM cisadm.{table}
WHERE {expr} < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS})
""",
        f"purge_plan_{name}",
        fmt="json",
    )
    if not rows or rows[0].get("MN") is None:
        print(f"{name}: nothing to purge", flush=True)
        return
    print(
        f"{name}: purge_est={rows[0].get('PURGE_EST')} from {rows[0]['MN']} to <{rows[0]['KEEP_START']}",
        flush=True,
    )
    first = date.fromisoformat(rows[0]["MN"][:10])
    keep_start = date.fromisoformat(rows[0]["KEEP_START"][:10])
    for start in year_starts(first, keep_start):
        yyyy = start.strftime("%Y")
        end = date(start.year + 1, 1, 1)
        # cap end at keep_start so we never delete keep-window rows
        if end > keep_start:
            end = keep_start
        if ts:
            lo = f"TIMESTAMP '{start.isoformat()} 00:00:00'"
            hi = f"TIMESTAMP '{end.isoformat()} 00:00:00'"
        else:
            lo = f"DATE '{start.isoformat()}'"
            hi = f"DATE '{end.isoformat()}'"
        # DELETE + COMMIT must share one DB connection or the delete rolls back.
        run(
            f"""
DELETE FROM cisadm.{table}
WHERE {expr} >= {lo}
  AND {expr} < {hi};
COMMIT;
""",
            f"purge_{name}_{yyyy}",
        )
    # leftover sweep (should be ~0)
    sweep = run(
        f"""
SELECT COUNT(*) leftover FROM cisadm.{table}
WHERE {expr} < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS})
""",
        f"purge_{name}_leftover_check",
        fmt="json",
    )
    leftover = sweep[0]["LEFTOVER"] if sweep else None
    print(f"{name}: leftover older-than-keep = {leftover}", flush=True)
    if leftover and leftover > 0:
        run(
            f"""
DELETE FROM cisadm.{table}
WHERE {expr} < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS});
COMMIT;
""",
            f"purge_{name}_final_sweep",
        )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    jobs = [
        ("bseg_billed", "bseg_billed_usage_rpt_curr", "bill_dt", False),
        ("bseg_sq", "bseg_sq_usage_rpt_curr", "bill_dt", False),
        ("ft_rpt", "ft_rpt_curr", "accounting_dt", False),
        ("ft_gl", "ft_gl_distribution_rpt_curr", "accounting_dt", False),
        ("d1_msrmt", "d1_msrmt_rpt_curr", "msrmt_dttm", True),
        ("d1_usage", "d1_usage_rpt_curr", "NVL(end_dttm, start_dttm)", True),
        ("d1_usage_scalar", "d1_usage_scalar_dtl_rpt_curr", "NVL(usage_end_dttm, end_dttm)", True),
    ]
    only = sys.argv[1:] if len(sys.argv) > 1 else None
    for name, table, expr, ts in jobs:
        if only and name not in only:
            continue
        print(f"\n######## {name} ########", flush=True)
        purge_expr(name, table, expr, ts)
    print("\nDONE yearly batched purge", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
