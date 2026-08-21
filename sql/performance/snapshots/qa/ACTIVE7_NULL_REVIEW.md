# Active 8 Snapshot Null Review

Historical read-only audit originally run on CityCorp (reference) and Odessa DEV
(target).

Current rule moving forward:

- Use Ellensburg as the development/reference database.
- Validate only `CISADM` source and snapshot objects.
- Treat the active QA set as the original 7 governed snapshots plus
  `CISADM.CMS_SA_SNAPSHOT`.
- Do not use `CISREAD` synonyms or legacy schemas for standard snapshot
  integrity checks.

## Rule used

- `all null`: null_pct = 100
- `mostly null`: null_pct >= 95
- `actionable`: Odessa >=95 but CityCorp <95 (likely mapping/load issue, not naturally sparse)

## FT_RPT_CURR

- Odessa rows: 7160281
- CityCorp rows: 6040686
- Actionable columns: 6

| Column | Odessa null % | CityCorp null % |
|---|---:|---:|
| `ADJ_AMT` | 95.88 | 94.6 |
| `ADJ_ID` | 95.88 | 94.6 |
| `ADJ_STATUS_DESC` | 95.88 | 94.6 |
| `ADJ_STATUS_FLG` | 95.88 | 94.6 |
| `ADJ_TYPE_CD` | 95.88 | 94.6 |
| `ADJ_TYPE_DESC` | 95.88 | 94.6 |

## FT_GL_DISTRIBUTION_RPT_CURR

- Odessa rows: 55
- CityCorp rows: 5784321
- Actionable columns: 23

| Column | Odessa null % | CityCorp null % |
|---|---:|---:|
| `BALANCING_STAT_DESC` | 100.0 | 1.21 |
| `BALANCING_STAT_FLG` | 100.0 | 1.21 |
| `BATCH_CD` | 100.0 | 0.0 |
| `BATCH_NBR` | 100.0 | 0.0 |
| `BCG_CRE_DTTM` | 100.0 | 1.21 |
| `BCG_CUR_AMT` | 100.0 | 1.21 |
| `BCG_CUR_BAL` | 100.0 | 1.21 |
| `BCG_TOT_AMT` | 100.0 | 1.21 |
| `BCG_TOT_BAL` | 100.0 | 1.21 |
| `BSEG_BILL_CYC_DESC` | 100.0 | 37.24 |
| `XFER_TO_GL_DT` | 100.0 | 0.0 |
| `ADJ_AMT` | 96.36 | 94.85 |
| `ADJ_CAN_RSN_CD` | 96.36 | 94.85 |
| `ADJ_ID` | 96.36 | 94.85 |
| `ADJ_STATUS_DESC` | 96.36 | 94.85 |
| `ADJ_STATUS_FLG` | 96.36 | 94.85 |
| `ADJ_TYPE_CD` | 96.36 | 94.85 |
| `ADJ_TYPE_DESC` | 96.36 | 94.85 |
| `APPR_REQ_ID` | 96.36 | 94.85 |
| `BASE_AMT` | 96.36 | 94.85 |
| `BEHALF_SA_ID` | 96.36 | 94.85 |
| `BILL_CYC_DESC` | 96.36 | 0.12 |
| `XFER_ADJ_ID` | 96.36 | 94.85 |

## BSEG_BILLED_USAGE_RPT_CURR

- Odessa rows: 5047837
- CityCorp rows: 2911737
- Actionable columns: 9

| Column | Odessa null % | CityCorp null % |
|---|---:|---:|
| `BILL_BILL_CYC_DESC` | 100.0 | 67.27 |
| `BSEG_BILL_CYC_DESC` | 100.0 | 67.74 |
| `BUD_PLAN_DESC` | 100.0 | 12.0 |
| `MAX_END_READ_DTTM` | 100.0 | 79.51 |
| `MIN_START_READ_DTTM` | 100.0 | 79.51 |
| `READ_LINE_COUNT` | 100.0 | 79.51 |
| `TOTAL_FINAL_REG_QTY` | 100.0 | 79.51 |
| `TOTAL_MSR_QTY` | 100.0 | 79.51 |
| `WIN_START_DT` | 100.0 | 67.74 |

## BSEG_SQ_USAGE_RPT_CURR

- Odessa rows: 1694938
- CityCorp rows: 7158300
- Actionable columns: 4

| Column | Odessa null % | CityCorp null % |
|---|---:|---:|
| `BILL_BILL_CYC_DESC` | 100.0 | 16.39 |
| `BSEG_BILL_CYC_DESC` | 100.0 | 17.97 |
| `BUD_PLAN_DESC` | 100.0 | 15.89 |
| `WIN_START_DT` | 100.0 | 17.97 |

## D1_USAGE_RPT_CURR

- Odessa rows: 38
- CityCorp rows: 629606
- Actionable columns: 3

