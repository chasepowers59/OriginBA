#!/usr/bin/env python3
"""Standard Offering Write Offs domain: relative payment window, account balance, running arrears.

Applies to `Write_Off_Process_1/Write_Offs___Domain` schema.data (one row per write-off process
from CISADM.C1_BI_WOPROC_VW). Three changes, all additive to the ids views bind to:

1. WO_PAY_AGG is rewritten in place (same id, same seven output columns and types, so the
   eight items and the join on it are untouched). Two defects go:
   - a hard-coded floor, `cre_dttm >= date '2025-09-01'` and `pay_dt >= date '2025-09-01'`:
     every process older than that showed empty payment figures, silently, and the cut-off
     never moved. The window is now each process's OWN start: payments on the process's
     service agreements dated on or after the process create date; "in window" additionally
     stops at the completion date, as before.
   - a join across two id spaces, `ci_pay_tndr.pay_tender_id = ci_pay_seg.pay_id`: a payment
     segment's PAY_ID is a CI_PAY row, not a tender, so event counts, first/last dates and the
     in-window amount never matched. The chain is now segment -> CI_PAY (pay_id) -> CI_PAY_EVENT
     (pay_event_id), the extractor graph's verified edges. Only frozen payments count
     (CI_PAY.PAY_STATUS_FLG = '50', the payment lifecycle's frozen status).
2. WO_ACCT_BAL, new derived table: the whole account's current and payoff balance across all of
   its service agreements, restricted to accounts that have a write-off process. Uses THIS
   repo's balance regime (`FREEZE_SW='Y' AND REDUNDANT_SW='N'`, cisadm-sql skill), NOT the
   FDL domain's `REDUNDANT_SW='Y'`, which selects the transactions already netted to zero.
   Exposed as row items only: an account balance repeated on every one of the account's
   processes is not additive, so it gets no Sum measure.
3. WO_PROC_ARS, new derived table: the arrears recorded on the process's service agreements
   (CI_WO_PROC_SA.ARS_AMT, FDL's "Write Off Arrears Amount"), plus a calculated
   RUNNING_ARS_ROW = that amount minus the frozen payments since the process started, which
   WO_PAY_AGG now provides. FDL's version also added the balance of payment-arrangement
   agreements selected by SA type 'PA' -- a client-configured code, so it is not carried.

Item ids, resourceIds, joins and table refs that existed before are byte-identical after; the
test proves it. Idempotent: patching a patched schema returns it unchanged.

    python3 scripts/jaspersoft/patch_write_offs_domain.py IN.xml OUT.xml
    # then, VPN on:  jrs_debug.py --env test --org Origin_DEV --confirm Origin_DEV domain-apply <uri> --schema OUT.xml
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

MARKER = 'id="WO_ACCT_BAL"'

WO_PAY_AGG_SQL = """select w.uncoll_proc_id,
       count(distinct case when pe.pay_event_id is not null then ps.pay_seg_id end) as pay_segment_count,
       count(distinct pe.pay_event_id) as payment_event_count,
       nvl(sum(case when pe.pay_event_id is not null then nvl(ps.pay_seg_amt, 0) else 0 end), 0) as pay_seg_amt_total,
       nvl(sum(case when pe.pay_event_id is not null and (w.wo_proc_compl_dt is null or pe.pay_dt <= w.wo_proc_compl_dt) then nvl(ps.pay_seg_amt, 0) else 0 end), 0) as pay_seg_amt_in_window,
       min(pe.pay_dt) as first_pay_dt,
       max(pe.pay_dt) as last_pay_dt
from cisadm.c1_bi_woproc_vw w
left join cisadm.ci_wo_proc_sa s on s.wo_proc_id = w.uncoll_proc_id
left join cisadm.ci_pay_seg ps on ps.sa_id = s.sa_id
left join cisadm.ci_pay p on p.pay_id = ps.pay_id and p.pay_status_flg = '50'
left join cisadm.ci_pay_event pe on pe.pay_event_id = p.pay_event_id and pe.pay_dt >= trunc(w.cre_dttm)
group by w.uncoll_proc_id"""

WO_ACCT_BAL_SQL = """select sa.acct_id,
       sum(ft.cur_amt) as cur_bal,
       sum(ft.tot_amt) as payoff_bal
