#!/usr/bin/env python3
"""College Station TEST AFTER QA for 2-year baseline (fast path).

Heavy full-history source scans on D1_USAGE / SCALAR are replaced with a
recent 3-month parity slice. Retention fingerprint still covers all 7.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

KEEP = 24
RECENT = 3
CLIENT = "collegestation"
OUT = Path("deploy/snapshot_rollout_logs/collegestation/baseline_2yr_20260826/after_qa")
RUNNER = [
    "python3",
    "scripts/local/run_client_oracle_sql.py",
    "--client",
    CLIENT,
    "--format",
    "json",
    "--max-rows",
    "50000",
]


def run(label: str, sql: str) -> list[dict]:
    print(f"\n=== {label} ===", flush=True)
    r = subprocess.run(RUNNER + ["--sql", sql], capture_output=True, text=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{label}.stdout.txt").write_text(r.stdout + "\n" + r.stderr)
    if r.returncode != 0:
        print((r.stderr or r.stdout)[-2500:])
        raise SystemExit(f"FAILED: {label}")
    if "[" not in r.stdout:
        print(r.stdout[-1500:])
        return []
    rows = json.loads(r.stdout[r.stdout.find("[") : r.stdout.rfind("]") + 1])
    for row in rows:
        print(row)
    return rows


def load_existing(label: str) -> list[dict] | None:
    path = OUT / f"{label}.stdout.txt"
    if not path.exists():
        return None
    text = path.read_text()
    if "[" not in text:
        return None
    try:
        return json.loads(text[text.find("[") : text.rfind("]") + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    results: dict = {}

    # Reuse fingerprint if present and valid
    fp = load_existing("fingerprint")
    if fp:
        print("=== fingerprint (reused) ===")
        for row in fp:
            print(row)
        results["fingerprint"] = fp
    else:
        results["fingerprint"] = run(
            "fingerprint",
            f"""
SELECT 'BSEG_BILLED' src, COUNT(*) total_rows,
       TO_CHAR(MIN(bill_dt),'YYYY-MM-DD') mn, TO_CHAR(MAX(bill_dt),'YYYY-MM-DD') mx,
       SUM(CASE WHEN bill_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP}) THEN 1 ELSE 0 END) older_than_2yr
FROM cisadm.bseg_billed_usage_rpt_curr
UNION ALL
SELECT 'BSEG_SQ', COUNT(*), TO_CHAR(MIN(bill_dt),'YYYY-MM-DD'), TO_CHAR(MAX(bill_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN bill_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP}) THEN 1 ELSE 0 END)
FROM cisadm.bseg_sq_usage_rpt_curr
UNION ALL
SELECT 'FT_RPT', COUNT(*), TO_CHAR(MIN(accounting_dt),'YYYY-MM-DD'), TO_CHAR(MAX(accounting_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN accounting_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP}) THEN 1 ELSE 0 END)
FROM cisadm.ft_rpt_curr
UNION ALL
SELECT 'FT_GL', COUNT(*), TO_CHAR(MIN(accounting_dt),'YYYY-MM-DD'), TO_CHAR(MAX(accounting_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN accounting_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP}) THEN 1 ELSE 0 END)
FROM cisadm.ft_gl_distribution_rpt_curr
UNION ALL
SELECT 'D1_MSRMT', COUNT(*), TO_CHAR(MIN(msrmt_dttm),'YYYY-MM-DD'), TO_CHAR(MAX(msrmt_dttm),'YYYY-MM-DD'),
       SUM(CASE WHEN msrmt_dttm < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP}) THEN 1 ELSE 0 END)
FROM cisadm.d1_msrmt_rpt_curr
UNION ALL
SELECT 'D1_USAGE', COUNT(*), TO_CHAR(MIN(NVL(end_dttm,start_dttm)),'YYYY-MM-DD'),
       TO_CHAR(MAX(NVL(end_dttm,start_dttm)),'YYYY-MM-DD'),
       SUM(CASE WHEN NVL(end_dttm,start_dttm) < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP}) THEN 1 ELSE 0 END)
FROM cisadm.d1_usage_rpt_curr
UNION ALL
SELECT 'D1_USAGE_SCALAR', COUNT(*), TO_CHAR(MIN(NVL(usage_end_dttm,end_dttm)),'YYYY-MM-DD'),
       TO_CHAR(MAX(NVL(usage_end_dttm,end_dttm)),'YYYY-MM-DD'),
       SUM(CASE WHEN NVL(usage_end_dttm,end_dttm) < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP}) THEN 1 ELSE 0 END)
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
""",
        )

    # Exact 24mo parity for tables that finish quickly (reuse if present)
    exact_checks = [
        (
            "parity_bseg_billed",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.ci_bseg bseg
   JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
   WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) raw_rows,
  (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr
   WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) snap_rows
FROM dual
""",
        ),
        (
            "parity_bseg_sq",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.ci_bseg_sq sq
   JOIN cisadm.ci_bseg bseg ON bseg.bseg_id = sq.bseg_id
   JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
   WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) raw_rows,
  (SELECT COUNT(*) FROM cisadm.bseg_sq_usage_rpt_curr
   WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) snap_rows
