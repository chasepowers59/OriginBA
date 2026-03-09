# DBA Index Request: Domain Query Performance

## Purpose
Request DBA-created indexes to improve runtime for high-volume domain SQL used by:
- usage/billing financial bridge
- billed usage consumption
- billed revenue by rate component
- billed revenue tax
- billing requirements expected-vs-actual
- write-off trend/effectiveness
- unbilled revenue snapshot refresh

## Evidence (from current benchmark run)
`sql/performance/billed_revenue/domain_core_benchmark_30d.sql` returned very low row counts but high elapsed time:
- usage bridge cases: ~38s for 13 rows
- rate/tax cases: ~37s for 15 rows
- billed usage count-only: ~30s for 13 rows

This pattern indicates expensive scans/joins on large fact paths, not output size.

## What Already Exists (do not duplicate)
Strong existing coverage already exists for:
- `CI_ACCT(ACCT_ID)`, `CI_BSEG(BSEG_ID)`, `CI_BSEG(BILL_ID)`, `CI_BSEG(SA_ID)`, `CI_SA(SA_ID)`
- `CI_LOOKUP_VAL_L(FIELD_NAME, FIELD_VALUE, LANGUAGE_CD)`
- `CI_BSEG_CALC(BSEG_ID, HEADER_SEQ)`
- `CI_BSEG_CALC_LN(BSEG_ID, HEADER_SEQ, SEQNO)`
- `CI_RC(RS_CD, EFFDT, RC_SEQ)` and `CI_RC_L(RS_CD, EFFDT, RC_SEQ, LANGUAGE_CD)`

## Requested New Indexes (priority order)

### P1 (highest impact)
1. `CI_BSEG_CALC_LN` for rate-component key matching
```sql
CREATE INDEX CISADM.XORG_BCLN_BSEG_UOM_TOU_SQI
    ON CISADM.CI_BSEG_CALC_LN (BSEG_ID, UOM_CD, TOU_CD, SQI_CD);
```
Why:
- Rate/tax domains join by `(BSEG_ID, UOM_CD, TOU_CD, SQI_CD)`.
- Current index on `CI_BSEG_CALC_LN` does not include UOM/TOU/SQI.

2. `CI_BSEG_CALC` covering join-to-rate context columns
```sql
CREATE INDEX CISADM.XORG_BCALC_BSEG_HDR_RS_EFF
    ON CISADM.CI_BSEG_CALC (BSEG_ID, HEADER_SEQ, RS_CD, EFFDT);
```
Why:
- Query pattern joins `BSEG_ID+HEADER_SEQ`, then immediately uses `RS_CD+EFFDT` to resolve rate component type.

3. `CI_RC` join order aligned to query predicates
```sql
CREATE INDEX CISADM.XORG_CIRC_RS_RCSEQ_EFF
    ON CISADM.CI_RC (RS_CD, RC_SEQ, EFFDT);
```
Why:
- Existing index order is `(RS_CD, EFFDT, RC_SEQ)`.
- Domain path joins on `RS_CD` + `RC_SEQ` and then effective date; this order is typically more selective for rate lookups.

### P2 (high value for interactive ad hoc)
4. `CI_BILL` bill-date filter support
```sql
CREATE INDEX CISADM.XORG_CIBILL_BILLDT_BILLID
    ON CISADM.CI_BILL (BILL_DT, BILL_ID);
```
Why:
- Many report filters/groupings use `BILL_DT`; current indexes are keyed by `BILL_ID`, `ACCT_ID`, `BILL_STAT_FLG`.

5. `CI_BSEG` SA + segment-date path for expected-vs-actual billing
```sql
CREATE INDEX CISADM.XORG_CIBSEG_SA_CREDT
    ON CISADM.CI_BSEG (SA_ID, CRE_DTTM, BSEG_ID, BILL_ID);
```
Why:
- Billing requirements/reporting patterns join from SA and often restrict segment window via `CRE_DTTM`.

### P3 (workload-specific)
6. `C1_USAGE` for unbilled extraction window
```sql
CREATE INDEX CISADM.XORG_C1USAGE_SA_BSEG_END
    ON CISADM.C1_USAGE (SA_ID, BSEG_ID, END_DTTM, USAGE_ID);
```
Why:
- Unbilled snapshot query filters by `SA_ID`, `BSEG_ID IS NULL`, and `END_DTTM` window, then joins by `USAGE_ID`.

7. `CI_PAY_EVENT` time-based write-off payment trend support
```sql
CREATE INDEX CISADM.XORG_CIPEVT_PAYDT_EVT
    ON CISADM.CI_PAY_EVENT (PAY_DT, PAY_EVENT_ID);
```
Why:
- Write-off effectiveness/duration queries and payment windows filter by `PAY_DT`.
- Existing index has `PAY_EVENT_ID` leading with `PAY_DT` second.

## Critical Note on C1_BI Views
`C1_BI_BILLED_USAGE_VW` and `C1_BI_FT_VW` are views in this environment (columns present, no table/index entries).  
Direct indexing on these objects is not possible unless materialized objects are used.

DBA follow-up needed:
1. Inspect view definitions and dependency chain.
2. Apply equivalent indexes on underlying large base tables for:
   - `ACCOUNTING_DT`, `BSEG_ID`, `BILL_ID`, `RS_CD`, `SA_ID`, `ACCT_ID` paths.

## Safe Rollout Order
1. Create P1 indexes first.
2. Re-run `sql/performance/billed_revenue/domain_core_benchmark_30d.sql`.
3. If still slow, add P2.
4. Add P3 only if unbilled/write-off workloads remain slow.

## Verification SQL (works with current dictionary view columns)
```sql
SELECT index_name, table_name, column_name, column_position
FROM all_ind_columns
WHERE table_owner = 'CISADM'
  AND table_name IN (
    'CI_BSEG_CALC_LN','CI_BSEG_CALC','CI_RC',
    'CI_BILL','CI_BSEG','C1_USAGE','CI_PAY_EVENT'
  )
ORDER BY table_name, index_name, column_position;
```

