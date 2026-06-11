# CISADM Schema Reference for SQL Agents

Generated: 2026-06-09 19:53 UTC

Curated reporting schema for Oracle C2M **CISADM** — tables, join trees, and key links used by OriginBA snapshots, domains, and governed SQL. Not the full physical dictionary (3,362 tables discovered); focused on **189 physical fact/dimension tables** plus **19 portal snapshot tables** across 9 workstreams.

## Where the discovery lives

| Artifact | Path | Purpose |
|----------|------|---------|
| Dictionary extract (CSV) | `output/cisadm_dictionary/` | Full read-only Oracle metadata: tables, columns, constraints, indexes, FK map |
| FK / join map (deduped) | `output/cisadm_dictionary/fk_join_map_full.csv` | 400 join rows for workstream physical tables |
| FK summary | `output/cisadm_dictionary/fk_join_map_summary.md` | Join source counts |
| Workstream dictionary | `output/workstream_reporting_dictionary.json` | 73 curated tables with field descriptions |
| Physical catalog | `output/workstream_physical_catalog.json` | Tables per workstream (physical only) |
| Join paths (machine) | `output/workstream_physical_join_paths.json` | Canonical chains + domain-inferred joins |
| AI context bundle | `output/ai_cisadm_context.json` | Merged JSON for agents (tables + joins + stats) |
| Discovery SQL pack | `sql/diagnostics/cisadm_dictionary/` | Scripts to re-extract from Oracle |
| Export runner | `scripts/local/export_cisadm_dictionary_outputs.py` | Re-run discovery for a client |

Regenerate AI context after discovery:
```bash
python3 scripts/local/export_cisadm_dictionary_outputs.py --client demo
python3 scripts/build_workstream_physical_catalog.py
python3 scripts/build_fk_join_map_full.py
python3 scripts/build_ai_cisadm_context.py --client demo
```

---

## SQL agent rules

1. **Pick the driver table** that matches business grain (see canonical chains below).
2. Use **LEFT JOIN** for optional lookups (`*_L`), char tables, and enrichment detail — preserve driving population.
3. Label tables: `LANGUAGE_CD = 'ENG'`.
4. C2M blank codes: `NULLIF(TRIM(col), '')`.
5. Aggregate detail children **before** joining across workstreams (avoid fan-out).
6. Do **not** use custom views (`CMS_*`, `*_VW`, `C1_BI_*`) in governed SQL.
7. Validate row counts after each major join.

### Status filters (common slices)

| Table | Slice | Predicate |
|-------|-------|-----------|
| `CI_SA` | Active service | `SA_STATUS_FLG = '20'` |
| `CI_FT` | Frozen FT | `FREEZE_SW = 'Y'` |
| `CI_FT` | Governed arrears | `FREEZE_SW = 'Y' AND NOT_IN_ARS_SW = 'N' AND FT_TYPE_FLG NOT IN ('PS','PX') AND ARS_DT IS NOT NULL` |
| `C1_USAGE` | Processed usage | `BO_STATUS_CD = 'BD-PROC'` |
| `D1_USAGE` | Sent usage | `BO_STATUS_CD = 'SENT'` |
| `D1_ACTIVITY_TYPE` | Field activities | `ACTIVITY_TYPE_CAT_FLG = 'D1FA'` |

---

## Core join spine (cross-workstream)

Most reporting questions traverse one of these trees:

```
BILLING:     CI_ACCT → CI_SA → CI_BSEG → CI_BILL
             (+ CI_BSEG_SQ, CI_BSEG_READ, CI_BSEG_CALC, CI_BSEG_EXCP as LEFT children)

FINANCE:     CI_ACCT → CI_SA → CI_FT → CI_FT_GL

USAGE:       CI_ACCT → CI_SA → C1_USAGE → D1_USAGE → D1_USAGE_SCALAR_DTL / D1_USAGE_PERIOD_SQ

METER/DEVICE: CI_PREM → CI_SP → D1_INSTALL_EVT → D1_DVC_CFG → D1_DVC → D1_MEASR_COMP
             MEASUREMENT: D1_INIT_MSRMT_DATA → D1_MSRMT → D1_MSRMT_LOG

PAYMENTS:    CI_PAY_EVENT → CI_PAY → CI_ACCT
             (+ CI_PAY_TNDR, CI_PAY_SEG, CI_TNDR_CTL as LEFT children)

CUSTOMER:    CI_ACCT → CI_ACCT_PER → CI_PER → CI_PER_NAME
             CASES: CI_CASE → CI_ACCT / CI_PREM

NEW SERVICE: CI_SA → CI_ACCT, CI_SA_SP → CI_SP → CI_PREM

DEBT:        CI_ACCT → CI_SA → CI_FT (+ CI_COLL_PROC, C1_PA_RQST workflow)

FIELD OPS:   D1_ACTIVITY → D1_ACTIVITY_TYPE (D1FA) → D1_ACTIVITY_REL / D1_ACTIVITY_CHAR

COMMON:      CI_TD_ENTRY (workflow), CI_PREM → CI_SP, CI_BATCH_INST
```

### Core key links (quick reference)

| From | To | Join |
|------|-----|------|
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` |
| `CI_SA` | `CI_BSEG` | `CI_SA.SA_ID = CI_BSEG.SA_ID` |
| `CI_BSEG` | `CI_BILL` | `CI_BSEG.BILL_ID = CI_BILL.BILL_ID` |
| `CI_SA` | `CI_FT` | `CI_SA.SA_ID = CI_FT.SA_ID` |
| `CI_FT` | `CI_FT_GL` | `CI_FT.FT_ID = CI_FT_GL.FT_ID` |
| `CI_SA` | `C1_USAGE` | `CI_SA.SA_ID = C1_USAGE.SA_ID` |
| `C1_USAGE` | `D1_USAGE` | `C1_USAGE.USAGE_ID = D1_USAGE.USG_EXT_ID` |
| `D1_USAGE` | `D1_USAGE_SCALAR_DTL` | `D1_USAGE.D1_USAGE_ID = D1_USAGE_SCALAR_DTL.D1_USAGE_ID` |
| `D1_USAGE` | `D1_USAGE_PERIOD_SQ` | `D1_USAGE.D1_USAGE_ID = D1_USAGE_PERIOD_SQ.D1_USAGE_ID` |
| `CI_SA` | `CI_SA_SP` | `CI_SA.SA_ID = CI_SA_SP.SA_ID` |
| `CI_SA_SP` | `CI_SP` | `CI_SA_SP.SP_ID = CI_SP.SP_ID` |
| `CI_PREM` | `CI_SP` | `CI_SP.PREM_ID = CI_PREM.PREM_ID` |
| `CI_SP` | `D1_INSTALL_EVT` | `D1_INSTALL_EVT.D1_SP_ID = CI_SP.SP_ID (via D1_SP)` |
| `CI_PAY_EVENT` | `CI_PAY` | `CI_PAY_EVENT.PAY_EVENT_ID = CI_PAY.PAY_EVENT_ID` |
| `CI_PAY` | `CI_ACCT` | `CI_PAY.ACCT_ID = CI_ACCT.ACCT_ID` |
| `CI_PAY` | `CI_PAY_TNDR` | `CI_PAY.PAY_ID = CI_PAY_TNDR.PAY_ID` |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID AND CI_ACCT_PER.MAIN_CUST_SW = 'Y'` |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID AND CI_PER_NAME.NAME_TYPE_FLG = 'PRIM'` |
| `CI_CASE` | `CI_ACCT` | `CI_CASE.ACCT_ID = CI_ACCT.ACCT_ID` |
| `CI_ACCT` | `CI_COLL_PROC` | `CI_COLL_PROC.ACCT_ID = CI_ACCT.ACCT_ID` |
| `CI_ACCT` | `C1_PA_RQST` | `C1_PA_RQST.ACCT_ID = CI_ACCT.ACCT_ID` |
| `D1_ACTIVITY` | `D1_ACTIVITY_TYPE` | `D1_ACTIVITY.ACTIVITY_TYPE_CD = D1_ACTIVITY_TYPE.ACTIVITY_TYPE_CD AND D1_ACTIVITY_TYPE.ACTIVITY_TYPE_CAT_FLG = 'D1FA'` |

---

## Snapshot reporting tables (pre-aggregated)

Governed analytics portal and Jaspersoft domains read these **snapshot** tables (`CISADM.<table>`) instead of live multi-table joins. Prefer snapshots for agent SQL unless the question requires raw CISADM detail.

| Snapshot ID | CISADM table | Workstream | Grain | Date filter field |
|-------------|--------------|------------|-------|-------------------|
| `FT_RPT_CURR` | `FT_RPT_CURR` | finance | FT_ID | `ACCOUNTING_DT` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `FT_GL_DISTRIBUTION_RPT_CURR` | finance | FT_ID + GL_SEQ_NBR | `ACCOUNTING_DT` |
| `BILLABLE_CHARGE_RPT_CURR` | `BILLABLE_CHARGE_RPT_CURR` | finance | BILLABLE_CHG_ID + LINE_SEQ | `CHARGE_START_DT` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `BSEG_BILLED_USAGE_RPT_CURR` | billing | BSEG_ID | `BILL_DT` |
| `BSEG_SQ_USAGE_RPT_CURR` | `BSEG_SQ_USAGE_RPT_CURR` | billing | BSEG_ID + UOM + TOU + SQI | `BILL_DT` |
| `D1_MSRMT_RPT_CURR` | `D1_MSRMT_RPT_CURR` | meter_ops | Final measurement | `MSRMT_DTTM` |
| `D1_USAGE_RPT_CURR` | `D1_USAGE_RPT_CURR` | meter_ops | D1_USAGE_ID | `START_DTTM` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `D1_USAGE_SCALAR_DTL_RPT_CURR` | meter_ops | D1_USAGE_ID + SEQ_NUM | `START_DTTM` |
| `DEVICE_SP_RPT_CURR` | `DEVICE_SP_RPT_CURR` | meter_ops | D1_DVC_ID | `DVC_STATUS_UPD_DTTM` |
| `PAY_EVENT_RPT_CURR` | `PAY_EVENT_RPT_CURR` | cashiering | PAY_ID | `PAY_DT` |
| `SA_AGED_BAL_RPT_CURR` | `SA_AGED_BAL_RPT_CURR` | debt | SA_ID | `NEWEST_ARS_DT` |
| `WO_PROC_RPT_CURR` | `WO_PROC_RPT_CURR` | debt | WO_PROC_ID | `WO_PROC_CRE_DTTM` |
| `ACCT_CUSTOMER_RPT_CURR` | `ACCT_CUSTOMER_RPT_CURR` | customer_ops | ACCT_ID | `SETUP_DT` |
| `CASE_PREM_CONTACT_RPT_CURR` | `CASE_PREM_CONTACT_RPT_CURR` | customer_ops | CASE_ID | `CASE_CRE_DTTM` |
| `NEW_SERVICE_PIPELINE_RPT_CURR` | `NEW_SERVICE_PIPELINE_RPT_CURR` | new_services | SA_ID | `START_DT` |
| `FIELD_ACTIVITY_RPT_CURR` | `FIELD_ACTIVITY_RPT_CURR` | field_ops | D1_ACTIVITY_ID | `ACT_CRE_DTTM` |
| `CREW_OPS_RPT_CURR` | `CREW_OPS_RPT_CURR` | field_ops | CREW_ID | `STATUS_UPD_DTTM` |
| `OPS_EXCEPTION_RPT_CURR` | `OPS_EXCEPTION_RPT_CURR` | common | EXCP_SOURCE + EXCP_NATURAL_KEY | `EXCP_CRE_DTTM` |
| `WORKFLOW_QUEUE_RPT_CURR` | `WORKFLOW_QUEUE_RPT_CURR` | common | QUEUE_SOURCE + QUEUE_NATURAL_KEY | `TD_CRE_DTTM` |

Catalog source: `output/snapshot_explorer_catalog.json`

---

## Billing and Rates (`billing`)

### Canonical join chains

**billing_fact_chain** — driver: `CI_BSEG`, grain: bill_segment
```
CI_ACCT → CI_SA → CI_BSEG → CI_BILL
```
- `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID`
- `CI_SA.SA_ID = CI_BSEG.SA_ID`
- `CI_BSEG.BILL_ID = CI_BILL.BILL_ID`

**billing_detail_enrichment** — driver: `CI_BSEG`, grain: bill_segment (enrichment)
```
CI_BSEG_SQ → CI_BSEG_READ → CI_BSEG_CALC → CI_BSEG_CALC_LN → CI_BSEG_ITEM → CI_BSEG_EXCP
```
- `CI_BSEG.BSEG_ID = <child>.BSEG_ID`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `CI_ACCT` | Account | `FULL` | 1049 |
| `CI_ACCT_PER` |  | — | 1045 |
| `CI_BILL` | Bill Header | `BILL_ID`, `BILL_CYC_CD`, `WIN_START_DT`, `ACCT_ID`, `BILL_STAT_FLG`, `BILL_DT` | 41157 |
| `CI_BSEG` | Bill Segment | `BILL_CYC_CD`, `BILL_ID`, `BILL_SCNR_ID`, `BSEG_DATA_AREA`, `BSEG_ID`, `BSEG_STAT_FLG` | 168608 |
| `CI_BSEG_CALC` | Auto-added coverage table for CI_BSEG_CALC | `BSEG_ID`, `HEADER_SEQ`, `START_DT`, `CURRENCY_CD`, `END_DT`, `RS_CD` | 167526 |
| `CI_BSEG_CALC_LN` | Auto-added coverage table for CI_BSEG_CALC_LN | `BSEG_ID`, `HEADER_SEQ`, `SEQNO`, `CHAR_TYPE_CD`, `CURRENCY_CD`, `CHAR_VAL` | 80140 |
| `CI_BSEG_EXCP` | Auto-added coverage table for CI_BSEG_EXCP | `BSEG_ID`, `MESSAGE_CAT_NBR`, `MESSAGE_NBR`, `BSEG_EXCP_FLG`, `EXP_MSG`, `MESSAGE_PARM1` | 1629 |
| `CI_BSEG_ITEM` | Auto-added coverage table for CI_BSEG_ITEM | `BSEG_ID`, `SEQNO`, `ITEM_TYPE_CD`, `ITEM_ID`, `START_DT`, `END_DT` | 0 |
| `CI_BSEG_READ` | Auto-added coverage table for CI_BSEG_READ | `BSEG_ID`, `SP_ID`, `REG_CONST`, `SEQNO`, `USAGE_FLG`, `USE_PCT` | 113087 |
| `CI_BSEG_SQ` | Auto-added coverage table for CI_BSEG_SQ | `BSEG_ID`, `UOM_CD`, `TOU_CD`, `SQI_CD`, `INIT_SQ`, `BILL_SQ` | 191922 |
| `CI_PER_NAME` |  | `JUST`, `FLATTEN` | 925 |
| `CI_SA` | SA (Service Agreement) | `ACCT_ID`, `ALLOW_EST_SW`, `BUS_ACTIVITY_DESC`, `CHAR_PREM_ID`, `CIAC_REVIEW_DT`, `CIS_DIVISION` | 6643 |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`CI_ACCT_MGMT_GR_L`, `CI_BILL_CAN_RSN_L`, `CI_BILL_CYC_L`, `CI_BUD_PLAN_L`, `CI_COLL_CL_L`, `CI_CUST_CL_L`, `CI_LOOKUP_VAL_L`, `CI_RS_L`, `CI_SQI_L`, `CI_TOU_L`, `CI_UOM_L`, `SC_USER`

### Snapshot tables in this workstream

`BSEG_BILLED_USAGE_RPT_CURR`, `BSEG_SQ_USAGE_RPT_CURR`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `CI_ACCT` | `CI_ACCT_ALERT` | `CI_ACCT.ACCT_ID = CI_ACCT_ALERT.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_MGMT_GR_L` | `CI_ACCT.ACCT_MGMT_GRP_CD = CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACC_GRP_L` | `CI_ACCT.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L_1` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BUD_PLAN_L` | `CI_ACCT.BUD_PLAN_CD = CI_BUD_PLAN_L.BUD_PLAN_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CIS_DIVISION_L` | `CI_ACCT.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_ACCT` | `CI_COLL_CL_L` | `CI_ACCT.COLL_CL_CD = CI_COLL_CL_L.COLL_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CUST_CL_L` | `CI_ACCT.CUST_CL_CD = CI_CUST_CL_L.CUST_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `SC_USER` | `CI_ACCT.BILL_PRT_INTERCEPT = SC_USER.USER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `C1_PER_CONTDET` | `CI_ACCT_PER.PER_ID = C1_PER_CONTDET.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER` | `CI_ACCT_PER.PER_ID = CI_PER.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_BILL` | `CI_ACCT` | `CI_BILL.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_BILL` | `CI_BILL_CYC_L` | `CI_BILL.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_BILL` | `CI_BSEG` | `CI_BILL.BILL_ID = CI_BSEG.BILL_ID` | domain_join_inventory |
| `CI_BILL` | `CI_LOOKUP_VAL_L` | `CI_BILL.BILL_STAT_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_BILL` | `CI_LOOKUP_VAL_L_1` | `CI_BILL.DOC_TYPE_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_BILL` | `SC_USER` | `CI_BILL.APAY_STOP_USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL` | `CI_BSEG.BILL_ID = CI_BILL.BILL_ID` | canonical_chain:billing |
| `CI_BSEG` | `CI_BILL_CAN_RSN_L` | `CI_BSEG.CAN_RSN_CD = CI_BILL_CAN_RSN_L.CAN_RSN_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL_CYC_L_1` | `CI_BSEG.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL_CYC_L_2` | `CI_BSEG.BILL_CYC_CD = CI_BILL_CYC_L_2.BILL_CYC_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_CALC` | `CI_BSEG.BSEG_ID = CI_BSEG_CALC.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_READ` | `CI_BSEG.BSEG_ID = CI_BSEG_READ.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_SQ` | `CI_BSEG.BSEG_ID = CI_BSEG_SQ.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_LOOKUP_VAL_L_2` | `CI_BSEG.BSEG_STAT_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_LOOKUP_VAL_L_3` | `CI_BSEG.BSEG_STAT_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_SA` | `CI_BSEG.SA_ID = CI_SA.SA_ID` | domain_join_inventory |
| `CI_BSEG` | `FT_GL_SUMMARY` | `CI_BSEG.BSEG_ID = FT_GL_SUMMARY.SIBLING_ID` | domain_join_inventory |
| `CI_BSEG_CALC` | `CI_RS_L` | `CI_BSEG_CALC.RS_CD = CI_RS_L.RS_CD` | domain_join_inventory |
| `CI_BSEG_EXCP` | `CI_BSEG` | `CI_BSEG_EXCP.BSEG_ID = CI_BSEG.BSEG_ID` | domain_join_inventory |
| `CI_BSEG_EXCP` | `CI_LOOKUP_VAL_L` | `CI_BSEG_EXCP.BSEG_EXCP_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG_EXCP` | `CI_TD_DRLKEY` | `CI_BSEG_EXCP.BSEG_ID = CI_TD_DRLKEY.KEY_VALUE` | domain_join_inventory |
| `CI_BSEG_EXCP` | `SC_USER` | `CI_BSEG_EXCP.USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_BSEG_EXCP` | `SC_USER_1` | `CI_BSEG_EXCP.REVIEW_USER_ID = SC_USER_1.USER_ID` | domain_join_inventory |
| `CI_BSEG_READ` | `CI_LOOKUP_VAL_L_3` | `CI_BSEG_READ.USAGE_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG_READ` | `CI_LOOKUP_VAL_L_4` | `CI_BSEG_READ.HOW_TO_USE_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG_READ` | `CI_SQI_L` | `CI_BSEG_READ.SQI_CD = CI_SQI_L.SQI_CD` | domain_join_inventory |
| `CI_BSEG_READ` | `CI_SQI_L_1` | `CI_BSEG_READ.FINAL_SQI_CD = CI_SQI_L_1.SQI_CD` | domain_join_inventory |
| `CI_BSEG_READ` | `CI_TOU_L` | `CI_BSEG_READ.TOU_CD = CI_TOU_L.TOU_CD` | domain_join_inventory |
| `CI_BSEG_READ` | `CI_TOU_L_1` | `CI_BSEG_READ.FINAL_TOU_CD = CI_TOU_L_1.TOU_CD` | domain_join_inventory |
| `CI_BSEG_READ` | `CI_UOM_L` | `CI_BSEG_READ.UOM_CD = CI_UOM_L.UOM_CD` | domain_join_inventory |
| `CI_BSEG_READ` | `CI_UOM_L_1` | `CI_BSEG_READ.FINAL_UOM_CD = CI_UOM_L_1.UOM_CD` | domain_join_inventory |
| `CI_BSEG_SQ` | `CI_SQI_L_2` | `CI_BSEG_SQ.SQI_CD = CI_SQI_L_2.SQI_CD` | domain_join_inventory |
| `CI_BSEG_SQ` | `CI_TOU_L_2` | `CI_BSEG_SQ.TOU_CD = CI_TOU_L_2.TOU_CD` | domain_join_inventory |
| `CI_BSEG_SQ` | `CI_UOM_L_2` | `CI_BSEG_SQ.UOM_CD = CI_UOM_L_2.UOM_CD` | domain_join_inventory |
| `CI_SA` | `C1_USAGE` | `CI_SA.SA_ID = C1_USAGE.SA_ID` | canonical_chain:meter_ops |
| `CI_SA` | `CI_ACCT` | `CI_SA.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_ACCT_PER` | `CI_SA.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_BILL_CHG` | `CI_SA.SA_ID = CI_BILL_CHG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_BSEG` | `CI_SA.SA_ID = CI_BSEG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_CIS_DIVISION_L` | `CI_SA.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_FT` | `CI_SA.SA_ID = CI_FT.SA_ID` | canonical_chain:debt_mgmt |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.PROP_SA_STAT_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_1` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_2` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |

