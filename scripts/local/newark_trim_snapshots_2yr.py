#!/usr/bin/env python3
"""Newark TEST: before/after fingerprint + source parity for 2-year snapshot trim."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

KEEP_MONTHS = 24
CLIENT = "newark"
OUT_DIR = Path("deploy/snapshot_rollout_logs/newark/trim_2yr_20260805")
RUNNER = ["python3", "scripts/local/run_client_oracle_sql.py", "--client", CLIENT, "--format", "json", "--max-rows", "50000"]


def run_sql(sql: str, label: str) -> list[dict]:
    print(f"\n=== {label} ===", flush=True)
    r = subprocess.run(RUNNER + ["--sql", sql], capture_output=True, text=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{label.replace(' ', '_').lower()}.stdout.txt").write_text(r.stdout + "\n" + r.stderr)
    if r.returncode != 0:
        print(r.stderr[-2000:] or r.stdout[-2000:])
        raise SystemExit(f"SQL failed: {label}")
    if "[" not in r.stdout:
        print(r.stdout[-1500:])
        return []
    rows = json.loads(r.stdout[r.stdout.find("[") : r.stdout.rfind("]") + 1])
    for row in rows:
        print(row)
    return rows


def fingerprint_sql() -> str:
    return f"""
SELECT 'BSEG_BILLED' src,
       COUNT(*) total_rows,
       TO_CHAR(MIN(bill_dt),'YYYY-MM-DD') mn,
       TO_CHAR(MAX(bill_dt),'YYYY-MM-DD') mx,
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END) keep_rows,
       SUM(CASE WHEN bill_dt <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END) purge_rows,
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(total_bill_sq,0) ELSE 0 END) keep_m1,
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(total_calc_amt,0) ELSE 0 END) keep_m2
FROM cisadm.bseg_billed_usage_rpt_curr
UNION ALL
SELECT 'BSEG_SQ', COUNT(*), TO_CHAR(MIN(bill_dt),'YYYY-MM-DD'), TO_CHAR(MAX(bill_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN bill_dt <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(total_bill_sq,0) ELSE 0 END),
       NULL
FROM cisadm.bseg_sq_usage_rpt_curr
UNION ALL
SELECT 'FT_RPT', COUNT(*), TO_CHAR(MIN(accounting_dt),'YYYY-MM-DD'), TO_CHAR(MAX(accounting_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN accounting_dt <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(cur_amt,0) ELSE 0 END),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(tot_amt,0) ELSE 0 END)
FROM cisadm.ft_rpt_curr
UNION ALL
SELECT 'FT_GL', COUNT(*), TO_CHAR(MIN(accounting_dt),'YYYY-MM-DD'), TO_CHAR(MAX(accounting_dt),'YYYY-MM-DD'),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN accounting_dt <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(gl_amount,0) ELSE 0 END),
       SUM(CASE WHEN accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(debit_amt,0) ELSE 0 END)