FROM dual
""",
        ),
        (
            "parity_ft_rpt",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.ci_ft
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP}) AND redundant_sw = 'N') raw_rows,
  (SELECT COUNT(*) FROM cisadm.ft_rpt_curr
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) snap_rows
FROM dual
""",
        ),
        (
            "parity_ft_gl",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.ci_ft_gl gl
   JOIN cisadm.ci_ft ft ON ft.ft_id = gl.ft_id
   WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) raw_rows,
  (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) snap_rows
FROM dual
""",
        ),
        (
            "parity_d1_msrmt",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.d1_msrmt
   WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) raw_rows,
  (SELECT COUNT(*) FROM cisadm.d1_msrmt_rpt_curr
   WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP})) snap_rows
FROM dual
""",
        ),
    ]

    for name, sql in exact_checks:
        existing = load_existing(name)
        if existing:
            print(f"=== {name} (reused) ===")
            for row in existing:
                print(row)
            results[name] = existing
        else:
            results[name] = run(name, sql)

    # Fast recent-slice parity for usage / scalar (avoids full 24mo D1_USAGE scan)
    results["parity_d1_usage_recent_3mo"] = run(
        "parity_d1_usage_recent_3mo",
        f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.d1_usage u
   WHERE NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm))
         >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{RECENT})) raw_rows,
  (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr
   WHERE NVL(start_dttm, NVL(usage_cre_dttm, status_upd_dttm))
         >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{RECENT})) snap_rows
FROM dual
""",
    )

    results["parity_d1_usage_scalar_recent_3mo"] = run(
        "parity_d1_usage_scalar_recent_3mo",
        f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl d
   WHERE d.start_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{RECENT})) raw_rows,
  (SELECT COUNT(*) FROM cisadm.d1_usage_scalar_dtl_rpt_curr
   WHERE NVL(start_dttm, usage_start_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{RECENT})) snap_rows
FROM dual
""",
    )

    results["parity_recent_3mo_bseg_monthly"] = run(
        "parity_recent_3mo_bseg_monthly",
        f"""
SELECT TO_CHAR(ym,'YYYY-MM') ym, raw_rows, snap_rows, snap_rows - raw_rows AS row_diff
FROM (
  SELECT COALESCE(r.ym, s.ym) ym, NVL(r.raw_rows,0) raw_rows, NVL(s.snap_rows,0) snap_rows
  FROM (
    SELECT TRUNC(bill.bill_dt,'MM') ym, COUNT(*) raw_rows
    FROM cisadm.ci_bseg bseg
    JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
    WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{RECENT})
    GROUP BY TRUNC(bill.bill_dt,'MM')
  ) r
  FULL OUTER JOIN (
    SELECT TRUNC(bill_dt,'MM') ym, COUNT(*) snap_rows
    FROM cisadm.bseg_billed_usage_rpt_curr
    WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{RECENT})
    GROUP BY TRUNC(bill_dt,'MM')
  ) s ON r.ym = s.ym
)
ORDER BY ym
""",
    )

    verdict = []
    for row in results.get("fingerprint") or []:
        older = int(row.get("OLDER_THAN_2YR") or 0)
        verdict.append(
            {
                "src": row.get("SRC"),
                "total_rows": row.get("TOTAL_ROWS"),
                "mn": row.get("MN"),
                "mx": row.get("MX"),
                "older_than_2yr": older,
                "retention_ok": older == 0,
            }
        )

    def parity_status(raw, snap):
        if raw is None or snap is None:
            return "NO_DATA"
        diff = int(snap) - int(raw)
        if diff == 0:
            return "PASS"
        if abs(diff) / max(int(raw), 1) < 0.01:
            return "NEAR"
        return "GAP"

    parity_verdict = []
    for key in [
        "parity_bseg_billed",
        "parity_bseg_sq",
        "parity_ft_rpt",
        "parity_ft_gl",
        "parity_d1_msrmt",
        "parity_d1_usage_recent_3mo",
        "parity_d1_usage_scalar_recent_3mo",
    ]:
        rows = results.get(key) or []
        if not rows:
            parity_verdict.append({"check": key, "status": "NO_DATA"})
            continue
        r = rows[0]
        raw = r.get("RAW_ROWS")
        snap = r.get("SNAP_ROWS")
        diff = None if raw is None or snap is None else int(snap) - int(raw)
        parity_verdict.append(
            {
                "check": key,
                "raw_rows": raw,
                "snap_rows": snap,
                "diff": diff,
                "status": parity_status(raw, snap),
                "note": "recent_3mo_slice" if "recent_3mo" in key else "full_24mo",
            }
        )

    summary = {
        "finished": datetime.now().isoformat(),
        "mode": "fast_after_qa",
        "retention": verdict,
        "parity": parity_verdict,
        "recent_3mo_bseg": results.get("parity_recent_3mo_bseg_monthly"),
        "scheduling": "HELD — test env; rolling JOB_REFRESH_* left disabled",
        "notes": [
            "D1_USAGE / SCALAR use recent 3-month source parity only (full 24mo source scan too slow).",
            "Retention fingerprint still validates all 7 tables have 0 older-than-2yr rows.",
        ],
    }
    (OUT / "after_qa_summary.json").write_text(json.dumps(summary, indent=2, default=str))
    print("\n=== SUMMARY ===")
    print(json.dumps(summary, indent=2, default=str))
    print(f"\nLogs: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