*(16 additional joins — see `fk_join_map_full.csv`)*

---

## Cashiering (`cashiering`)

### Canonical join chains

**payment_event_chain** — driver: `CI_PAY_EVENT`, grain: payment_event (enrichment)
```
CI_ACCT → CI_PAY → CI_PAY_EVENT → CI_PAY_TNDR → CI_PAY_SEG → CI_DEP_CTL
```
- `CI_PAY_EVENT.PAY_EVENT_ID = CI_PAY.PAY_EVENT_ID`
- `CI_PAY.ACCT_ID = CI_ACCT.ACCT_ID`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `CI_ACCT` | Account | `FULL` | 1049 |
| `CI_ACCT_PER` |  | — | 1045 |
| `CI_DEP_CTL` | Deposit Control | — | 631 |
| `CI_PAY` |  | — | 39685 |
| `CI_PAY_EVENT` | Payment Event | — | 39684 |
| `CI_PAY_SEG` | Auto-added coverage table for CI_PAY_SEG | `PAY_SEG_ID`, `CURRENCY_CD`, `PAY_ID`, `SA_ID`, `PAY_SEG_AMT`, `VERSION` | 154389 |
| `CI_PAY_TNDR` |  | — | 39734 |
| `CI_PER_NAME` |  | `JUST`, `FLATTEN` | 925 |
| `CI_PP` |  | — | 1313 |
| `CI_PP_SCHED_PAY` |  | — | 1789 |
| `CI_TNDR_CTL` |  | — | 1326 |
| `CI_TNDR_DEP` |  | — | 141 |
| `CI_TNDR_END_BAL` |  | — | 1896 |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`CI_BANK_ACCOUNT_L`, `CI_BANK_L`, `CI_BATCH_CTRL_L`, `CI_LOOKUP_VAL_L`, `CI_MATCH_TYPE_L`, `CI_PAY_CAN_RSN_L`, `CI_PAY_METH_L`, `CI_PP_TYPE_L`, `CI_TENDER_TYPE_L`, `CI_THRD_PTY_L`, `CI_TNDR_SRCE_L`, `SC_USER`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `CI_ACCT` | `CI_ACCT_ALERT` | `CI_ACCT.ACCT_ID = CI_ACCT_ALERT.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_MGMT_GR_L` | `CI_ACCT.ACCT_MGMT_GRP_CD = CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACC_GRP_L` | `CI_ACCT.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L_1` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BUD_PLAN_L` | `CI_ACCT.BUD_PLAN_CD = CI_BUD_PLAN_L.BUD_PLAN_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CIS_DIVISION_L` | `CI_ACCT.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_ACCT` | `CI_COLL_CL_L` | `CI_ACCT.COLL_CL_CD = CI_COLL_CL_L.COLL_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CUST_CL_L` | `CI_ACCT.CUST_CL_CD = CI_CUST_CL_L.CUST_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `SC_USER` | `CI_ACCT.BILL_PRT_INTERCEPT = SC_USER.USER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `C1_PER_CONTDET` | `CI_ACCT_PER.PER_ID = C1_PER_CONTDET.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER` | `CI_ACCT_PER.PER_ID = CI_PER.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_DEP_CTL` | `CI_LOOKUP_VAL_L_1` | `CI_DEP_CTL.TNDR_SRCE_TYPE_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_DEP_CTL` | `CI_LOOKUP_VAL_L_2` | `CI_DEP_CTL.DEP_CTL_STATUS_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_DEP_CTL` | `SC_USER_2` | `CI_DEP_CTL.USER_ID = SC_USER_2.USER_ID` | domain_join_inventory |
| `CI_DEP_CTL` | `SC_USER_3` | `CI_DEP_CTL.BALANCED_USER_ID = SC_USER_3.USER_ID` | domain_join_inventory |
| `CI_PAY` | `CI_ACCT` | `CI_PAY.ACCT_ID = CI_ACCT.ACCT_ID` | canonical_chain:cashiering |
| `CI_PAY` | `CI_ACCT_PER` | `CI_PAY.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_PAY` | `CI_LOOKUP_VAL_L` | `CI_PAY.PAY_STATUS_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_PAY` | `CI_MATCH_TYPE_L` | `CI_PAY.MATCH_TYPE_CD = CI_MATCH_TYPE_L.MATCH_TYPE_CD` | domain_join_inventory |
| `CI_PAY` | `CI_PAY_CAN_RSN_L` | `CI_PAY.CAN_RSN_CD = CI_PAY_CAN_RSN_L.CAN_RSN_CD` | domain_join_inventory |
| `CI_PAY` | `CI_PAY_EVENT` | `CI_PAY.PAY_EVENT_ID = CI_PAY_EVENT.PAY_EVENT_ID` | domain_join_inventory |
| `CI_PAY_EVENT` | `CI_PAY` | `CI_PAY_EVENT.PAY_EVENT_ID = CI_PAY.PAY_EVENT_ID` | canonical_chain:cashiering |
| `CI_PAY_TNDR` | `CI_ACCT_PER` | `CI_PAY_TNDR.PAYOR_ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_PAY_TNDR` | `CI_LOOKUP_VAL_L` | `CI_PAY_TNDR.TNDR_STATUS_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_PAY_TNDR` | `CI_PAY_CAN_RSN_L` | `CI_PAY_TNDR.CAN_RSN_CD = CI_PAY_CAN_RSN_L.CAN_RSN_CD` | domain_join_inventory |
| `CI_PAY_TNDR` | `CI_PAY_EVENT` | `CI_PAY_TNDR.PAY_EVENT_ID = CI_PAY_EVENT.PAY_EVENT_ID` | domain_join_inventory |
| `CI_PAY_TNDR` | `CI_TENDER_TYPE_L` | `CI_PAY_TNDR.TENDER_TYPE_CD = CI_TENDER_TYPE_L.TENDER_TYPE_CD` | domain_join_inventory |
| `CI_PAY_TNDR` | `CI_TNDR_CTL` | `CI_PAY_TNDR.TNDR_CTL_ID = CI_TNDR_CTL.TNDR_CTL_ID` | domain_join_inventory |
| `CI_PP` | `CI_ACCT_PER` | `CI_PP.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_PP` | `CI_ACCT_PER_1` | `CI_PP.PAYOR_ACCT_ID = CI_ACCT_PER_1.ACCT_ID` | domain_join_inventory |
| `CI_PP` | `CI_LOOKUP_VAL_L` | `CI_PP.PP_CAN_RSN_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_PP` | `CI_LOOKUP_VAL_L_1` | `CI_PP.PP_STAT_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_PP` | `CI_PAY_METH_L` | `CI_PP.PAY_METH_CD = CI_PAY_METH_L.PAY_METH_CD` | domain_join_inventory |
| `CI_PP` | `CI_PP_TYPE_L` | `CI_PP.PP_TYPE_CD = CI_PP_TYPE_L.PP_TYPE_CD` | domain_join_inventory |
| `CI_PP` | `CI_THRD_PTY_L` | `CI_PP.THRD_PTY_PAYOR_CD = CI_THRD_PTY_L.THRD_PTY_PAYOR_CD` | domain_join_inventory |
| `CI_PP` | `SC_USER` | `CI_PP.USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_PP` | `SC_USER_1` | `CI_PP.LAST_STAT_USER_ID = SC_USER_1.USER_ID` | domain_join_inventory |
| `CI_TNDR_CTL` | `CI_BATCH_CTRL_L` | `CI_TNDR_CTL.BATCH_CD = CI_BATCH_CTRL_L.BATCH_CD` | domain_join_inventory |
| `CI_TNDR_CTL` | `CI_DEP_CTL` | `CI_TNDR_CTL.DEP_CTL_ID = CI_DEP_CTL.DEP_CTL_ID` | domain_join_inventory |
| `CI_TNDR_CTL` | `CI_LOOKUP_VAL_L` | `CI_TNDR_CTL.TNDR_CTL_ST_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_TNDR_CTL` | `CI_LOOKUP_VAL_L_1` | `CI_TNDR_CTL.TNDR_CTL_ST_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_TNDR_CTL` | `CI_TNDR_SRCE_L` | `CI_TNDR_CTL.TNDR_SOURCE_CD = CI_TNDR_SRCE_L.TNDR_SOURCE_CD` | domain_join_inventory |
| `CI_TNDR_CTL` | `SC_USER` | `CI_TNDR_CTL.BALANCED_USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_TNDR_CTL` | `SC_USER` | `CI_TNDR_CTL.USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_TNDR_CTL` | `SC_USER_1` | `CI_TNDR_CTL.BALANCED_USER_ID = SC_USER_1.USER_ID` | domain_join_inventory |
| `CI_TNDR_CTL` | `SC_USER_1` | `CI_TNDR_CTL.USER_ID = SC_USER_1.USER_ID` | domain_join_inventory |
| `CI_TNDR_DEP` | `CI_BANK_ACCOUNT_L` | `CI_TNDR_DEP.BANK_ACCT_KEY = CI_BANK_ACCOUNT_L.BANK_ACCT_KEY` | domain_join_inventory |
| `CI_TNDR_DEP` | `CI_BANK_ACCOUNT_L` | `CI_TNDR_DEP.BANK_CD = CI_BANK_ACCOUNT_L.BANK_CD` | domain_join_inventory |
| `CI_TNDR_DEP` | `CI_BANK_L` | `CI_TNDR_DEP.BANK_CD = CI_BANK_L.BANK_CD` | domain_join_inventory |

---

## Meter Operations (`meter_ops`)

### Canonical join chains

**usage_chain** — driver: `D1_USAGE`, grain: usage
```
CI_ACCT → CI_SA → C1_USAGE → D1_USAGE → D1_USAGE_SCALAR_DTL → D1_USAGE_PERIOD_SQ
```
- `CI_SA.SA_ID = C1_USAGE.SA_ID`
- `C1_USAGE.USAGE_ID = D1_USAGE.USG_EXT_ID`
- `D1_USAGE.D1_USAGE_ID = D1_USAGE_SCALAR_DTL.D1_USAGE_ID`

**device_install_chain** — driver: `D1_INSTALL_EVT`, grain: install_event (enrichment)
```
CI_SP → D1_INSTALL_EVT → D1_DVC_CFG → D1_DVC → D1_MEASR_COMP
```
- `D1_INSTALL_EVT.D1_DEVICE_ID = D1_DVC.D1_DEVICE_ID`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `C1_USAGE` | Auto-added coverage table for C1_USAGE | `BILL_CYC_CD`, `BO_STATUS_CD`, `BSEG_ID`, `BUS_OBJ_CD`, `CRE_DTTM`, `END_DTTM` | 27462 |
| `CI_ACCT` | Account | `FULL` | 1049 |
| `CI_ACCT_PER` |  | — | 1045 |
| `CI_PER_NAME` |  | `JUST`, `FLATTEN` | 925 |
| `CI_PREM` | Premise | `ADDRESS1`, `ADDRESS1_UPR`, `ADDRESS2`, `ADDRESS3`, `ADDRESS4`, `CIS_DIVISION` | 1041 |
| `CI_SA` | SA (Service Agreement) | `ACCT_ID`, `ALLOW_EST_SW`, `BUS_ACTIVITY_DESC`, `CHAR_PREM_ID`, `CIAC_REVIEW_DT`, `CIS_DIVISION` | 6643 |
| `CI_SP` | Service Point - CCB | `SP_ID`, `SP_TYPE_CD`, `PREM_ID`, `SP_STATUS_FLG`, `INSTALL_DT`, `ABOLISH_DT` | 3305 |
| `D1_DVC` | Device | `D1_DEVICE_ID`, `DEVICE_TYPE_CD`, `BUS_OBJ_CD`, `MANUFACTURER_CD`, `D1_MODEL_CD`, `D1_SPR_CD` | 5086 |
| `D1_DVC_CFG` |  | `DEVICE_CONFIG_ID`, `DEVICE_CONFIG_TYPE_CD`, `EFF_DTTM`, `BO_STATUS_CD`, `BO_DATA_AREA`, `BO_STATUS_REASON_CD` | 2466 |
| `D1_DVC_EVT` | Device events are developments that have taken place relative to a device, and can include power outages, power restorations, tampering alerts, command completions, among others. | `DVC_EVT_ID`, `DVC_EVT_TYPE_CD`, `BUS_OBJ_CD`, `EXT_EVT_NAME_FLG`, `D1_SPR_CD`, `BO_STATUS_CD` | 1436 |
| `D1_INSTALL_EVT` | Install Event | `INSTALL_EVT_ID`, `BO_STATUS_CD`, `D1_INSTALL_DTTM`, `D1_REMOVAL_DTTM`, `ARM_STAT_FLG`, `BO_DATA_AREA` | 2426 |
| `D1_MEASR_COMP` | Measuring components are single points for which data will be received and stored in the system. Measuring components can be associated to a device or not (these are virtual or stand-alone). This is helpful for the Clients as it allows them to retrieve the Measuring Components that's either related to a SP or not used. | `MEASR_COMP_ID`, `MEASR_COMP_TYPE_CD`, `LATEST_MSRMT_DTTM`, `MOST_RECENT_NON_EST_MSRMT_DTTM`, `ACCESS_GRP_CD`, `ADJ_LATEST_MSRMT_DTTM` | 7074 |
| `D1_SP_EQPMNT` | Auto-added coverage table for D1_SP_EQPMNT | `ACTIVE_INACTIVE_FLG`, `BO_DATA_AREA`, `COMMENTS`, `D1_DEVICE_ID`, `D1_INSTALL_DTTM`, `D1_REMOVAL_DTTM` | 2626 |
| `D1_USAGE` | Usage Transactions are records of bill determinant calculations for a Usage Subscription. This is useful to the Client as it allows them to retrieve the Bill information to the usage and measurement | `BO_STATUS_CD`, `BO_STATUS_REASON_CD`, `BUS_OBJ_CD`, `COMMENTS`, `CRE_DTTM`, `D1_SPR_CD` | 27704 |
| `D1_USAGE_PERIOD_SQ` | Auto-added coverage table for D1_USAGE_PERIOD_SQ | `BO_DATA_AREA`, `CHAR_TYPE_CD`, `CHAR_VAL`, `D1_FORMULA`, `D1_SP_ID`, `D1_SQI_CD` | 26500 |
| `D1_USAGE_SCALAR_DTL` |  | — | 28844 |
| `W1_ASSET` |  | — | 5087 |
| `W1_ASSET_CHAR` |  | — | 0 |
| `W1_ASSET_IDENTIFIER` |  | — | 15266 |
| `W1_ASSET_NODE` |  | — | 5230 |
| `W1_BOM_PART` |  | — | 0 |
| `W1_NODE` |  | — | 3310 |
| `W1_VENDOR_LOC` |  | — | 0 |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`CI_ACC_GRP_L`, `CI_CHAR_VAL_L`, `CI_LOOKUP_VAL_L`, `CI_MR_INSTR_L`, `CI_MR_WARN_L`, `CI_PREM_TYPE_L`, `CI_STATE_L`, `CI_TIME_ZONE_L`, `CI_TREND_AREA_L`, `D1_COMMAND_SET_L`, `D1_DVC_CFG_TYPE_L`, `D1_DVC_EVT_TYPE_L`, `D1_DVC_TYPE_L`, `D1_MANUFACTURER_L`, `D1_MODEL_L`, `D1_SPR_L`, `F1_BUS_OBJ_L`, `F1_BUS_OBJ_STATUS_L`, `F1_BUS_OBJ_STATUS_RSN_L`, `F1_EXT_LOOKUP_VAL_L`, `W1_APPROVAL_PROF_L`, `W1_ASSET_TYPE_L`, `W1_BUYER_L`, `W1_COST_CENTER_L`, `W1_EXPENSE_CD_L`, `W1_MAINTMGR_L`, `W1_NODE_TYPE_L`, `W1_PLANNER_L`, `W1_PROPERTY_UNIT_L`, `W1_SERVICE_AREA_L`, `W1_SPECIFICATION_L`

### Snapshot tables in this workstream

`D1_MSRMT_RPT_CURR`, `D1_USAGE_RPT_CURR`, `D1_USAGE_SCALAR_DTL_RPT_CURR`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `C1_USAGE` | `D1_USAGE` | `C1_USAGE.USAGE_ID = D1_USAGE.USG_EXT_ID` | canonical_chain:meter_ops |
| `CI_ACCT` | `CI_ACCT_ALERT` | `CI_ACCT.ACCT_ID = CI_ACCT_ALERT.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_MGMT_GR_L` | `CI_ACCT.ACCT_MGMT_GRP_CD = CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACC_GRP_L` | `CI_ACCT.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L_1` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BUD_PLAN_L` | `CI_ACCT.BUD_PLAN_CD = CI_BUD_PLAN_L.BUD_PLAN_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CIS_DIVISION_L` | `CI_ACCT.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_ACCT` | `CI_COLL_CL_L` | `CI_ACCT.COLL_CL_CD = CI_COLL_CL_L.COLL_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CUST_CL_L` | `CI_ACCT.CUST_CL_CD = CI_CUST_CL_L.CUST_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `SC_USER` | `CI_ACCT.BILL_PRT_INTERCEPT = SC_USER.USER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `C1_PER_CONTDET` | `CI_ACCT_PER.PER_ID = C1_PER_CONTDET.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER` | `CI_ACCT_PER.PER_ID = CI_PER.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_PREM` | `CI_CIS_DIVISION_L` | `CI_PREM.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_PREM` | `CI_MR_INSTR_L` | `CI_PREM.MR_INSTR_CD = CI_MR_INSTR_L.MR_INSTR_CD` | domain_join_inventory |
| `CI_PREM` | `CI_MR_WARN_L` | `CI_PREM.MR_WARN_CD = CI_MR_WARN_L.MR_WARN_CD` | domain_join_inventory |
| `CI_PREM` | `CI_PREM_TYPE_L` | `CI_PREM.PREM_TYPE_CD = CI_PREM_TYPE_L.PREM_TYPE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_SA` | `CI_PREM.PREM_ID = CI_SA.CHAR_PREM_ID` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.COUNTRY = CI_STATE_L.COUNTRY` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.STATE = CI_STATE_L.STATE` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L_1` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L_1.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.TREND_AREA_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.DESCR` | domain_join_inventory |
| `CI_SA` | `C1_USAGE` | `CI_SA.SA_ID = C1_USAGE.SA_ID` | canonical_chain:meter_ops |
| `CI_SA` | `CI_ACCT` | `CI_SA.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_ACCT_PER` | `CI_SA.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_BILL_CHG` | `CI_SA.SA_ID = CI_BILL_CHG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_BSEG` | `CI_SA.SA_ID = CI_BSEG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_CIS_DIVISION_L` | `CI_SA.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_FT` | `CI_SA.SA_ID = CI_FT.SA_ID` | canonical_chain:debt_mgmt |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.PROP_SA_STAT_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_1` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_2` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_2` | `CI_SA.SPECIAL_USAGE_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_3` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_3` | `CI_SA.STRT_RSN_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_4` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_4` | `CI_SA.STOP_RSN_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_NB_RULE_L` | `CI_SA.NB_RULE_CD = CI_NB_RULE_L.NB_RULE_CD` | domain_join_inventory |
| `CI_SA` | `CI_PREM` | `CI_SA.CHAR_PREM_ID = CI_PREM.PREM_ID` | domain_join_inventory |
| `CI_SA` | `CI_PROP_DCL_RSN_L` | `CI_SA.PROP_DCL_RSN_CD = CI_PROP_DCL_RSN_L.PROP_DCL_RSN_CD` | domain_join_inventory |
| `CI_SA` | `CI_SA_SP` | `CI_SA.SA_ID = CI_SA_SP.SA_ID` | canonical_chain:new_services |
| `CI_SA` | `CI_SA_TYPE` | `CI_SA.CIS_DIVISION = CI_SA_TYPE.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_SA_TYPE` | `CI_SA.SA_TYPE_CD = CI_SA_TYPE.SA_TYPE_CD` | domain_join_inventory |
| `CI_SA` | `CI_SA_TYPE_L` | `CI_SA.CIS_DIVISION = CI_SA_TYPE_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_SA_TYPE_L` | `CI_SA.SA_TYPE_CD = CI_SA_TYPE_L.SA_TYPE_CD` | domain_join_inventory |
| `CI_SA` | `CI_SIC_L` | `CI_SA.SIC_CD = CI_SIC_L.SIC_CD` | domain_join_inventory |
| `CI_SA` | `CI_SS_OPT_L` | `CI_SA.START_OPT_CD = CI_SS_OPT_L.START_OPT_CD` | domain_join_inventory |
| `CI_SA` | `CM_FT_BAL` | `CI_SA.SA_ID = CM_FT_BAL.SA_ID` | domain_join_inventory |
| `CI_SP` | `CI_PREM` | `CI_SP.PREM_ID = CI_PREM.PREM_ID` | domain_join_inventory |
| `D1_DVC` | `CI_ACC_GRP_L` | `D1_DVC.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `D1_DVC` | `CI_LOOKUP_VAL_L` | `D1_DVC.IN_DATA_SHIFT_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `D1_DVC` | `CI_LOOKUP_VAL_L_1` | `D1_DVC.ARMING_REQ_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `D1_DVC` | `CI_LOOKUP_VAL_L_2` | `D1_DVC.HEAD_END_REGISTR_STATUS_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `D1_DVC` | `D1_COMMAND_SET_L` | `D1_DVC.D1_CMD_SET_CD = D1_COMMAND_SET_L.D1_CMD_SET_CD` | domain_join_inventory |

*(87 additional joins — see `fk_join_map_full.csv`)*

---

## Customer Operations (`customer_ops`)

### Canonical join chains

**account_customer_chain** — driver: `CI_ACCT`, grain: account
```
CI_ACCT → CI_ACCT_PER → CI_PER → CI_PER_NAME → CI_PREM
```
- `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID AND CI_ACCT_PER.MAIN_CUST_SW = 'Y'`
- `CI_ACCT_PER.PER_ID = CI_PER.PER_ID`
- `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID AND CI_PER_NAME.NAME_TYPE_FLG = 'PRIM'`

**case_chain** — driver: `CI_CASE`, grain: case (enrichment)
```
CI_CASE → CI_CC → CI_ACCT → CI_PREM → CI_PER
```
- `CI_CASE.ACCT_ID = CI_ACCT.ACCT_ID`
- `CI_CASE.PREM_ID = CI_PREM.PREM_ID`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `C1_PER_CONTDET` |  | — | 1790 |
| `CI_ACCT` | Account | `FULL` | 1049 |
| `CI_ACCT_ALERT` |  | — | 321 |
| `CI_ACCT_PER` |  | — | 1045 |
| `CI_BSEG` | Bill Segment | `BILL_CYC_CD`, `BILL_ID`, `BILL_SCNR_ID`, `BSEG_DATA_AREA`, `BSEG_ID`, `BSEG_STAT_FLG` | 168608 |
| `CI_BSEG_CALC` | Auto-added coverage table for CI_BSEG_CALC | `BSEG_ID`, `HEADER_SEQ`, `START_DT`, `CURRENCY_CD`, `END_DT`, `RS_CD` | 167526 |
| `CI_CASE` |  | — | 14 |
| `CI_CC` |  | — | 1173 |
| `CI_LANDLORD` | Auto-added coverage table for CI_LANDLORD | `ACCT_ID`, `DESCR`, `DESCR_UPR`, `LL_ID`, `VERSION` | 117 |
| `CI_LL_DETAIL` |  | — | 810 |
| `CI_PER` | Justification: This domain will retrieve Person Information. At the very least, it matches the schema on datavergence. It should also be able to account for additional data entry in the future. | `ADDRESS1`, `ADDRESS2`, `ADDRESS3`, `ADDRESS4`, `CITY`, `COUNTRY` | 923 |
| `CI_PER_NAME` |  | `JUST`, `FLATTEN` | 925 |
| `CI_PER_PER` |  | — | 0 |
| `CI_PREM` | Premise | `ADDRESS1`, `ADDRESS1_UPR`, `ADDRESS2`, `ADDRESS3`, `ADDRESS4`, `CIS_DIVISION` | 1041 |
| `CI_PREM_CHAR` | Auto-added coverage table for CI_PREM_CHAR | `ADHOC_CHAR_VAL`, `CHAR_TYPE_CD`, `CHAR_VAL`, `CHAR_VAL_FK1`, `CHAR_VAL_FK2`, `CHAR_VAL_FK3` | 5830 |
| `CI_SA` | SA (Service Agreement) | `ACCT_ID`, `ALLOW_EST_SW`, `BUS_ACTIVITY_DESC`, `CHAR_PREM_ID`, `CIAC_REVIEW_DT`, `CIS_DIVISION` | 6643 |
| `CI_SA_TYPE` |  | — | 105 |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`CI_ACCT_MGMT_GR_L`, `CI_ACC_GRP_L`, `CI_ALERT_TYPE_L`, `CI_BILL_CYC_L`, `CI_BUD_PLAN_L`, `CI_CASE_STATUS_L`, `CI_CASE_TYPE_L`, `CI_CC_CL_L`, `CI_CC_TYPE_L`, `CI_CIS_DIVISION_L`, `CI_COLL_CL_L`, `CI_CUST_CL_L`, `CI_DEBT_CL_L`, `CI_DEP_CL_L`, `CI_GEO_TYPE_L`, `CI_LETTER_TMPL_L`, `CI_LOOKUP_VAL_L`, `CI_MR_INSTR_L`, `CI_MR_WARN_L`, `CI_NB_RULE_L`, `CI_PER_REL_TYPE_L`, `CI_PHONE_TYPE_L`, `CI_PREM_TYPE_L`, `CI_PROP_DCL_RSN_L`, `CI_REV_CL_L`, `CI_SA_TYPE_L`, `CI_SIC_L`, `CI_SS_OPT_L`, `CI_STATE_L`, `CI_SVC_TYPE_L`, `CI_TIME_ZONE_L`, `CI_TREND_AREA_L`, `CI_WO_DEBT_CL_L`, `SC_USER`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `CI_ACCT` | `CI_ACCT_ALERT` | `CI_ACCT.ACCT_ID = CI_ACCT_ALERT.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_MGMT_GR_L` | `CI_ACCT.ACCT_MGMT_GRP_CD = CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACC_GRP_L` | `CI_ACCT.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L_1` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BUD_PLAN_L` | `CI_ACCT.BUD_PLAN_CD = CI_BUD_PLAN_L.BUD_PLAN_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CIS_DIVISION_L` | `CI_ACCT.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_ACCT` | `CI_COLL_CL_L` | `CI_ACCT.COLL_CL_CD = CI_COLL_CL_L.COLL_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CUST_CL_L` | `CI_ACCT.CUST_CL_CD = CI_CUST_CL_L.CUST_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `SC_USER` | `CI_ACCT.BILL_PRT_INTERCEPT = SC_USER.USER_ID` | domain_join_inventory |
| `CI_ACCT_ALERT` | `CI_ALERT_TYPE_L` | `CI_ACCT_ALERT.ALERT_TYPE_CD = CI_ALERT_TYPE_L.ALERT_TYPE_CD` | domain_join_inventory |
| `CI_ACCT_PER` | `C1_PER_CONTDET` | `CI_ACCT_PER.PER_ID = C1_PER_CONTDET.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER` | `CI_ACCT_PER.PER_ID = CI_PER.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL` | `CI_BSEG.BILL_ID = CI_BILL.BILL_ID` | canonical_chain:billing |
| `CI_BSEG` | `CI_BILL_CAN_RSN_L` | `CI_BSEG.CAN_RSN_CD = CI_BILL_CAN_RSN_L.CAN_RSN_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL_CYC_L_1` | `CI_BSEG.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL_CYC_L_2` | `CI_BSEG.BILL_CYC_CD = CI_BILL_CYC_L_2.BILL_CYC_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_CALC` | `CI_BSEG.BSEG_ID = CI_BSEG_CALC.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_READ` | `CI_BSEG.BSEG_ID = CI_BSEG_READ.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_SQ` | `CI_BSEG.BSEG_ID = CI_BSEG_SQ.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_LOOKUP_VAL_L_2` | `CI_BSEG.BSEG_STAT_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_LOOKUP_VAL_L_3` | `CI_BSEG.BSEG_STAT_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_SA` | `CI_BSEG.SA_ID = CI_SA.SA_ID` | domain_join_inventory |
| `CI_BSEG` | `FT_GL_SUMMARY` | `CI_BSEG.BSEG_ID = FT_GL_SUMMARY.SIBLING_ID` | domain_join_inventory |
| `CI_BSEG_CALC` | `CI_RS_L` | `CI_BSEG_CALC.RS_CD = CI_RS_L.RS_CD` | domain_join_inventory |
| `CI_CASE` | `CI_ACCT` | `CI_CASE.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_CASE` | `CI_CASE_STATUS_L` | `CI_CASE.CASE_STATUS_CD = CI_CASE_STATUS_L.CASE_STATUS_CD` | domain_join_inventory |
| `CI_CASE` | `CI_CASE_STATUS_L` | `CI_CASE.CASE_TYPE_CD = CI_CASE_STATUS_L.CASE_TYPE_CD` | domain_join_inventory |
| `CI_CASE` | `CI_CASE_TYPE_L` | `CI_CASE.CASE_TYPE_CD = CI_CASE_TYPE_L.CASE_TYPE_CD` | domain_join_inventory |
| `CI_CASE` | `CI_LOOKUP_VAL_L` | `CI_CASE.CASE_COND_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_CASE` | `CI_PER_NAME` | `CI_CASE.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_CASE` | `CI_PHONE_TYPE_L` | `CI_CASE.PHONE_TYPE_CD = CI_PHONE_TYPE_L.PHONE_TYPE_CD` | domain_join_inventory |
| `CI_CASE` | `CI_PREM` | `CI_CASE.PREM_ID = CI_PREM.PREM_ID` | domain_join_inventory |
| `CI_CASE` | `SC_USER` | `CI_CASE.USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_CC` | `CI_ACCT` | `CI_CC.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_CC` | `CI_CC_CL_L` | `CI_CC.CC_CL_CD = CI_CC_CL_L.CC_CL_CD` | domain_join_inventory |
| `CI_CC` | `CI_CC_TYPE_L` | `CI_CC.CC_CL_CD = CI_CC_TYPE_L.CC_CL_CD` | domain_join_inventory |
| `CI_CC` | `CI_CC_TYPE_L` | `CI_CC.CC_TYPE_CD = CI_CC_TYPE_L.CC_TYPE_CD` | domain_join_inventory |
| `CI_CC` | `CI_LETTER_TMPL_L` | `CI_CC.LTR_TMPL_CD = CI_LETTER_TMPL_L.LTR_TMPL_CD` | domain_join_inventory |
| `CI_CC` | `CI_LOOKUP_VAL_L` | `CI_CC.CC_ENTITY_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_CC` | `CI_LOOKUP_VAL_L_1` | `CI_CC.CC_STATUS_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_CC` | `CI_LOOKUP_VAL_L_2` | `CI_CC.CONTACT_METH_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_CC` | `CI_PER_NAME` | `CI_CC.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_CC` | `CI_PREM` | `CI_CC.PREM_ID = CI_PREM.PREM_ID` | domain_join_inventory |
| `CI_CC` | `SC_USER` | `CI_CC.USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_LANDLORD` | `CI_ACCT` | `CI_LANDLORD.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_LANDLORD` | `CI_ACCT_PER` | `CI_LANDLORD.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_LANDLORD` | `CI_PREM` | `CI_LANDLORD.LL_ID = CI_PREM.LL_ID` | domain_join_inventory |
| `CI_PER` | `CI_LOOKUP_VAL_L` | `CI_PER.PER_OR_BUS_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_PER` | `CI_LOOKUP_VAL_L_1` | `CI_PER.LS_SL_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_PER` | `CI_LOOKUP_VAL_L_2` | `CI_PER.RECV_MKTG_INFO_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_PER` | `CI_LOOKUP_VAL_L_3` | `CI_PER.WEB_PWD_HINT_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_PER` | `CI_LOOKUP_VAL_L_6` | `CI_PER.PER_OR_BUS_FLG = CI_LOOKUP_VAL_L_6.FIELD_VALUE` | domain_join_inventory |
| `CI_PER` | `CI_TIME_ZONE_L` | `CI_PER.TIME_ZONE_CD = CI_TIME_ZONE_L.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_CIS_DIVISION_L` | `CI_PREM.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_PREM` | `CI_MR_INSTR_L` | `CI_PREM.MR_INSTR_CD = CI_MR_INSTR_L.MR_INSTR_CD` | domain_join_inventory |
| `CI_PREM` | `CI_MR_WARN_L` | `CI_PREM.MR_WARN_CD = CI_MR_WARN_L.MR_WARN_CD` | domain_join_inventory |

*(43 additional joins — see `fk_join_map_full.csv`)*

---

## New Services and Planning (`new_services`)

### Canonical join chains

**service_agreement_chain** — driver: `CI_SA`, grain: sa
```
CI_ACCT → CI_SA → CI_SA_SP → CI_SP → CI_SA_TYPE → CI_ENRL
```
- `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID`
- `CI_SA.SA_ID = CI_SA_SP.SA_ID`
- `CI_SA_SP.SP_ID = CI_SP.SP_ID`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `CI_ACCT` | Account | `FULL` | 1049 |
| `CI_ACCT_PER` |  | — | 1045 |
| `CI_ENRL` |  | — | 6 |
| `CI_PER_NAME` |  | `JUST`, `FLATTEN` | 925 |
| `CI_PREM` | Premise | `ADDRESS1`, `ADDRESS1_UPR`, `ADDRESS2`, `ADDRESS3`, `ADDRESS4`, `CIS_DIVISION` | 1041 |
| `CI_SA` | SA (Service Agreement) | `ACCT_ID`, `ALLOW_EST_SW`, `BUS_ACTIVITY_DESC`, `CHAR_PREM_ID`, `CIAC_REVIEW_DT`, `CIS_DIVISION` | 6643 |
| `CI_SA_SP` |  | — | 4269 |
| `CI_SA_TYPE` |  | — | 105 |
| `CI_SP` | Service Point - CCB | `SP_ID`, `SP_TYPE_CD`, `PREM_ID`, `SP_STATUS_FLG`, `INSTALL_DT`, `ABOLISH_DT` | 3305 |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`CI_BILL_CYC_L`, `CI_BUD_PLAN_L`, `CI_CIS_DIVISION_L`, `CI_COLL_CL_L`, `CI_CUST_CL_L`, `CI_LOOKUP_VAL_L`, `CI_MR_INSTR_L`, `CI_MR_WARN_L`, `CI_NB_RULE_L`, `CI_PREM_TYPE_L`, `CI_PROP_DCL_RSN_L`, `CI_SA_TYPE_L`, `CI_SIC_L`, `CI_SS_OPT_L`, `CI_STATE_L`, `CI_SVC_TYPE_L`, `CI_TIME_ZONE_L`, `CI_TREND_AREA_L`, `SC_USER`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `CI_ACCT` | `CI_ACCT_ALERT` | `CI_ACCT.ACCT_ID = CI_ACCT_ALERT.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_MGMT_GR_L` | `CI_ACCT.ACCT_MGMT_GRP_CD = CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACC_GRP_L` | `CI_ACCT.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L_1` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BUD_PLAN_L` | `CI_ACCT.BUD_PLAN_CD = CI_BUD_PLAN_L.BUD_PLAN_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CIS_DIVISION_L` | `CI_ACCT.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_ACCT` | `CI_COLL_CL_L` | `CI_ACCT.COLL_CL_CD = CI_COLL_CL_L.COLL_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CUST_CL_L` | `CI_ACCT.CUST_CL_CD = CI_CUST_CL_L.CUST_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `SC_USER` | `CI_ACCT.BILL_PRT_INTERCEPT = SC_USER.USER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `C1_PER_CONTDET` | `CI_ACCT_PER.PER_ID = C1_PER_CONTDET.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER` | `CI_ACCT_PER.PER_ID = CI_PER.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_PREM` | `CI_CIS_DIVISION_L` | `CI_PREM.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_PREM` | `CI_MR_INSTR_L` | `CI_PREM.MR_INSTR_CD = CI_MR_INSTR_L.MR_INSTR_CD` | domain_join_inventory |
| `CI_PREM` | `CI_MR_WARN_L` | `CI_PREM.MR_WARN_CD = CI_MR_WARN_L.MR_WARN_CD` | domain_join_inventory |
| `CI_PREM` | `CI_PREM_TYPE_L` | `CI_PREM.PREM_TYPE_CD = CI_PREM_TYPE_L.PREM_TYPE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_SA` | `CI_PREM.PREM_ID = CI_SA.CHAR_PREM_ID` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.COUNTRY = CI_STATE_L.COUNTRY` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.STATE = CI_STATE_L.STATE` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L_1` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L_1.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.TREND_AREA_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.DESCR` | domain_join_inventory |
| `CI_SA` | `C1_USAGE` | `CI_SA.SA_ID = C1_USAGE.SA_ID` | canonical_chain:meter_ops |
| `CI_SA` | `CI_ACCT` | `CI_SA.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_ACCT_PER` | `CI_SA.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_BILL_CHG` | `CI_SA.SA_ID = CI_BILL_CHG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_BSEG` | `CI_SA.SA_ID = CI_BSEG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_CIS_DIVISION_L` | `CI_SA.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_FT` | `CI_SA.SA_ID = CI_FT.SA_ID` | canonical_chain:debt_mgmt |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.PROP_SA_STAT_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_1` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_2` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_2` | `CI_SA.SPECIAL_USAGE_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_3` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_3` | `CI_SA.STRT_RSN_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_4` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_4` | `CI_SA.STOP_RSN_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_NB_RULE_L` | `CI_SA.NB_RULE_CD = CI_NB_RULE_L.NB_RULE_CD` | domain_join_inventory |
| `CI_SA` | `CI_PREM` | `CI_SA.CHAR_PREM_ID = CI_PREM.PREM_ID` | domain_join_inventory |
| `CI_SA` | `CI_PROP_DCL_RSN_L` | `CI_SA.PROP_DCL_RSN_CD = CI_PROP_DCL_RSN_L.PROP_DCL_RSN_CD` | domain_join_inventory |
| `CI_SA` | `CI_SA_SP` | `CI_SA.SA_ID = CI_SA_SP.SA_ID` | canonical_chain:new_services |
| `CI_SA` | `CI_SA_TYPE` | `CI_SA.CIS_DIVISION = CI_SA_TYPE.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_SA_TYPE` | `CI_SA.SA_TYPE_CD = CI_SA_TYPE.SA_TYPE_CD` | domain_join_inventory |
| `CI_SA` | `CI_SA_TYPE_L` | `CI_SA.CIS_DIVISION = CI_SA_TYPE_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_SA_TYPE_L` | `CI_SA.SA_TYPE_CD = CI_SA_TYPE_L.SA_TYPE_CD` | domain_join_inventory |
| `CI_SA` | `CI_SIC_L` | `CI_SA.SIC_CD = CI_SIC_L.SIC_CD` | domain_join_inventory |
| `CI_SA` | `CI_SS_OPT_L` | `CI_SA.START_OPT_CD = CI_SS_OPT_L.START_OPT_CD` | domain_join_inventory |
| `CI_SA` | `CM_FT_BAL` | `CI_SA.SA_ID = CM_FT_BAL.SA_ID` | domain_join_inventory |
| `CI_SA_SP` | `CI_SP` | `CI_SA_SP.SP_ID = CI_SP.SP_ID` | canonical_chain:new_services |
| `CI_SA_TYPE` | `CI_DEBT_CL_L` | `CI_SA_TYPE.DEBT_CL_CD = CI_DEBT_CL_L.DEBT_CL_CD` | domain_join_inventory |
| `CI_SA_TYPE` | `CI_DEP_CL_L` | `CI_SA_TYPE.DEP_CL_CD = CI_DEP_CL_L.DEP_CL_CD` | domain_join_inventory |
| `CI_SA_TYPE` | `CI_LOOKUP_VAL_L_5` | `CI_SA_TYPE.SPECIAL_ROLE_FLG = CI_LOOKUP_VAL_L_5.FIELD_VALUE` | domain_join_inventory |
| `CI_SA_TYPE` | `CI_REV_CL_L` | `CI_SA_TYPE.REV_CL_CD = CI_REV_CL_L.REV_CL_CD` | domain_join_inventory |
| `CI_SA_TYPE` | `CI_SA_TYPE_L` | `CI_SA_TYPE.CIS_DIVISION = CI_SA_TYPE_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA_TYPE` | `CI_SA_TYPE_L` | `CI_SA_TYPE.SA_TYPE_CD = CI_SA_TYPE_L.SA_TYPE_CD` | domain_join_inventory |

*(3 additional joins — see `fk_join_map_full.csv`)*

---

## Finance (`finance`)

### Canonical join chains

**financial_transaction_chain** — driver: `CI_FT`, grain: ft
```
CI_ACCT → CI_SA → CI_FT → CI_FT_GL → CI_FT_PROC
```
- `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID`
- `CI_SA.SA_ID = CI_FT.SA_ID`
- `CI_FT.FT_ID = CI_FT_GL.FT_ID`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `CI_ACCT` | Account | `FULL` | 1049 |
| `CI_ACCT_PER` |  | — | 1045 |
| `CI_ADJ` | Auto-added coverage table for CI_ADJ | `BEHALF_SA_ID`, `ADJ_ID`, `SA_ID`, `ADJ_TYPE_CD`, `ADJ_STATUS_FLG`, `CRE_DT` | 12242 |
| `CI_BAL_CTL_GRP` |  | — | 7 |
| `CI_BILL_CHG` |  | — | 18116 |
| `CI_BSEG` | Bill Segment | `BILL_CYC_CD`, `BILL_ID`, `BILL_SCNR_ID`, `BSEG_DATA_AREA`, `BSEG_ID`, `BSEG_STAT_FLG` | 168608 |
| `CI_B_CHG_LINE` |  | — | 18127 |
| `CI_FT` | Financial Transaction | `FT_ID`, `SA_ID`, `SIBLING_ID`, `FT_TYPE_FLG`, `CUR_AMT`, `GL_DIVISION` | 337824 |
| `CI_FT_GL` |  | `FT_ID`, `GL_SEQ_NBR`, `DST_ID`, `CHAR_TYPE_CD`, `AMOUNT`, `CHAR_VAL` | 140849 |
| `CI_FT_PROC` |  | `FT_ID`, `BATCH_CD`, `BATCH_NBR`, `SPR_CD`, `ADJ_ID`, `VERSION` | 62415 |
| `CI_PAY_SEG` | Auto-added coverage table for CI_PAY_SEG | `PAY_SEG_ID`, `CURRENCY_CD`, `PAY_ID`, `SA_ID`, `PAY_SEG_AMT`, `VERSION` | 154389 |
| `CI_PER_NAME` |  | `JUST`, `FLATTEN` | 925 |
| `CI_PREM` | Premise | `ADDRESS1`, `ADDRESS1_UPR`, `ADDRESS2`, `ADDRESS3`, `ADDRESS4`, `CIS_DIVISION` | 1041 |
| `CI_SA` | SA (Service Agreement) | `ACCT_ID`, `ALLOW_EST_SW`, `BUS_ACTIVITY_DESC`, `CHAR_PREM_ID`, `CIAC_REVIEW_DT`, `CIS_DIVISION` | 6643 |
| `CI_SA_TYPE` |  | — | 105 |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`CI_ACCT_MGMT_GR_L`, `CI_ADJ_CAN_RSN_L`, `CI_ADJ_TYPE_L`, `CI_BILL_CAN_RSN_L`, `CI_BILL_CYC_L`, `CI_BUD_PLAN_L`, `CI_CIS_DIVISION_L`, `CI_COLL_CL_L`, `CI_CUST_CL_L`, `CI_GL_DIVISION_L`, `CI_LOOKUP_VAL_L`, `CI_MR_INSTR_L`, `CI_MR_WARN_L`, `CI_NB_RULE_L`, `CI_PREM_TYPE_L`, `CI_PROP_DCL_RSN_L`, `CI_SA_TYPE_L`, `CI_SIC_L`, `CI_SS_OPT_L`, `CI_STATE_L`, `CI_TIME_ZONE_L`, `CI_TREND_AREA_L`, `SC_USER`

### Snapshot tables in this workstream

`FT_GL_DISTRIBUTION_RPT_CURR`, `FT_RPT_CURR`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `CI_ACCT` | `CI_ACCT_ALERT` | `CI_ACCT.ACCT_ID = CI_ACCT_ALERT.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_MGMT_GR_L` | `CI_ACCT.ACCT_MGMT_GRP_CD = CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACC_GRP_L` | `CI_ACCT.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L_1` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BUD_PLAN_L` | `CI_ACCT.BUD_PLAN_CD = CI_BUD_PLAN_L.BUD_PLAN_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CIS_DIVISION_L` | `CI_ACCT.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_ACCT` | `CI_COLL_CL_L` | `CI_ACCT.COLL_CL_CD = CI_COLL_CL_L.COLL_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CUST_CL_L` | `CI_ACCT.CUST_CL_CD = CI_CUST_CL_L.CUST_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `SC_USER` | `CI_ACCT.BILL_PRT_INTERCEPT = SC_USER.USER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `C1_PER_CONTDET` | `CI_ACCT_PER.PER_ID = C1_PER_CONTDET.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER` | `CI_ACCT_PER.PER_ID = CI_PER.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_ADJ` | `CI_ADJ_CAN_RSN_L` | `CI_ADJ.CAN_RSN_CD = CI_ADJ_CAN_RSN_L.CAN_RSN_CD` | domain_join_inventory |
| `CI_ADJ` | `CI_ADJ_TYPE_L` | `CI_ADJ.ADJ_TYPE_CD = CI_ADJ_TYPE_L.ADJ_TYPE_CD` | domain_join_inventory |
| `CI_ADJ` | `CI_LOOKUP_VAL_L_4` | `CI_ADJ.ADJ_STATUS_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `CI_BAL_CTL_GRP` | `CI_LOOKUP_VAL_L_5` | `CI_BAL_CTL_GRP.BALANCING_STAT_FLG = CI_LOOKUP_VAL_L_5.FIELD_VALUE` | domain_join_inventory |
| `CI_BILL_CHG` | `CI_B_CHG_LINE` | `CI_BILL_CHG.BILLABLE_CHG_ID = CI_B_CHG_LINE.BILLABLE_CHG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL` | `CI_BSEG.BILL_ID = CI_BILL.BILL_ID` | canonical_chain:billing |
| `CI_BSEG` | `CI_BILL_CAN_RSN_L` | `CI_BSEG.CAN_RSN_CD = CI_BILL_CAN_RSN_L.CAN_RSN_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL_CYC_L_1` | `CI_BSEG.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL_CYC_L_2` | `CI_BSEG.BILL_CYC_CD = CI_BILL_CYC_L_2.BILL_CYC_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_CALC` | `CI_BSEG.BSEG_ID = CI_BSEG_CALC.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_READ` | `CI_BSEG.BSEG_ID = CI_BSEG_READ.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_SQ` | `CI_BSEG.BSEG_ID = CI_BSEG_SQ.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_LOOKUP_VAL_L_2` | `CI_BSEG.BSEG_STAT_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_LOOKUP_VAL_L_3` | `CI_BSEG.BSEG_STAT_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_SA` | `CI_BSEG.SA_ID = CI_SA.SA_ID` | domain_join_inventory |
| `CI_BSEG` | `FT_GL_SUMMARY` | `CI_BSEG.BSEG_ID = FT_GL_SUMMARY.SIBLING_ID` | domain_join_inventory |
| `CI_FT` | `CI_ADJ` | `CI_FT.PARENT_ID = CI_ADJ.ADJ_TYPE_CD` | domain_join_inventory |
| `CI_FT` | `CI_ADJ` | `CI_FT.SIBLING_ID = CI_ADJ.ADJ_ID` | domain_join_inventory |
| `CI_FT` | `CI_BAL_CTL_GRP` | `CI_FT.BAL_CTL_GRP_ID = CI_BAL_CTL_GRP.BAL_CTL_GRP_ID` | domain_join_inventory |
| `CI_FT` | `CI_BSEG` | `CI_FT.BILL_ID = CI_BSEG.BILL_ID` | domain_join_inventory |
| `CI_FT` | `CI_BSEG` | `CI_FT.SIBLING_ID = CI_BSEG.BSEG_ID` | domain_join_inventory |
| `CI_FT` | `CI_FT_GL` | `CI_FT.FT_ID = CI_FT_GL.FT_ID` | canonical_chain:finance |
| `CI_FT` | `CI_GL_DIVISION_L` | `CI_FT.GL_DIVISION = CI_GL_DIVISION_L.GL_DIVISION` | domain_join_inventory |
| `CI_FT` | `CI_PAY_SEG` | `CI_FT.PARENT_ID = CI_PAY_SEG.PAY_ID` | domain_join_inventory |
| `CI_FT` | `CI_PAY_SEG` | `CI_FT.SIBLING_ID = CI_PAY_SEG.PAY_SEG_ID` | domain_join_inventory |
| `CI_FT` | `CI_SA` | `CI_FT.SA_ID = CI_SA.SA_ID` | domain_join_inventory |
| `CI_FT` | `SC_USER` | `CI_FT.FREEZE_USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_PREM` | `CI_CIS_DIVISION_L` | `CI_PREM.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_PREM` | `CI_MR_INSTR_L` | `CI_PREM.MR_INSTR_CD = CI_MR_INSTR_L.MR_INSTR_CD` | domain_join_inventory |
| `CI_PREM` | `CI_MR_WARN_L` | `CI_PREM.MR_WARN_CD = CI_MR_WARN_L.MR_WARN_CD` | domain_join_inventory |
| `CI_PREM` | `CI_PREM_TYPE_L` | `CI_PREM.PREM_TYPE_CD = CI_PREM_TYPE_L.PREM_TYPE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_SA` | `CI_PREM.PREM_ID = CI_SA.CHAR_PREM_ID` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.COUNTRY = CI_STATE_L.COUNTRY` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.STATE = CI_STATE_L.STATE` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L_1` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L_1.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.TREND_AREA_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.DESCR` | domain_join_inventory |
| `CI_SA` | `C1_USAGE` | `CI_SA.SA_ID = C1_USAGE.SA_ID` | canonical_chain:meter_ops |
| `CI_SA` | `CI_ACCT` | `CI_SA.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_ACCT_PER` | `CI_SA.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_BILL_CHG` | `CI_SA.SA_ID = CI_BILL_CHG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_BSEG` | `CI_SA.SA_ID = CI_BSEG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_CIS_DIVISION_L` | `CI_SA.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_FT` | `CI_SA.SA_ID = CI_FT.SA_ID` | canonical_chain:debt_mgmt |

*(28 additional joins — see `fk_join_map_full.csv`)*

---

## Debt Management (`debt_mgmt`)

### Canonical join chains

**debt_chain** — driver: `CI_FT`, grain: sa
```
CI_ACCT → CI_SA → CI_FT → CI_COLL_PROC → C1_PA_RQST → C1_PA_RQST_REL_OBJ
```
- `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID`
- `CI_SA.SA_ID = CI_FT.SA_ID`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `C1_PA_RQST` | This table contains information on the arrangement downpayment, arrangement amounts, number of installments, and installment amount. | `PA_RQST_ID`, `BO_STATUS_REASON_CD`, `BO_STATUS_CD`, `PA_RQST_NBR_INSTALLMENT`, `STATUS_UPD_DTTM`, `ILM_DT` | 20 |
| `C1_PA_RQST_REL_OBJ` | Auto-added coverage table for C1_PA_RQST_REL_OBJ | `PA_RQST_ID`, `PA_RQST_REL_OBJ_TYPE_FLG`, `SEQ_NUM`, `MAINT_OBJ_CD`, `PK_VALUE1`, `PK_VALUE2` | 28 |
| `CI_ACCT` | Account | `FULL` | 1049 |
| `CI_ACCT_PER` |  | — | 1045 |
| `CI_COLL_PROC` | Collection Process | — | 11478 |
| `CI_FT` | Financial Transaction | `FT_ID`, `SA_ID`, `SIBLING_ID`, `FT_TYPE_FLG`, `CUR_AMT`, `GL_DIVISION` | 337824 |
| `CI_PER_NAME` |  | `JUST`, `FLATTEN` | 925 |
| `CI_PREM` | Premise | `ADDRESS1`, `ADDRESS1_UPR`, `ADDRESS2`, `ADDRESS3`, `ADDRESS4`, `CIS_DIVISION` | 1041 |
| `CI_SA` | SA (Service Agreement) | `ACCT_ID`, `ALLOW_EST_SW`, `BUS_ACTIVITY_DESC`, `CHAR_PREM_ID`, `CIAC_REVIEW_DT`, `CIS_DIVISION` | 6643 |
| `CI_SEV_EVT` |  | — | 11592 |
| `CI_SEV_PROC` |  | — | 2267 |
| `CI_WO_EVT` |  | — | 5841 |
| `CI_WO_PROC` |  | — | 1637 |
| `CI_WO_PROC_SA` |  | — | 4404 |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`CI_ACCT_MGMT_GR_L`, `CI_BILL_CYC_L`, `CI_BUD_PLAN_L`, `CI_COLL_CL_L`, `CI_CUST_CL_L`, `CI_LOOKUP_VAL_L`, `CI_MR_INSTR_L`, `CI_MR_WARN_L`, `CI_PREM_TYPE_L`, `CI_SA_TYPE_L`, `CI_SEV_EVT_TYPE_L`, `CI_SEV_PROC_TMP_L`, `CI_STATE_L`, `CI_TIME_ZONE_L`, `CI_TREND_AREA_L`, `CI_WO_CNTL_L`, `CI_WO_DEBT_CL_L`, `CI_WO_EVT_TYP_L`, `CI_WO_PROC_TMPL_L`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `CI_ACCT` | `CI_ACCT_ALERT` | `CI_ACCT.ACCT_ID = CI_ACCT_ALERT.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_MGMT_GR_L` | `CI_ACCT.ACCT_MGMT_GRP_CD = CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACC_GRP_L` | `CI_ACCT.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L_1` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BUD_PLAN_L` | `CI_ACCT.BUD_PLAN_CD = CI_BUD_PLAN_L.BUD_PLAN_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CIS_DIVISION_L` | `CI_ACCT.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_ACCT` | `CI_COLL_CL_L` | `CI_ACCT.COLL_CL_CD = CI_COLL_CL_L.COLL_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CUST_CL_L` | `CI_ACCT.CUST_CL_CD = CI_CUST_CL_L.CUST_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `SC_USER` | `CI_ACCT.BILL_PRT_INTERCEPT = SC_USER.USER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `C1_PER_CONTDET` | `CI_ACCT_PER.PER_ID = C1_PER_CONTDET.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER` | `CI_ACCT_PER.PER_ID = CI_PER.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_FT` | `CI_ADJ` | `CI_FT.PARENT_ID = CI_ADJ.ADJ_TYPE_CD` | domain_join_inventory |
| `CI_FT` | `CI_ADJ` | `CI_FT.SIBLING_ID = CI_ADJ.ADJ_ID` | domain_join_inventory |
| `CI_FT` | `CI_BAL_CTL_GRP` | `CI_FT.BAL_CTL_GRP_ID = CI_BAL_CTL_GRP.BAL_CTL_GRP_ID` | domain_join_inventory |
| `CI_FT` | `CI_BSEG` | `CI_FT.BILL_ID = CI_BSEG.BILL_ID` | domain_join_inventory |
| `CI_FT` | `CI_BSEG` | `CI_FT.SIBLING_ID = CI_BSEG.BSEG_ID` | domain_join_inventory |
| `CI_FT` | `CI_FT_GL` | `CI_FT.FT_ID = CI_FT_GL.FT_ID` | canonical_chain:finance |
| `CI_FT` | `CI_GL_DIVISION_L` | `CI_FT.GL_DIVISION = CI_GL_DIVISION_L.GL_DIVISION` | domain_join_inventory |
| `CI_FT` | `CI_PAY_SEG` | `CI_FT.PARENT_ID = CI_PAY_SEG.PAY_ID` | domain_join_inventory |
| `CI_FT` | `CI_PAY_SEG` | `CI_FT.SIBLING_ID = CI_PAY_SEG.PAY_SEG_ID` | domain_join_inventory |
| `CI_FT` | `CI_SA` | `CI_FT.SA_ID = CI_SA.SA_ID` | domain_join_inventory |
| `CI_FT` | `SC_USER` | `CI_FT.FREEZE_USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_PREM` | `CI_CIS_DIVISION_L` | `CI_PREM.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_PREM` | `CI_MR_INSTR_L` | `CI_PREM.MR_INSTR_CD = CI_MR_INSTR_L.MR_INSTR_CD` | domain_join_inventory |
| `CI_PREM` | `CI_MR_WARN_L` | `CI_PREM.MR_WARN_CD = CI_MR_WARN_L.MR_WARN_CD` | domain_join_inventory |
| `CI_PREM` | `CI_PREM_TYPE_L` | `CI_PREM.PREM_TYPE_CD = CI_PREM_TYPE_L.PREM_TYPE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_SA` | `CI_PREM.PREM_ID = CI_SA.CHAR_PREM_ID` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.COUNTRY = CI_STATE_L.COUNTRY` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.STATE = CI_STATE_L.STATE` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L_1` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L_1.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.TREND_AREA_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.DESCR` | domain_join_inventory |
| `CI_SA` | `C1_USAGE` | `CI_SA.SA_ID = C1_USAGE.SA_ID` | canonical_chain:meter_ops |
| `CI_SA` | `CI_ACCT` | `CI_SA.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_ACCT_PER` | `CI_SA.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_BILL_CHG` | `CI_SA.SA_ID = CI_BILL_CHG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_BSEG` | `CI_SA.SA_ID = CI_BSEG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_CIS_DIVISION_L` | `CI_SA.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_FT` | `CI_SA.SA_ID = CI_FT.SA_ID` | canonical_chain:debt_mgmt |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.PROP_SA_STAT_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_1` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_2` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_2` | `CI_SA.SPECIAL_USAGE_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_3` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_3` | `CI_SA.STRT_RSN_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_4` | `CI_SA.SA_STATUS_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_LOOKUP_VAL_L_4` | `CI_SA.STOP_RSN_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `CI_SA` | `CI_NB_RULE_L` | `CI_SA.NB_RULE_CD = CI_NB_RULE_L.NB_RULE_CD` | domain_join_inventory |
| `CI_SA` | `CI_PREM` | `CI_SA.CHAR_PREM_ID = CI_PREM.PREM_ID` | domain_join_inventory |
| `CI_SA` | `CI_PROP_DCL_RSN_L` | `CI_SA.PROP_DCL_RSN_CD = CI_PROP_DCL_RSN_L.PROP_DCL_RSN_CD` | domain_join_inventory |
| `CI_SA` | `CI_SA_SP` | `CI_SA.SA_ID = CI_SA_SP.SA_ID` | canonical_chain:new_services |
| `CI_SA` | `CI_SA_TYPE` | `CI_SA.CIS_DIVISION = CI_SA_TYPE.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_SA_TYPE` | `CI_SA.SA_TYPE_CD = CI_SA_TYPE.SA_TYPE_CD` | domain_join_inventory |
| `CI_SA` | `CI_SA_TYPE_L` | `CI_SA.CIS_DIVISION = CI_SA_TYPE_L.CIS_DIVISION` | domain_join_inventory |

*(21 additional joins — see `fk_join_map_full.csv`)*

---

## Field Operations (`field_ops`)

### Canonical join chains

**field_activity_chain** — driver: `D1_ACTIVITY`, grain: activity (enrichment)
```
CI_SP → D1_ACTIVITY → D1_ACTIVITY_TYPE → D1_ACTIVITY_CHAR → D1_ACTIVITY_REL → D1_ACTIVITY_REL_OBJ → C1_REPRESENTATIVE → F1_TSK → F1_TSK_LOG
```
- `D1_ACTIVITY.D1_ACTIVITY_ID = D1_ACTIVITY_CHAR.D1_ACTIVITY_ID`
- `D1_ACTIVITY.ACTIVITY_TYPE_CD = D1_ACTIVITY_TYPE.ACTIVITY_TYPE_CD`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `C1_REPRESENTATIVE` | This will be used for the creation of Crew Based domain to measure Field Worker Performance (How many FAs can a crew complete within the Day) | `C1_REPRESENTATIVE_CD`, `BUS_OBJ_CD`, `BO_STATUS_CD`, `BO_STATUS_REASON_CD`, `C1_REPRESENTATIVE_TYPE_FLG`, `USER_ID` | 44 |
| `CI_SP` | Service Point - CCB | `SP_ID`, `SP_TYPE_CD`, `PREM_ID`, `SP_STATUS_FLG`, `INSTALL_DT`, `ABOLISH_DT` | 3305 |
| `D1_ACTIVITY` | Activity | `D1_ACTIVITY_ID`, `BUS_OBJ_CD`, `BO_STATUS_CD`, `ACTIVITY_TYPE_CD`, `START_DTTM`, `END_DTTM` | 214737 |
| `D1_ACTIVITY_CHAR` | Auto-added coverage table for D1_ACTIVITY_CHAR | `FA_PRIORITY_FLG`, `FA_INT_STATUS_FLG`, `THRD_PTY_REP_CD`, `CM_ML_SVC_AREA`, `D1_ACTIVITY`, `CHAR_TYPE_CD` | 460 |
| `D1_ACTIVITY_REL` | Auto-added coverage table for D1_ACTIVITY_REL | `ACTIVITY_REL_TYPE_FLG`, `D1_ACTIVITY_ID`, `REL_ACTIVITY_ID`, `VERSION` | 7641 |
| `D1_ACTIVITY_REL_OBJ` | Auto-added coverage table for D1_ACTIVITY_REL_OBJ | `ACTIVITY_REL_OBJ_TYPE_FLG`, `D1_ACTIVITY_ID`, `MAINT_OBJ_CD`, `PK_VALUE1`, `PK_VALUE2`, `PK_VALUE3` | 614841 |
| `D1_ACTIVITY_TYPE` |  | — | 23 |
| `D1_SP` | This table records information about Field Activities. It is useful for Clients as it allows them to easily access and extract FA-related data via reports. | `D1_SP`, `D1_SP_TYPE_CD`, `APPOINTMENT_WINDOW_START_DTTM`, `APPOINTMENT_WINDOW_END_DTTM`, `D1_TAKEN_BY`, `D1_TAKEN_DATE` | 3305 |
| `F1_TSK` |  | — | — |
| `F1_TSK_LOG` |  | — | — |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`C1_REPRESENTATIVE_L`, `CI_ACC_GRP_L`, `CI_LOOKUP_VAL_L`, `CI_NT_XID_L`, `CI_STATE_L`, `CI_TIME_ZONE_L`, `D1_ACTIVITY_TYPE_L`, `D1_MKT_L`, `D1_MSRMT_CYC_L`, `D1_MSRMT_CYC_RTE_L`, `D1_SP_TYPE_L`, `F1_BUS_OBJ_L`, `F1_BUS_OBJ_STATUS_L`, `F1_BUS_OBJ_STATUS_RSN_L`, `F1_EXT_LOOKUP_VAL_L`, `SC_USER`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `C1_REPRESENTATIVE` | `C1_REPRESENTATIVE_L` | `C1_REPRESENTATIVE.C1_REPRESENTATIVE_CD = C1_REPRESENTATIVE_L.C1_REPRESENTATIVE_CD` | domain_join_inventory |
| `C1_REPRESENTATIVE` | `CI_LOOKUP_VAL_L` | `C1_REPRESENTATIVE.C1_REPRESENTATIVE_TYPE_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `C1_REPRESENTATIVE` | `CI_NT_XID_L` | `C1_REPRESENTATIVE.NT_XID_CD = CI_NT_XID_L.NT_XID_CD` | domain_join_inventory |
| `C1_REPRESENTATIVE` | `D1_ACTIVITY_CHAR` | `C1_REPRESENTATIVE.C1_REPRESENTATIVE_CD = D1_ACTIVITY_CHAR.SRCH_CHAR_VAL` | domain_join_inventory |
| `C1_REPRESENTATIVE` | `F1_BUS_OBJ_L` | `C1_REPRESENTATIVE.BUS_OBJ_CD = F1_BUS_OBJ_L.BUS_OBJ_CD` | domain_join_inventory |
| `C1_REPRESENTATIVE` | `F1_BUS_OBJ_STATUS_L` | `C1_REPRESENTATIVE.BO_STATUS_CD = F1_BUS_OBJ_STATUS_L.BO_STATUS_CD` | domain_join_inventory |
| `C1_REPRESENTATIVE` | `F1_BUS_OBJ_STATUS_L` | `C1_REPRESENTATIVE.BUS_OBJ_CD = F1_BUS_OBJ_STATUS_L.BUS_OBJ_CD` | domain_join_inventory |
| `C1_REPRESENTATIVE` | `F1_BUS_OBJ_STATUS_RSN_L` | `C1_REPRESENTATIVE.BO_STATUS_REASON_CD = F1_BUS_OBJ_STATUS_RSN_L.BO_STATUS_REASON_CD` | domain_join_inventory |
| `C1_REPRESENTATIVE` | `SC_USER` | `C1_REPRESENTATIVE.USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_SP` | `CI_PREM` | `CI_SP.PREM_ID = CI_PREM.PREM_ID` | domain_join_inventory |
| `D1_ACTIVITY` | `D1_ACTIVITY_CHAR` | `D1_ACTIVITY.D1_ACTIVITY_ID = D1_ACTIVITY_CHAR.D1_ACTIVITY_ID` | canonical_chain:field_ops |
| `D1_ACTIVITY` | `D1_ACTIVITY_REL` | `D1_ACTIVITY.D1_ACTIVITY_ID = D1_ACTIVITY_REL.D1_ACTIVITY_ID` | domain_join_inventory |
| `D1_ACTIVITY` | `D1_ACTIVITY_REL_OBJ` | `D1_ACTIVITY.D1_ACTIVITY_ID = D1_ACTIVITY_REL_OBJ.D1_ACTIVITY_ID` | domain_join_inventory |
| `D1_ACTIVITY` | `D1_ACTIVITY_TYPE` | `D1_ACTIVITY.ACTIVITY_TYPE_CD = D1_ACTIVITY_TYPE.ACTIVITY_TYPE_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `D1_ACTIVITY_TYPE_L` | `D1_ACTIVITY.ACTIVITY_TYPE_CD = D1_ACTIVITY_TYPE_L.ACTIVITY_TYPE_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_BUS_OBJ_L` | `D1_ACTIVITY.BUS_OBJ_CD = F1_BUS_OBJ_L.BUS_OBJ_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_BUS_OBJ_L_1` | `D1_ACTIVITY.BUS_OBJ_CD = F1_BUS_OBJ_L_1.BUS_OBJ_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_BUS_OBJ_STATUS_L` | `D1_ACTIVITY.BO_STATUS_CD = F1_BUS_OBJ_STATUS_L.BO_STATUS_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_BUS_OBJ_STATUS_L` | `D1_ACTIVITY.BUS_OBJ_CD = F1_BUS_OBJ_STATUS_L.BUS_OBJ_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_BUS_OBJ_STATUS_L_1` | `D1_ACTIVITY.BO_STATUS_CD = F1_BUS_OBJ_STATUS_L_1.BO_STATUS_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_BUS_OBJ_STATUS_L_1` | `D1_ACTIVITY.BUS_OBJ_CD = F1_BUS_OBJ_STATUS_L_1.BUS_OBJ_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_BUS_OBJ_STATUS_RSN_L` | `D1_ACTIVITY.BO_STATUS_REASON_CD = F1_BUS_OBJ_STATUS_RSN_L.BO_STATUS_REASON_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_BUS_OBJ_STATUS_RSN_L_1` | `D1_ACTIVITY.BO_STATUS_REASON_CD = F1_BUS_OBJ_STATUS_RSN_L_1.BO_STATUS_REASON_CD` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_EXT_LOOKUP_VAL_L` | `D1_ACTIVITY.CANCEL_REASON = F1_EXT_LOOKUP_VAL_L.F1_EXT_LOOKUP_VALUE` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_EXT_LOOKUP_VAL_L_1` | `D1_ACTIVITY.FIELD_TASK_TYPE = F1_EXT_LOOKUP_VAL_L_1.F1_EXT_LOOKUP_VALUE` | domain_join_inventory |
| `D1_ACTIVITY` | `F1_EXT_LOOKUP_VAL_L_2` | `D1_ACTIVITY.RESCHEDULE_REASON = F1_EXT_LOOKUP_VAL_L_2.F1_EXT_LOOKUP_VALUE` | domain_join_inventory |
| `D1_ACTIVITY_CHAR` | `D1_ACTIVITY` | `D1_ACTIVITY_CHAR.D1_ACTIVITY_ID = D1_ACTIVITY.D1_ACTIVITY_ID` | domain_join_inventory |
| `D1_ACTIVITY_REL_OBJ` | `D1_SP` | `D1_ACTIVITY_REL_OBJ.PK_VALUE1 = D1_SP.D1_SP_ID` | domain_join_inventory |
| `D1_ACTIVITY_TYPE` | `D1_ACTIVITY_TYPE_L` | `D1_ACTIVITY_TYPE.ACTIVITY_TYPE_CD = D1_ACTIVITY_TYPE_L.ACTIVITY_TYPE_CD` | domain_join_inventory |
| `D1_SP` | `CI_ACC_GRP_L` | `D1_SP.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `D1_SP` | `CI_LOOKUP_VAL_L_1` | `D1_SP.DISCONN_LOC_FLG = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `D1_SP` | `CI_LOOKUP_VAL_L_2` | `D1_SP.SP_SRC_STAT_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `D1_SP` | `CI_LOOKUP_VAL_L_3` | `D1_SP.DISCONN_LOC_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `D1_SP` | `CI_LOOKUP_VAL_L_4` | `D1_SP.DISCONN_LOC_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `D1_SP` | `CI_LOOKUP_VAL_L_4` | `D1_SP.SP_SRC_STAT_FLG = CI_LOOKUP_VAL_L_4.FIELD_VALUE` | domain_join_inventory |
| `D1_SP` | `CI_LOOKUP_VAL_L_5` | `D1_SP.SP_SRC_STAT_FLG = CI_LOOKUP_VAL_L_5.FIELD_VALUE` | domain_join_inventory |
| `D1_SP` | `CI_STATE_L` | `D1_SP.COUNTRY = CI_STATE_L.COUNTRY` | domain_join_inventory |
| `D1_SP` | `CI_STATE_L` | `D1_SP.STATE = CI_STATE_L.STATE` | domain_join_inventory |
| `D1_SP` | `CI_TIME_ZONE_L` | `D1_SP.TIME_ZONE_CD = CI_TIME_ZONE_L.TIME_ZONE_CD` | domain_join_inventory |
| `D1_SP` | `D1_DIVISION_L` | `D1_SP.DIVISION_CD = D1_DIVISION_L.DIVISION_CD` | domain_join_inventory |
| `D1_SP` | `D1_MKT_L` | `D1_SP.MKT_CD = D1_MKT_L.MKT_CD` | domain_join_inventory |
| `D1_SP` | `D1_MSRMT_CYC_L` | `D1_SP.MSRMT_CYC_CD = D1_MSRMT_CYC_L.MSRMT_CYC_CD` | domain_join_inventory |
| `D1_SP` | `D1_MSRMT_CYC_RTE_L` | `D1_SP.MSRMT_CYC_CD = D1_MSRMT_CYC_RTE_L.MSRMT_CYC_CD` | domain_join_inventory |
| `D1_SP` | `D1_MSRMT_CYC_RTE_L` | `D1_SP.MSRMT_CYC_RTE_CD = D1_MSRMT_CYC_RTE_L.MSRMT_CYC_RTE_CD` | domain_join_inventory |
| `D1_SP` | `D1_SP_TYPE_L` | `D1_SP.D1_SP_TYPE_CD = D1_SP_TYPE_L.D1_SP_TYPE_CD` | domain_join_inventory |
| `D1_SP` | `F1_BUS_OBJ_L_1` | `D1_SP.BUS_OBJ_CD = F1_BUS_OBJ_L_1.BUS_OBJ_CD` | domain_join_inventory |
| `D1_SP` | `F1_BUS_OBJ_STATUS_L` | `D1_SP.BO_STATUS_CD = F1_BUS_OBJ_STATUS_L.BO_STATUS_CD` | domain_join_inventory |
| `D1_SP` | `F1_BUS_OBJ_STATUS_L` | `D1_SP.BUS_OBJ_CD = F1_BUS_OBJ_STATUS_L.BUS_OBJ_CD` | domain_join_inventory |
| `D1_SP` | `F1_BUS_OBJ_STATUS_L_1` | `D1_SP.BO_STATUS_CD = F1_BUS_OBJ_STATUS_L_1.BO_STATUS_CD` | domain_join_inventory |
| `D1_SP` | `F1_BUS_OBJ_STATUS_L_1` | `D1_SP.BUS_OBJ_CD = F1_BUS_OBJ_STATUS_L_1.BUS_OBJ_CD` | domain_join_inventory |
| `D1_SP` | `F1_BUS_OBJ_STATUS_RSN_L_1` | `D1_SP.BO_STATUS_REASON_CD = F1_BUS_OBJ_STATUS_RSN_L_1.BO_STATUS_REASON_CD` | domain_join_inventory |