FROM cisadm.ft_gl_distribution_rpt_curr
UNION ALL
SELECT 'D1_USAGE', COUNT(*), TO_CHAR(MIN(start_dttm),'YYYY-MM-DD'), TO_CHAR(MAX(end_dttm),'YYYY-MM-DD'),
       SUM(CASE WHEN NVL(end_dttm, start_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN NVL(end_dttm, start_dttm) <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       NULL, NULL
FROM cisadm.d1_usage_rpt_curr
UNION ALL
SELECT 'D1_USAGE_SCALAR', COUNT(*), TO_CHAR(MIN(start_dttm),'YYYY-MM-DD'), TO_CHAR(MAX(usage_end_dttm),'YYYY-MM-DD'),
       SUM(CASE WHEN NVL(usage_end_dttm, end_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN NVL(usage_end_dttm, end_dttm) <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN NVL(usage_end_dttm, end_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(quantity,0) ELSE 0 END),
       SUM(CASE WHEN NVL(usage_end_dttm, end_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(final_quantity,0) ELSE 0 END)
FROM cisadm.d1_usage_scalar_dtl_rpt_curr
UNION ALL
SELECT 'D1_MSRMT', COUNT(*), TO_CHAR(MIN(msrmt_dttm),'YYYY-MM-DD'), TO_CHAR(MAX(msrmt_dttm),'YYYY-MM-DD'),
       SUM(CASE WHEN msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN msrmt_dttm <  ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN 1 ELSE 0 END),
       SUM(CASE WHEN msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{KEEP_MONTHS}) THEN NVL(msrmt_val,0) ELSE 0 END),
       NULL
FROM cisadm.d1_msrmt_rpt_curr
"""


def source_parity_sqls() -> list[tuple[str, str]]:
    k = KEEP_MONTHS
    return [
        (
            "parity_bseg_billed",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.ci_bseg bseg
   JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
   WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS raw_rows,
  (SELECT COUNT(*) FROM cisadm.bseg_billed_usage_rpt_curr
   WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS snap_rows
FROM dual
""",
        ),
        (
            "parity_bseg_sq_lines",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.ci_bseg_sq sq
   JOIN cisadm.ci_bseg bseg ON bseg.bseg_id = sq.bseg_id
   JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
   WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS raw_rows,
  (SELECT COUNT(*) FROM cisadm.bseg_sq_usage_rpt_curr
   WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS snap_rows
FROM dual
""",
        ),
        (
            "parity_ft_rpt",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.ci_ft
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k}) AND redundant_sw = 'N') AS raw_rows,
  (SELECT COUNT(*) FROM cisadm.ft_rpt_curr
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS snap_rows,
  (SELECT SUM(NVL(cur_amt,0)) FROM cisadm.ci_ft
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k}) AND redundant_sw = 'N') AS raw_cur,
  (SELECT SUM(NVL(cur_amt,0)) FROM cisadm.ft_rpt_curr
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS snap_cur
FROM dual
""",
        ),
        (
            "parity_ft_gl",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.ci_ft_gl gl
   JOIN cisadm.ci_ft ft ON ft.ft_id = gl.ft_id
   WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS raw_rows,
  (SELECT COUNT(*) FROM cisadm.ft_gl_distribution_rpt_curr
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS snap_rows,
  (SELECT SUM(NVL(gl.amount,0)) FROM cisadm.ci_ft_gl gl
   JOIN cisadm.ci_ft ft ON ft.ft_id = gl.ft_id
   WHERE ft.accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS raw_gl,
  (SELECT SUM(NVL(gl_amount,0)) FROM cisadm.ft_gl_distribution_rpt_curr
   WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS snap_gl
FROM dual
""",
        ),
        (
            "parity_d1_msrmt",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.d1_msrmt
   WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS raw_rows,
  (SELECT COUNT(*) FROM cisadm.d1_msrmt_rpt_curr
   WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS snap_rows
FROM dual
""",
        ),
        (
            "parity_d1_usage",
            f"""
SELECT
  (SELECT COUNT(*) FROM cisadm.d1_usage u
   WHERE NVL(u.end_dttm, NVL(u.start_dttm, NVL(u.cre_dttm, u.status_upd_dttm)))
         >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS raw_rows,
  (SELECT COUNT(*) FROM cisadm.d1_usage_rpt_curr
   WHERE NVL(end_dttm, start_dttm) >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})) AS snap_rows
FROM dual
""",
        ),
        (
            "parity_recent_3mo_bseg_monthly",
            f"""
SELECT TO_CHAR(ym,'YYYY-MM') ym, raw_rows, snap_rows, snap_rows - raw_rows AS row_diff
FROM (
  SELECT COALESCE(r.ym, s.ym) ym, NVL(r.raw_rows,0) raw_rows, NVL(s.snap_rows,0) snap_rows
  FROM (
    SELECT TRUNC(bill.bill_dt,'MM') ym, COUNT(*) raw_rows
    FROM cisadm.ci_bseg bseg
    JOIN cisadm.ci_bill bill ON bill.bill_id = bseg.bill_id AND bill.bill_stat_flg = 'C '
    WHERE bill.bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)
    GROUP BY TRUNC(bill.bill_dt,'MM')
  ) r
  FULL OUTER JOIN (
    SELECT TRUNC(bill_dt,'MM') ym, COUNT(*) snap_rows
    FROM cisadm.bseg_billed_usage_rpt_curr
    WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE,'MM'), -3)
    GROUP BY TRUNC(bill_dt,'MM')
  ) s ON r.ym = s.ym
)
ORDER BY ym
""",
        ),
    ]


def purge_sqls() -> list[tuple[str, str]]:
    k = KEEP_MONTHS
    return [
        ("purge_bseg_billed", f"DELETE FROM cisadm.bseg_billed_usage_rpt_curr WHERE bill_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})"),
        ("purge_bseg_sq", f"DELETE FROM cisadm.bseg_sq_usage_rpt_curr WHERE bill_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})"),
        ("purge_ft_rpt", f"DELETE FROM cisadm.ft_rpt_curr WHERE accounting_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})"),
        ("purge_ft_gl", f"DELETE FROM cisadm.ft_gl_distribution_rpt_curr WHERE accounting_dt < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})"),
        ("purge_d1_usage", f"DELETE FROM cisadm.d1_usage_rpt_curr WHERE NVL(end_dttm, start_dttm) < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})"),
        ("purge_d1_usage_scalar", f"DELETE FROM cisadm.d1_usage_scalar_dtl_rpt_curr WHERE NVL(usage_end_dttm, end_dttm) < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})"),
        ("purge_d1_msrmt", f"DELETE FROM cisadm.d1_msrmt_rpt_curr WHERE msrmt_dttm < ADD_MONTHS(TRUNC(SYSDATE,'MM'), -{k})"),
        ("commit", "COMMIT"),
    ]


def stats_sql() -> str:
    tables = [
        "BSEG_BILLED_USAGE_RPT_CURR",
        "BSEG_SQ_USAGE_RPT_CURR",
        "FT_RPT_CURR",
        "FT_GL_DISTRIBUTION_RPT_CURR",
        "D1_USAGE_RPT_CURR",
        "D1_USAGE_SCALAR_DTL_RPT_CURR",
        "D1_MSRMT_RPT_CURR",
    ]
    # gather via anonymous block
    lines = ["BEGIN"]
    for t in tables:
        lines.append(
            f"  DBMS_STATS.GATHER_TABLE_STATS(ownname=>'CISADM', tabname=>'{t}', estimate_percent=>DBMS_STATS.AUTO_SAMPLE_SIZE, method_opt=>'FOR ALL COLUMNS SIZE AUTO', cascade=>TRUE);"
        )
    lines.append("END;")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["before", "purge", "stats", "after", "all"])
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    meta = {"started": datetime.now().isoformat(), "keep_months": KEEP_MONTHS, "phase": args.phase}
    (OUT_DIR / "run_meta.json").write_text(json.dumps(meta, indent=2))

    phases = ["before", "purge", "stats", "after"] if args.phase == "all" else [args.phase]
    results = {}

    for phase in phases:
        if phase in ("before", "after"):
            results[f"{phase}_fingerprint"] = run_sql(fingerprint_sql(), f"{phase}_fingerprint")
            for name, sql in source_parity_sqls():
                results[f"{phase}_{name}"] = run_sql(sql, f"{phase}_{name}")
        elif phase == "purge":
            for name, sql in purge_sqls():
                print(f"\n=== {name} ===", flush=True)
                r = subprocess.run(RUNNER[:-4] + ["--format", "table", "--sql", sql], capture_output=True, text=True)
                (OUT_DIR / f"{name}.stdout.txt").write_text(r.stdout + "\n" + r.stderr)
                print(r.stdout[-1500:] if r.stdout else r.stderr[-1500:])
                if r.returncode != 0:
                    raise SystemExit(f"Purge failed: {name}")
        elif phase == "stats":
            print("\n=== gather stats ===", flush=True)
            r = subprocess.run(RUNNER[:-4] + ["--format", "table", "--sql", stats_sql()], capture_output=True, text=True)
            (OUT_DIR / "gather_stats.stdout.txt").write_text(r.stdout + "\n" + r.stderr)
            print(r.stdout[-1000:] if r.stdout else r.stderr[-1000:])
            if r.returncode != 0:
                raise SystemExit("Stats gather failed")

    (OUT_DIR / f"results_{args.phase}.json").write_text(json.dumps(results, indent=2, default=str))
    print("\nDONE", args.phase)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