from cisadm.ci_ft ft
join cisadm.ci_sa sa on sa.sa_id = ft.sa_id
where ft.freeze_sw = 'Y'
  and ft.redundant_sw = 'N'
  and sa.acct_id in (select wp.acct_id from cisadm.ci_wo_proc wp)
group by sa.acct_id"""

WO_PROC_ARS_SQL = """select wps.wo_proc_id,
       nvl(sum(wps.ars_amt), 0) as ars_amt
from cisadm.ci_wo_proc_sa wps
group by wps.wo_proc_id"""

NEW_TABLES = {  # id -> (sql, [(field, java type)])
    "WO_ACCT_BAL": (WO_ACCT_BAL_SQL, [("ACCT_ID", "java.lang.String"), ("CUR_BAL", "java.math.BigDecimal"), ("PAYOFF_BAL", "java.math.BigDecimal")]),
    "WO_PROC_ARS": (WO_PROC_ARS_SQL, [("WO_PROC_ID", "java.lang.String"), ("ARS_AMT", "java.math.BigDecimal")]),
}
NEW_JOINS = [
    ('C1_BI_WOPROC_VW.ACCT_ID == WO_ACCT_BAL.ACCT_ID', "WO_ACCT_BAL"),
    ('C1_BI_WOPROC_VW.UNCOLL_PROC_ID == WO_PROC_ARS.WO_PROC_ID', "WO_PROC_ARS"),
]
RUNNING_ARS_EXPR = "WO_PROC_ARS.ARS_AMT - IF(IsNull(WO_PAY_AGG.PAY_SEG_AMT_TOTAL), 0, WO_PAY_AGG.PAY_SEG_AMT_TOTAL)"

ROW_ITEMS = [  # (item id, label, resourceId) appended to SET_AMOUNTS
    ("WO_ARS_AMT_ROW", "Write Off Arrears Amount (Row)", "JoinTree_1.WO_PROC_ARS.ARS_AMT"),
    ("RUNNING_ARS_ROW", "Running Arrears Net Of Payments (Row)", "JoinTree_1.RUNNING_ARS_ROW"),
    ("ACCT_CUR_BAL_ROW", "Account Current Balance (Row)", "JoinTree_1.WO_ACCT_BAL.CUR_BAL"),
    ("ACCT_PAYOFF_BAL_ROW", "Account Payoff Balance (Row)", "JoinTree_1.WO_ACCT_BAL.PAYOFF_BAL"),
]
MEASURE_ITEMS = [  # (item id, label, resourceId) appended to SET_METRICS; per-process values, additive
    ("WO_ARS_AMT_TOTAL", "Write Off Arrears Amount Total", "JoinTree_1.WO_PROC_ARS.ARS_AMT"),
    ("RUNNING_ARS_TOTAL", "Running Arrears Net Of Payments Total", "JoinTree_1.RUNNING_ARS_ROW"),
]


def _datasource_id(schema: str) -> str:
    ids = sorted(set(re.findall(r'<jdbcDataSource id="([^"]+)"', schema)))
    if len(ids) != 1:
        raise SystemExit(f"expected exactly one datasource id, found {ids}")
    return ids[0]


def _replace_once(schema: str, anchor: str, replacement: str, what: str) -> str:
    if schema.count(anchor) != 1:
        raise SystemExit(f"anchor for {what} found {schema.count(anchor)} times, expected 1")
    return schema.replace(anchor, replacement, 1)


def _jdbc_query(qid: str, ds: str, sql: str, fields: list[tuple[str, str]]) -> str:
    flds = "".join(f'        <field id="{f}" type="{t}"></field>\n' for f, t in fields)
    return (f'    <jdbcQuery id="{qid}" datasourceId="{ds}">\n      <fieldList>\n{flds}      </fieldList>\n'
            f"      <query>{escape(sql)}</query>\n    </jdbcQuery>\n")


def patch(schema: str) -> str:
    if MARKER in schema:
        return schema
    ds = _datasource_id(schema)

    # 1. WO_PAY_AGG: the query text only
    m = re.search(r'(<jdbcQuery id="WO_PAY_AGG"[^>]*>.*?<query>)(.*?)(</query>)', schema, re.S)
    if not m:
        raise SystemExit("WO_PAY_AGG jdbcQuery not found: is this the Write Offs domain?")
    schema = schema[: m.start(2)] + escape(WO_PAY_AGG_SQL) + schema[m.end(2):]

    # 2+3. new derived tables, before the join tree
    anchor = f'    <jdbcTable id="JoinTree_1" datasourceId="{ds}"'
    tables = "".join(_jdbc_query(q, ds, sql, fields) for q, (sql, fields) in NEW_TABLES.items())
    schema = _replace_once(schema, anchor, tables + anchor, "join tree")

    # join-tree fields: the new tables' columns, then the calculated running arrears
    jt_fields = "".join(f'        <field id="{q}.{f}" type="{t}"></field>\n'
                        for q, (_, fields) in NEW_TABLES.items() for f, t in fields)
    last_pay = '        <field id="WO_PAY_AGG.LAST_PAY_DT" type="java.sql.Timestamp"></field>\n'
    schema = _replace_once(schema, last_pay, last_pay + jt_fields, "WO_PAY_AGG join-tree fields")
    calc_anchor = '        <field id="PAY_SEG_AMT_IN_WINDOW_ROW" dataSetExpression="WO_PAY_AGG.PAY_SEG_AMT_IN_WINDOW" type="java.math.BigDecimal"></field>\n'
    calc = f'        <field id="RUNNING_ARS_ROW" dataSetExpression="{escape(RUNNING_ARS_EXPR)}" type="java.math.BigDecimal"></field>\n'
    schema = _replace_once(schema, calc_anchor, calc_anchor + calc, "calculated fields")

    # joins and table refs, after WO_PAY_AGG's
    join_anchor = '<join expr="C1_BI_WOPROC_VW.UNCOLL_PROC_ID == WO_PAY_AGG.UNCOLL_PROC_ID" left="C1_BI_WOPROC_VW" right="WO_PAY_AGG" type="leftOuter" weight="1"></join>\n'
    joins = "".join(f'        <join expr="{e}" left="C1_BI_WOPROC_VW" right="{r}" type="leftOuter" weight="1"></join>\n' for e, r in NEW_JOINS)
    schema = _replace_once(schema, join_anchor, join_anchor + joins, "joins")
    ref_anchor = '        <tableRef alwaysIncludeTable="false" tableAlias="WO_PAY_AGG" tableId="WO_PAY_AGG"></tableRef>\n'
    refs = "".join(f'        <tableRef alwaysIncludeTable="false" tableAlias="{q}" tableId="{q}"></tableRef>\n' for q in NEW_TABLES)
    schema = _replace_once(schema, ref_anchor, ref_anchor + refs, "table refs")

    # items: rows into SET_AMOUNTS, measures into SET_METRICS, each appended before the set closes
    def append_items(sch: str, set_id: str, items: list[tuple[str, str, str]], measure: bool) -> str:
        blk = re.search(rf'(<itemGroup id="{set_id}".*?)(\n      </items>\n    </itemGroup>)', sch, re.S)
        if not blk:
            raise SystemExit(f"item group {set_id} not found")
        extra = "".join(
            ('\n        <item defaultAgg="Sum" dimensionOrMeasure="Measure" ' if measure else '\n        <item ')
            + f'id="{i}" label="{l}" resourceId="{r}"></item>' for i, l, r in items)
        return sch[: blk.end(1)] + extra + sch[blk.end(1):]
    schema = append_items(schema, "SET_AMOUNTS", ROW_ITEMS, measure=False)
    schema = append_items(schema, "SET_METRICS", MEASURE_ITEMS, measure=True)
    return schema


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__.split("\n\n")[0]); print("usage: patch_write_offs_domain.py IN.xml OUT.xml"); return 2
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    out = patch(src.read_text(encoding="utf-8"))
    dst.write_text(out, encoding="utf-8")
    print(f"wrote {dst} ({len(out):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