---

## Common (`common`)

### Canonical join chains

**workflow_queue_chain** — driver: `CI_TD_ENTRY`, grain: todo_entry (enrichment)
```
CI_TD_ENTRY → CI_BATCH_INST → CI_PREM → CI_ACCT
```

**premise_chain** — driver: `CI_PREM`, grain: premise (enrichment)
```
CI_PREM → CI_PREM_CHAR → CI_PREM_GEO → CI_SP
```
- `CI_SP.PREM_ID = CI_PREM.PREM_ID`

### Fact and dimension tables

| Table | Description | Key fields | Est. rows |
|-------|-------------|------------|-----------|
| `CI_ACCT` | Account | `FULL` | 1049 |
| `CI_ACCT_PER` |  | — | 1045 |
| `CI_BATCH_CTRL` |  | — | 2766 |
| `CI_BATCH_INST` |  | — | 176134 |
| `CI_BATCH_RUN` |  | — | 170551 |
| `CI_BATCH_THD` |  | — | 176037 |
| `CI_BSEG` | Bill Segment | `BILL_CYC_CD`, `BILL_ID`, `BILL_SCNR_ID`, `BSEG_DATA_AREA`, `BSEG_ID`, `BSEG_STAT_FLG` | 168608 |
| `CI_BSEG_EXCP` | Auto-added coverage table for CI_BSEG_EXCP | `BSEG_ID`, `MESSAGE_CAT_NBR`, `MESSAGE_NBR`, `BSEG_EXCP_FLG`, `EXP_MSG`, `MESSAGE_PARM1` | 1629 |
| `CI_PER_NAME` |  | `JUST`, `FLATTEN` | 925 |
| `CI_PREM` | Premise | `ADDRESS1`, `ADDRESS1_UPR`, `ADDRESS2`, `ADDRESS3`, `ADDRESS4`, `CIS_DIVISION` | 1041 |
| `CI_PREM_CHAR` | Auto-added coverage table for CI_PREM_CHAR | `ADHOC_CHAR_VAL`, `CHAR_TYPE_CD`, `CHAR_VAL`, `CHAR_VAL_FK1`, `CHAR_VAL_FK2`, `CHAR_VAL_FK3` | 5830 |
| `CI_PREM_GEO` | Auto-added coverage table for CI_PREM_GEO | `GEO_TYPE_CD`, `GEO_VAL`, `PREM_ID`, `VERSION` | 1955 |
| `CI_SA` | SA (Service Agreement) | `ACCT_ID`, `ALLOW_EST_SW`, `BUS_ACTIVITY_DESC`, `CHAR_PREM_ID`, `CIAC_REVIEW_DT`, `CIS_DIVISION` | 6643 |
| `CI_SP` | Service Point - CCB | `SP_ID`, `SP_TYPE_CD`, `PREM_ID`, `SP_STATUS_FLG`, `INSTALL_DT`, `ABOLISH_DT` | 3305 |
| `CI_TD_DRLKEY` |  | — | 308693 |
| `CI_TD_DRLKEY_TY` |  | — | 358 |
| `CI_TD_ENTRY` |  | — | 308597 |
| `D1_CONTACT_IDENTIFIER` | Auto-added coverage table for D1_CONTACT_IDENTIFIER | `CONTACT_ID`, `CONTACT_ID_TYPE_FLG`, `ID_VALUE`, `VERSION` | 976 |
| `D1_DVC_CFG` |  | `DEVICE_CONFIG_ID`, `DEVICE_CONFIG_TYPE_CD`, `EFF_DTTM`, `BO_STATUS_CD`, `BO_DATA_AREA`, `BO_STATUS_REASON_CD` | 2466 |
| `D1_INIT_MSRMT_DATA` | Initial measurement data (IMD) is the term for measurement data in its initial (or raw) form. This is received from an external system or user created or system estimated in C2M. Once it's processed it will be stored as measurement(D1_MSRMT) or the IMD will be in Exception state depending on the VEE Rules setup. It is useful for Clients as it allows them to review the information of the expected number of reads uploaded to the system and how many are processed at a given period o | `BO_STATUS_CD`, `BO_STATUS_REASON_CD`, `BUS_OBJ_CD`, `CRE_DTTM`, `D1_FROM_DTTM`, `D1_TO_DTTM` | 213380 |
| `D1_INSTALL_EVT` | Install Event | `INSTALL_EVT_ID`, `BO_STATUS_CD`, `D1_INSTALL_DTTM`, `D1_REMOVAL_DTTM`, `ARM_STAT_FLG`, `BO_DATA_AREA` | 2426 |
| `D1_MEASR_COMP` | Measuring components are single points for which data will be received and stored in the system. Measuring components can be associated to a device or not (these are virtual or stand-alone). This is helpful for the Clients as it allows them to retrieve the Measuring Components that's either related to a SP or not used. | `MEASR_COMP_ID`, `MEASR_COMP_TYPE_CD`, `LATEST_MSRMT_DTTM`, `MOST_RECENT_NON_EST_MSRMT_DTTM`, `ACCESS_GRP_CD`, `ADJ_LATEST_MSRMT_DTTM` | 7074 |
| `D1_SP` | This table records information about Field Activities. It is useful for Clients as it allows them to easily access and extract FA-related data via reports. | `D1_SP`, `D1_SP_TYPE_CD`, `APPOINTMENT_WINDOW_START_DTTM`, `APPOINTMENT_WINDOW_END_DTTM`, `D1_TAKEN_BY`, `D1_TAKEN_DATE` | 3305 |
| `D1_USAGE` | Usage Transactions are records of bill determinant calculations for a Usage Subscription. This is useful to the Client as it allows them to retrieve the Bill information to the usage and measurement | `BO_STATUS_CD`, `BO_STATUS_REASON_CD`, `BUS_OBJ_CD`, `COMMENTS`, `CRE_DTTM`, `D1_SPR_CD` | 27704 |
| `D1_USAGE_EXCP` | Auto-added coverage table for D1_USAGE_EXCP | `BO_DATA_AREA`, `BO_STATUS_CD`, `BO_STATUS_REASON_CD`, `BUS_OBJ_CD`, `CRE_DTTM`, `D1_USAGE_ID` | 140339 |
| `D1_US_CONTACT` | Auto-added coverage table for D1_US_CONTACT | `CONTACT_ID`, `US_CNTCT_REL_FLG`, `US_ID`, `VERSION` | 4295 |
| `D1_US_SP` | Auto-added coverage table for D1_US_SP | `BO_DATA_AREA`, `D1_SP_ID`, `D1_STOP_DTTM`, `D1_USAGE_FLG`, `OVRD_START_DTTM`, `OVRD_STOP_DTTM` | 4269 |
| `D1_VEE_EXCP` | Auto-added coverage table for D1_VEE_EXCP | `BO_STATUS_CD` | 541797 |

