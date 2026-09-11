# New Service Pipeline Snapshot

This folder is for the governed new-services pipeline snapshot built from `CISADM.CI_SA` with account, customer, premise, and lookup context aligned to the Standard Offering `New_Services___Domain` join graph.

## Purpose

`CISADM.NEW_SERVICE_PIPELINE_RPT_CURR` is the standardized new-services snapshot for start-service pipeline reporting.

It is designed for ad hoc reporting where users need one safe row per service agreement with:
- pending and recently started service-agreement status
- proposal / enrollment context (`PROP_SA_STAT_FLG`, `ENRL_ID`, decline reason)
- account and primary-customer context
- premise address and service-location attributes
- SA type and service-type descriptions
- lightweight pipeline-aging indicators

## Grain

One row per `SA_ID`.

Natural key:
- `SA_ID`

## Why this grain was chosen

The legacy `New_Services___Domain` drives from `CI_SA` and enriches each service agreement with account, customer, premise, and lookup context.

Keeping `SA_ID` as the snapshot grain preserves:
- one row per pending or recently started service agreement
- safe distinct counts of service agreements and premises
- parity with Standard Offering new-services Ad Hoc and pending-SA views

## Population filters

The snapshot intentionally includes only service agreements relevant to the new/start-service pipeline.

### `SA_STATUS_FLG`

| Code | Meaning | Snapshot rule |
| --- | --- | --- |
| `10` | Pending | Always include. These are the primary pipeline backlog rows. |
| `20` | Active | Include recently started service agreements. The operational refresh scopes active rows by `START_DT` / `END_DT` window. |

Normalized predicate used in refresh SQL:

```sql
NULLIF(TRIM(sa.sa_status_flg), '') IN ('10', '20')
```

### `PROP_SA_STAT_FLG`

Proposal status is used to keep enrollment-stage service agreements while excluding terminal proposal outcomes.

| Code | Typical meaning | Snapshot rule |
| --- | --- | --- |
| `NULL` / blank | No proposal context | Include when `SA_STATUS_FLG` is in the pipeline set above. |
| `10` | Pending Start | Include. Matches Standard Offering pending-service-agreement views. |
| `20` | Started | Include. Proposal converted to live service. |
| `30` | Declined | Exclude. |
| `40` | Canceled | Exclude. |

Normalized predicate used in refresh SQL:

```sql
(
    NULLIF(TRIM(sa.prop_sa_stat_flg), '') IS NULL
    OR NULLIF(TRIM(sa.prop_sa_stat_flg), '') IN ('10', '20')
)
```

Validate exact lookup labels and any client-specific proposal codes in `CI_LOOKUP_VAL_L` where `FIELD_NAME = 'PROP_SA_STAT_FLG'` before production rollout.

### Rolling refresh window

The operational procedure keeps a `6-month` rolling scope on service-agreement dates:
- all pending rows (`SA_STATUS_FLG = '10'`) are always retained
- active rows (`SA_STATUS_FLG = '20'`) are retained when `START_DT` or `END_DT` falls inside the window

## Driving tables

- `CISADM.CI_SA`
- `CISADM.CI_SA_TYPE`
- `CISADM.CI_ACCT`
- `CISADM.CI_ACCT_PER`
- `CISADM.CI_PER_NAME`
- `CISADM.CI_PREM`

Lookup and presentation tables:
- `CISADM.CI_SA_TYPE_L`
- `CISADM.CI_SVC_TYPE_L`
- `CISADM.CI_LOOKUP_VAL_L`
- `CISADM.CI_CIS_DIVISION_L`
- `CISADM.CI_BILL_CYC_L`
- `CISADM.CI_COLL_CL_L`
- `CISADM.CI_CUST_CL_L`
- `CISADM.CI_ACCT_MGMT_GR_L`
- `CISADM.CI_BUD_PLAN_L`
- `CISADM.CI_NB_RULE_L`
- `CISADM.CI_PROP_DCL_RSN_L`
- `CISADM.CI_SS_OPT_L`
- `CISADM.CI_SIC_L`
- `CISADM.CI_PREM_TYPE_L`
- `CISADM.CI_MR_INSTR_L`
- `CISADM.CI_MR_WARN_L`
- `CISADM.CI_TREND_AREA_L`
- `CISADM.CI_STATE_L`
- `CISADM.CI_TIME_ZONE_L`
- `CISADM.SC_USER`

## What is included

- SA header fields and key lifecycle dates (`START_DT`, `END_DT`, `EXPIRE_DT`, `ENRL_ID`, `CRE_DTTM`)
- proposal status, decline reason, and start/stop reason context
- account class, bill cycle, and account-management descriptions
- primary customer name
- premise address, postal, and location descriptions
- derived pipeline-aging fields:
  - `DAYS_SINCE_CREATED`
  - `DAYS_UNTIL_START`
  - `STALE_PENDING_SW` (`SA_STATUS_FLG = '10'` and `START_DT` in the past)

## What is intentionally excluded

- row-per-service-point detail
- service-point characteristic detail
- debt truth and arrears balances as required fields

Optional client-specific balance overlay:
- `CM_FT_BAL` is joined only as an optional `LEFT JOIN` when the client view exists. Do not treat `FT_BAL_CUR_AMT` / `FT_BAL_TOT_AMT` as governed cross-client measures.

## Key design rules

- This is a pipeline-workflow snapshot, not a debt or billing snapshot.
- `STALE_PENDING_SW` supports operations SLA views; it mirrors the SmartCity stale-pending service-agreement check.
- Premise is `LEFT JOIN`ed so pending SAs without a populated `CHAR_PREM_ID` remain visible.
- Lookup descriptions resolve from delivered `_L` tables with `LANGUAGE_CD = 'ENG'`.

## Recommended use

- pending start-service backlog monitoring
- stale pending service-agreement detection
- recently started service counts by SA type, division, or geography
- enrollment / order-id trace views

## Do not use for

- active-account-only operational reporting across all live SAs
- billing completeness or billed-usage analysis
- account-level debt exposure

Use governed finance, billed-usage, or debt-management snapshots for those subjects.

## Workflow

1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. Run the one-time baseline load with `02a_full_history_refresh_procedure.sql`.
3. Deploy the operational rolling refresh with `02_refresh_snapshot_procedure.sql`.
4. Validate row safety and description coverage with `04_validation_queries.sql`.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`