| Column | Odessa null % | CityCorp null % |
|---|---:|---:|
| `BSEG_BILL_CYC_DESC` | 100.0 | 7.68 |
| `BUD_PLAN_DESC` | 100.0 | 24.18 |
| `C1_BILL_CYC_DESC` | 100.0 | 7.68 |

## D1_USAGE_SCALAR_DTL_RPT_CURR

- Odessa rows: 192
- CityCorp rows: 622220
- Actionable columns: 2

| Column | Odessa null % | CityCorp null % |
|---|---:|---:|
| `BUD_PLAN_DESC` | 100.0 | 20.62 |
| `C1_BILL_CYC_DESC` | 100.0 | 3.73 |

## D1_MSRMT_RPT_CURR

- Odessa rows: 1788897
- CityCorp rows: 1236065
- Actionable columns: 24

| Column | Odessa null % | CityCorp null % |
|---|---:|---:|
| `IMD_EXT_ID` | 100.0 | 74.14 |
| `MOST_RECENT_MSRMT_READING_COND` | 100.0 | 2.97 |
| `MOST_RECENT_MSRMT_READING_COND_DESC` | 100.0 | 3.05 |
| `MSRMT_CYC_RTE_DESC` | 100.0 | 3.51 |
| `READING_COND_DESC` | 100.0 | 30.28 |
| `DATA_SRC_FLG` | 99.99 | 72.17 |
| `IMD_BO_STATUS_CD` | 99.99 | 72.17 |
| `IMD_BO_STATUS_DESC` | 99.99 | 72.17 |
| `IMD_BO_STATUS_REASON_CD` | 99.99 | 72.17 |
| `IMD_BUS_OBJ_CD` | 99.99 | 72.17 |
| `IMD_BUS_OBJ_DESC` | 99.99 | 72.17 |
| `IMD_CRE_DTTM` | 99.99 | 72.17 |
| `IMD_FROM_DTTM` | 99.99 | 72.22 |
| `IMD_LAST_UPDATE_DTTM` | 99.99 | 72.17 |
| `IMD_STATUS_UPD_DTTM` | 99.99 | 72.17 |
| `IMD_TIME_ZONE_CD` | 99.99 | 72.17 |
| `IMD_TIME_ZONE_DESC` | 99.99 | 72.17 |
| `IMD_TO_DTTM` | 99.99 | 72.17 |
| `INIT_MSRMT_DATA_ID` | 99.99 | 72.17 |
| `RETENTION_PERIOD` | 99.99 | 72.17 |
| `ADJ_LATEST_MSRMT_DTTM` | 99.92 | 3.14 |
| `LATEST_MSRMT_DTTM` | 99.91 | 0.69 |
| `MOST_RECENT_MSRMT_DTTM` | 99.91 | 2.45 |
| `MOST_RECENT_NON_EST_MSRMT_DTTM` | 99.91 | 2.45 |

## Mapping changes applied

- Root cause refinement: Odessa often stores cycle codes as blank-padded strings instead of true `NULL`, so fallback logic must use trimmed nullification first.
- Billed usage snapshots:
  - `bill_bill_cyc_cd = COALESCE(NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))`
  - `bseg_bill_cyc_cd = COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bill.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))`
- `FT_GL_DISTRIBUTION_RPT_CURR`: `bseg_bill_cyc_cd = COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))`
- `D1_USAGE_RPT_CURR`:
  - `c1_bill_cyc_cd = COALESCE(NULLIF(TRIM(bridge.c1_bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))`
  - `bseg_bill_cyc_cd = COALESCE(NULLIF(TRIM(bseg.bill_cyc_cd), ''), NULLIF(TRIM(bridge.c1_bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))`
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `c1_bill_cyc_cd = COALESCE(NULLIF(TRIM(bridge.c1_bill_cyc_cd), ''), NULLIF(TRIM(acct.bill_cyc_cd), ''))`

## Odessa DEV post-refresh result

- `BSEG_BILLED_USAGE_RPT_CURR`: `bill_bill_cyc_cd` populated on `5,061,911 / 5,061,916` rows after rerun
- `BSEG_SQ_USAGE_RPT_CURR`: `bill_bill_cyc_cd` populated on `1,699,798 / 1,699,801` rows after rerun
- `FT_GL_DISTRIBUTION_RPT_CURR`: bill-cycle coverage improved from `0` to `2 / 57` rows
- `D1_USAGE_RPT_CURR`: cycle coverage improved from `0` to `1 / 38` rows
- `D1_USAGE_SCALAR_DTL_RPT_CURR`: `c1_bill_cyc_cd` populated on `41 / 192` rows after rerun

## Remaining mostly/all-null columns

Many remaining null-heavy columns in Odessa appear to reflect source sparsity/conversion scope (not mapping):
- `D1_USAGE*` low bridge population in Odessa
- `D1_MSRMT_RPT_CURR` IMD fields mostly absent in Odessa source
- FT/adjustment/pay-seg detail fields are naturally sparse by FT type