### Lookup / label tables (`LANGUAGE_CD = 'ENG'`)

`CI_ACCT_MGMT_GR_L`, `CI_ACC_GRP_L`, `CI_BATCH_CTRL_L`, `CI_BILL_CYC_L`, `CI_BUD_PLAN_L`, `CI_COLL_CL_L`, `CI_CUST_CL_L`, `CI_LOOKUP_VAL_L`, `CI_MR_INSTR_L`, `CI_MR_WARN_L`, `CI_MSG_L`, `CI_PREM_TYPE_L`, `CI_ROLE_L`, `CI_SA_TYPE_L`, `CI_SP_TYPE_L`, `CI_STATE_L`, `CI_TD_TYPE_L`, `CI_TIME_ZONE_L`, `CI_TREND_AREA_L`, `D1_DIVISION_L`, `D1_EXCP_TYPE_L`, `D1_MKT_L`, `D1_MSRMT_CYC_L`, `D1_MSRMT_CYC_RTE_L`, `D1_SP_TYPE_L`, `D1_USAGE_EXCP_TYPE_L`, `D1_USG_GRP_L`, `D1_USG_RULE_L`, `D1_VEE_GRP_L`, `D1_VEE_RULE_L`, `F1_BUS_OBJ_L`, `F1_BUS_OBJ_STATUS_L`, `SC_USER`

