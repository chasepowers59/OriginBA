#!/usr/bin/env python3
"""
Run read-only performance benchmarks for the six updated usage/billing domains.

Outputs per-query:
- row_count
- elapsed_seconds
- completed flag
- warning flag if elapsed > 10s or row_count == 0

Connection source:
- .env: ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN
- optional: ORACLE_CLIENT_LIB_DIR for python-oracledb thick mode
"""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


def load_env(path: Path) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        values[k.strip()] = v.strip()
    return values


@dataclass
class BenchmarkCase:
    key: str
    description: str
    sql: str
    zero_unexpected: bool = True


def build_cases() -> List[BenchmarkCase]:
    usage_base = """
with usage_base as (
    select u.bill_id,
           u.bseg_id,
           u.sa_id,
           u.acct_id,
           u.rs_cd,
           u.uom_cd,
           u.tou_cd,
           u.sqi_cd,
           u.ft_type_flg,
           u.accounting_dt
      from cisadm.c1_bi_billed_usage_vw u
     where u.accounting_dt >= trunc(sysdate) - 30
       and u.accounting_dt < trunc(sysdate) + 1
       and u.bill_id is not null
       and u.bseg_id is not null
       and u.rs_cd is not null
)
"""

    usage_keys_bseg = """
usage_keys as (
    select distinct ub.bseg_id,
           ub.uom_cd,
           ub.tou_cd,
           ub.sqi_cd
      from usage_base ub
     where ub.uom_cd is not null
       and ub.tou_cd is not null
       and ub.sqi_cd is not null
)
"""

    usage_keys_bill = """
usage_keys as (
    select distinct ub.bill_id,
           ub.bseg_id,
           ub.rs_cd
      from usage_base ub
)
"""

    return [
        BenchmarkCase(
            key="usage_billing_fin_bridge_perffast",
            description="Usage Billing Financial Bridge (PerfFast): usage + FT aggregate join",
            sql=f"""
{usage_base},
{usage_keys_bill},
ft_filtered as (
    select f.bill_id,
           f.bseg_id,
           f.rs_cd,
           nvl(f.ft_gl_rev_amt, 0) as ft_gl_rev_amt,
           nvl(f.ft_gl_tax_amt, 0) as ft_gl_tax_amt,
           nvl(f.ft_other_amt, 0) as ft_other_amt,
           nvl(f.tot_amt, 0) as tot_amt,
           nvl(f.ft_cnt, 0) as ft_cnt
      from cisadm.c1_bi_ft_vw f
      join usage_keys uk
        on uk.bill_id = f.bill_id
       and uk.bseg_id = f.bseg_id
       and uk.rs_cd = f.rs_cd
     where f.accounting_dt >= trunc(sysdate) - 30
       and f.accounting_dt < trunc(sysdate) + 1
       and f.bill_id is not null
       and f.bseg_id is not null
       and f.rs_cd is not null
),
ft_agg as (
    select ff.bill_id,
           ff.bseg_id,
           ff.rs_cd,
           sum(ff.ft_gl_rev_amt) as ft_gl_rev_amt_total,
           sum(ff.ft_gl_tax_amt) as ft_gl_tax_amt_total,
           sum(ff.ft_other_amt) as ft_other_amt_total,
           sum(ff.tot_amt) as ft_tot_amt_total,
           sum(ff.ft_cnt) as ft_cnt_total
      from ft_filtered ff
     group by ff.bill_id, ff.bseg_id, ff.rs_cd
)
select count(*)
  from usage_base ub
  left join ft_agg fa
    on fa.bill_id = ub.bill_id
   and fa.bseg_id = ub.bseg_id
   and fa.rs_cd = ub.rs_cd
""",
        ),
        BenchmarkCase(
            key="usage_billing_fin_bridge_ultrasafe",
            description="Usage Billing Financial Bridge (UltraSafe): usage + FT row join",
            sql=f"""
{usage_base},
{usage_keys_bill}
select count(*)
  from usage_base ub
  left join (
      select f.bill_id,
             f.bseg_id,
             f.rs_cd
        from cisadm.c1_bi_ft_vw f
        join usage_keys uk
          on uk.bill_id = f.bill_id
         and uk.bseg_id = f.bseg_id
         and uk.rs_cd = f.rs_cd
       where f.accounting_dt >= trunc(sysdate) - 30
         and f.accounting_dt < trunc(sysdate) + 1
         and f.bill_id is not null
         and f.bseg_id is not null
         and f.rs_cd is not null
  ) ft
    on ft.bill_id = ub.bill_id
   and ft.bseg_id = ub.bseg_id
   and ft.rs_cd = ub.rs_cd
""",
        ),
        BenchmarkCase(
            key="billed_revenue_rate_component",
            description="Billed Revenue by Rate Component: usage + RC component context",
            sql=f"""
{usage_base},
{usage_keys_bseg},
rc_component_ctx as (
    select bcl.bseg_id,
           bcl.uom_cd,
           bcl.tou_cd,
           bcl.sqi_cd
      from cisadm.ci_bseg_calc_ln bcl
      join usage_keys uk
        on uk.bseg_id = bcl.bseg_id
       and uk.uom_cd = bcl.uom_cd
       and uk.tou_cd = bcl.tou_cd
       and uk.sqi_cd = bcl.sqi_cd
      join cisadm.ci_bseg_calc bc
        on bc.bseg_id = bcl.bseg_id
       and bc.header_seq = bcl.header_seq
      left join cisadm.ci_rc rc
        on rc.rs_cd = bc.rs_cd
       and rc.rc_seq = bcl.rc_seq
       and rc.effdt = bc.effdt
)
select count(*)
  from usage_base ub
  join rc_component_ctx rcx
    on rcx.bseg_id = ub.bseg_id
   and rcx.uom_cd = ub.uom_cd
   and rcx.tou_cd = ub.tou_cd
   and rcx.sqi_cd = ub.sqi_cd
""",
        ),
        BenchmarkCase(
            key="billed_revenue_tax_lean",
            description="Billed Revenue Tax Lean: usage + RC component context",
            sql=f"""
{usage_base},
{usage_keys_bseg},
rc_component_ctx as (
    select bcl.bseg_id,
           bcl.uom_cd,
           bcl.tou_cd,
           bcl.sqi_cd
      from cisadm.ci_bseg_calc_ln bcl
      join usage_keys uk
        on uk.bseg_id = bcl.bseg_id
       and uk.uom_cd = bcl.uom_cd
       and uk.tou_cd = bcl.tou_cd
       and uk.sqi_cd = bcl.sqi_cd
      join cisadm.ci_bseg_calc bc
        on bc.bseg_id = bcl.bseg_id
       and bc.header_seq = bcl.header_seq
      left join cisadm.ci_rc rc
        on rc.rs_cd = bc.rs_cd
       and rc.rc_seq = bcl.rc_seq
       and rc.effdt = bc.effdt
)
select count(*)
  from usage_base ub
  join rc_component_ctx rcx
    on rcx.bseg_id = ub.bseg_id
   and rcx.uom_cd = ub.uom_cd
   and rcx.tou_cd = ub.tou_cd
   and rcx.sqi_cd = ub.sqi_cd
""",
        ),
        BenchmarkCase(
            key="billed_usage_consumption_perf6m",
            description="Billed Usage Consumption Amount (Perf): base usage extract",
            sql="""
select count(*)
  from cisadm.c1_bi_billed_usage_vw u
 where u.accounting_dt >= trunc(sysdate) - 30
   and u.accounting_dt < trunc(sysdate) + 1
   and u.bill_id is not null
   and u.bseg_id is not null
   and u.rs_cd is not null
""",
        ),
        BenchmarkCase(
            key="billed_usage_consumption_ultralean",
            description="Billed Usage Consumption Amount (UltraLean): base usage extract",
            sql="""
select count(*)
  from cisadm.c1_bi_billed_usage_vw u
 where u.accounting_dt >= trunc(sysdate) - 30
   and u.accounting_dt < trunc(sysdate) + 1
   and u.bill_id is not null
   and u.bseg_id is not null
   and u.rs_cd is not null
""",
        ),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env-file", default=".env")
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--dsn", default=None)
    args = parser.parse_args()

    env = load_env(Path(args.env_file))
    user = args.user or env.get("ORACLE_USER")
    pwd = args.password or env.get("ORACLE_PASSWORD")
    dsn = args.dsn or env.get("ORACLE_DSN")
    lib_dir = env.get("ORACLE_CLIENT_LIB_DIR")
    if not all([user, pwd, dsn]):
        print("ERROR: Missing ORACLE_USER / ORACLE_PASSWORD / ORACLE_DSN")
        return 2

    import oracledb

    if lib_dir:
        try:
            oracledb.init_oracle_client(lib_dir=lib_dir)
        except Exception:
            # If already initialized or thin mode is acceptable, continue.
            pass

    cases = build_cases()

    try:
        conn = oracledb.connect(user=user, password=pwd, dsn=dsn)
    except Exception as ex:
        print(f"ERROR: DB connect failed: {type(ex).__name__}: {str(ex).splitlines()[0]}")
        return 3

    print("case_key|row_count|elapsed_seconds|completed|flag")
    try:
        for case in cases:
            t0 = time.perf_counter()
            try:
                with conn.cursor() as cur:
                    cur.execute(case.sql)
                    row = cur.fetchone()
                elapsed = time.perf_counter() - t0
                row_count = int(row[0]) if row and row[0] is not None else 0
                flags: List[str] = []
                if elapsed > 10:
                    flags.append("SLOW_GT_10S")
                if case.zero_unexpected and row_count == 0:
                    flags.append("ZERO_ROWS_UNEXPECTED")
                flag = ",".join(flags) if flags else "OK"
                print(f"{case.key}|{row_count}|{elapsed:.3f}|Y|{flag}")
            except Exception as ex:
                elapsed = time.perf_counter() - t0
                print(f"{case.key}|0|{elapsed:.3f}|N|ERROR:{type(ex).__name__}")
    finally:
        conn.close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