### Join links (child → parent)

| Child | Parent | Join SQL | Source |
|-------|--------|----------|--------|
| `CI_ACCT` | `CI_ACCT_ALERT` | `CI_ACCT.ACCT_ID = CI_ACCT_ALERT.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_MGMT_GR_L` | `CI_ACCT.ACCT_MGMT_GRP_CD = CI_ACCT_MGMT_GR_L.ACCT_MGMT_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_ACCT_PER` | `CI_ACCT.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `CI_ACC_GRP_L` | `CI_ACCT.ACCESS_GRP_CD = CI_ACC_GRP_L.ACCESS_GRP_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BILL_CYC_L_1` | `CI_ACCT.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_BUD_PLAN_L` | `CI_ACCT.BUD_PLAN_CD = CI_BUD_PLAN_L.BUD_PLAN_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CIS_DIVISION_L` | `CI_ACCT.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_ACCT` | `CI_COLL_CL_L` | `CI_ACCT.COLL_CL_CD = CI_COLL_CL_L.COLL_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_CUST_CL_L` | `CI_ACCT.CUST_CL_CD = CI_CUST_CL_L.CUST_CL_CD` | domain_join_inventory |
| `CI_ACCT` | `CI_SA` | `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID` | domain_join_inventory |
| `CI_ACCT` | `SC_USER` | `CI_ACCT.BILL_PRT_INTERCEPT = SC_USER.USER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `C1_PER_CONTDET` | `CI_ACCT_PER.PER_ID = C1_PER_CONTDET.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER` | `CI_ACCT_PER.PER_ID = CI_PER.PER_ID` | domain_join_inventory |
| `CI_ACCT_PER` | `CI_PER_NAME` | `CI_ACCT_PER.PER_ID = CI_PER_NAME.PER_ID` | domain_join_inventory |
| `CI_BATCH_INST` | `CI_BATCH_CTRL` | `CI_BATCH_INST.BATCH_CD = CI_BATCH_CTRL.BATCH_CD` | domain_join_inventory |
| `CI_BATCH_INST` | `CI_BATCH_CTRL_L` | `CI_BATCH_INST.BATCH_CD = CI_BATCH_CTRL_L.BATCH_CD` | domain_join_inventory |
| `CI_BATCH_INST` | `CI_BATCH_RUN` | `CI_BATCH_INST.BATCH_CD = CI_BATCH_RUN.BATCH_CD` | domain_join_inventory |
| `CI_BATCH_INST` | `CI_BATCH_RUN` | `CI_BATCH_INST.BATCH_NBR = CI_BATCH_RUN.BATCH_NBR` | domain_join_inventory |
| `CI_BATCH_INST` | `CI_BATCH_RUN` | `CI_BATCH_INST.BATCH_RERUN_NBR = CI_BATCH_RUN.BATCH_RERUN_NBR` | domain_join_inventory |
| `CI_BATCH_INST` | `CI_BATCH_THD` | `CI_BATCH_INST.BATCH_CD = CI_BATCH_THD.BATCH_CD` | domain_join_inventory |
| `CI_BATCH_INST` | `CI_BATCH_THD` | `CI_BATCH_INST.BATCH_NBR = CI_BATCH_THD.BATCH_NBR` | domain_join_inventory |
| `CI_BATCH_INST` | `CI_BATCH_THD` | `CI_BATCH_INST.BATCH_RERUN_NBR = CI_BATCH_THD.BATCH_RERUN_NBR` | domain_join_inventory |
| `CI_BATCH_RUN` | `CI_LOOKUP_VAL_L` | `CI_BATCH_RUN.RUN_STATUS = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_BATCH_THD` | `CI_LOOKUP_VAL_L_1` | `CI_BATCH_THD.THREAD_STATUS = CI_LOOKUP_VAL_L_1.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL` | `CI_BSEG.BILL_ID = CI_BILL.BILL_ID` | canonical_chain:billing |
| `CI_BSEG` | `CI_BILL_CAN_RSN_L` | `CI_BSEG.CAN_RSN_CD = CI_BILL_CAN_RSN_L.CAN_RSN_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL_CYC_L_1` | `CI_BSEG.BILL_CYC_CD = CI_BILL_CYC_L_1.BILL_CYC_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BILL_CYC_L_2` | `CI_BSEG.BILL_CYC_CD = CI_BILL_CYC_L_2.BILL_CYC_CD` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_CALC` | `CI_BSEG.BSEG_ID = CI_BSEG_CALC.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_READ` | `CI_BSEG.BSEG_ID = CI_BSEG_READ.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_BSEG_SQ` | `CI_BSEG.BSEG_ID = CI_BSEG_SQ.BSEG_ID` | domain_join_inventory |
| `CI_BSEG` | `CI_LOOKUP_VAL_L_2` | `CI_BSEG.BSEG_STAT_FLG = CI_LOOKUP_VAL_L_2.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_LOOKUP_VAL_L_3` | `CI_BSEG.BSEG_STAT_FLG = CI_LOOKUP_VAL_L_3.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG` | `CI_SA` | `CI_BSEG.SA_ID = CI_SA.SA_ID` | domain_join_inventory |
| `CI_BSEG` | `FT_GL_SUMMARY` | `CI_BSEG.BSEG_ID = FT_GL_SUMMARY.SIBLING_ID` | domain_join_inventory |
| `CI_BSEG_EXCP` | `CI_BSEG` | `CI_BSEG_EXCP.BSEG_ID = CI_BSEG.BSEG_ID` | domain_join_inventory |
| `CI_BSEG_EXCP` | `CI_LOOKUP_VAL_L` | `CI_BSEG_EXCP.BSEG_EXCP_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |
| `CI_BSEG_EXCP` | `CI_TD_DRLKEY` | `CI_BSEG_EXCP.BSEG_ID = CI_TD_DRLKEY.KEY_VALUE` | domain_join_inventory |
| `CI_BSEG_EXCP` | `SC_USER` | `CI_BSEG_EXCP.USER_ID = SC_USER.USER_ID` | domain_join_inventory |
| `CI_BSEG_EXCP` | `SC_USER_1` | `CI_BSEG_EXCP.REVIEW_USER_ID = SC_USER_1.USER_ID` | domain_join_inventory |
| `CI_PREM` | `CI_CIS_DIVISION_L` | `CI_PREM.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_PREM` | `CI_MR_INSTR_L` | `CI_PREM.MR_INSTR_CD = CI_MR_INSTR_L.MR_INSTR_CD` | domain_join_inventory |
| `CI_PREM` | `CI_MR_WARN_L` | `CI_PREM.MR_WARN_CD = CI_MR_WARN_L.MR_WARN_CD` | domain_join_inventory |
| `CI_PREM` | `CI_PREM_TYPE_L` | `CI_PREM.PREM_TYPE_CD = CI_PREM_TYPE_L.PREM_TYPE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_SA` | `CI_PREM.PREM_ID = CI_SA.CHAR_PREM_ID` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.COUNTRY = CI_STATE_L.COUNTRY` | domain_join_inventory |
| `CI_PREM` | `CI_STATE_L` | `CI_PREM.STATE = CI_STATE_L.STATE` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TIME_ZONE_L_1` | `CI_PREM.TIME_ZONE_CD = CI_TIME_ZONE_L_1.TIME_ZONE_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.TREND_AREA_CD` | domain_join_inventory |
| `CI_PREM` | `CI_TREND_AREA_L` | `CI_PREM.TREND_AREA_CD = CI_TREND_AREA_L.DESCR` | domain_join_inventory |
| `CI_SA` | `C1_USAGE` | `CI_SA.SA_ID = C1_USAGE.SA_ID` | canonical_chain:meter_ops |
| `CI_SA` | `CI_ACCT` | `CI_SA.ACCT_ID = CI_ACCT.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_ACCT_PER` | `CI_SA.ACCT_ID = CI_ACCT_PER.ACCT_ID` | domain_join_inventory |
| `CI_SA` | `CI_BILL_CHG` | `CI_SA.SA_ID = CI_BILL_CHG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_BSEG` | `CI_SA.SA_ID = CI_BSEG.SA_ID` | domain_join_inventory |
| `CI_SA` | `CI_CIS_DIVISION_L` | `CI_SA.CIS_DIVISION = CI_CIS_DIVISION_L.CIS_DIVISION` | domain_join_inventory |
| `CI_SA` | `CI_FT` | `CI_SA.SA_ID = CI_FT.SA_ID` | canonical_chain:debt_mgmt |
| `CI_SA` | `CI_LOOKUP_VAL_L` | `CI_SA.PROP_SA_STAT_FLG = CI_LOOKUP_VAL_L.FIELD_VALUE` | domain_join_inventory |

*(105 additional joins — see `fk_join_map_full.csv`)*

---

## Hub tables (appear in multiple workstreams)

| Table | Workstreams | Role |
|-------|-------------|------|
| `CI_LOOKUP_VAL_L` | billing, cashiering, common, customer_ops, debt_mgmt, field_ops, finance, meter_ops, new_services | Generic code/description lookup |
| `CI_ACCT` | billing, cashiering, common, customer_ops, debt_mgmt, finance, meter_ops, new_services | Customer account — financial umbrella |
| `CI_ACCT_PER` | billing, cashiering, common, customer_ops, debt_mgmt, finance, meter_ops, new_services |  |
| `CI_PER_NAME` | billing, cashiering, common, customer_ops, debt_mgmt, finance, meter_ops, new_services | Person name (join via CI_ACCT_PER) |
| `CI_SA` | billing, common, customer_ops, debt_mgmt, finance, meter_ops, new_services | Service agreement — contract under account |
| `SC_USER` | billing, cashiering, common, customer_ops, field_ops, finance, new_services | Application user reference |
| `CI_STATE_L` | common, customer_ops, debt_mgmt, field_ops, finance, meter_ops, new_services |  |
| `CI_TIME_ZONE_L` | common, customer_ops, debt_mgmt, field_ops, finance, meter_ops, new_services |  |
| `CI_BILL_CYC_L` | billing, common, customer_ops, debt_mgmt, finance, new_services |  |
| `CI_BUD_PLAN_L` | billing, common, customer_ops, debt_mgmt, finance, new_services |  |
| `CI_COLL_CL_L` | billing, common, customer_ops, debt_mgmt, finance, new_services |  |
| `CI_CUST_CL_L` | billing, common, customer_ops, debt_mgmt, finance, new_services |  |
| `CI_MR_INSTR_L` | common, customer_ops, debt_mgmt, finance, meter_ops, new_services |  |
| `CI_MR_WARN_L` | common, customer_ops, debt_mgmt, finance, meter_ops, new_services |  |
| `CI_PREM` | common, customer_ops, debt_mgmt, finance, meter_ops, new_services | Premise — physical site |
| `CI_PREM_TYPE_L` | common, customer_ops, debt_mgmt, finance, meter_ops, new_services |  |
| `CI_TREND_AREA_L` | common, customer_ops, debt_mgmt, finance, meter_ops, new_services |  |
| `CI_ACCT_MGMT_GR_L` | billing, common, customer_ops, debt_mgmt, finance |  |
| `CI_SA_TYPE_L` | common, customer_ops, debt_mgmt, finance, new_services |  |
| `CI_BSEG` | billing, common, customer_ops, finance | Bill segment — billing-period fact |
| `CI_ACC_GRP_L` | common, customer_ops, field_ops, meter_ops |  |
| `CI_SP` | common, field_ops, meter_ops, new_services | Service point — delivery location |

---

## Row multiplication risks

| Risk area | Cause | Mitigation |
|-----------|-------|------------|
| Billing | Multiple `CI_BSEG_*` children at once | Aggregate per `BSEG_ID` first, or use snapshot |
| Usage | `D1_USAGE_SCALAR_DTL` / `D1_USAGE_PERIOD_SQ` | Aggregate to `D1_USAGE_ID` before wide joins |
| Finance | `CI_FT_GL` multiple GL lines per FT | Aggregate per `FT_ID` before account rollups |
| Payments | `CI_PAY_TNDR` multiple tenders per payment | Aggregate per `PAY_ID` |
| Field ops | `D1_ACTIVITY_REL_OBJ` multiple related objects | One row per activity — aggregate rel tables |
| Device history | Multiple `D1_INSTALL_EVT` per SP over time | Filter effective date / status window |

---

## Companion references

- `docs/cisadm_relationship_map.md` — business chain narratives
- `knowledge_base/c2m_cisadm/workstream_physical_join_paths.md` — SQL examples per workstream
- `docs/cisadm_sql_cheat_sheet.md` — starter patterns
- `docs/cisadm_workstream_vocabulary_guide.md` — business vocabulary
- `docs/assistant_skills/cisadm_sql_prompt_guide.md` — prompt guidance for agents
