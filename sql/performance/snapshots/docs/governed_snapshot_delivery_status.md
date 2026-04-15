# Governed Snapshot Delivery Status

## Completed

### Billed Usage
- `BSEG_BILLED_USAGE_RPT_CURR`
  - QA: complete
  - Master guide: complete
- `BSEG_SQ_USAGE_RPT_CURR`
  - QA: complete
  - Master guide: complete

### Finance
- `FT_RPT_CURR`
  - QA: complete
  - Master guide: complete
- `FT_GL_DISTRIBUTION_RPT_CURR`
  - QA: complete
  - Master guide: complete

### Meter Ops
- `D1_USAGE_RPT_CURR`
  - QA: complete
  - Master guide: complete
- `D1_USAGE_SCALAR_DTL_RPT_CURR`
  - QA: complete
  - Master guide: complete
- `D1_MSRMT_RPT_CURR`
  - QA: complete
  - Master guide: complete

## Remaining

### Debt Management
- `ACCT_DEBT_RPT_CURR`
  - QA: missing
  - Master guide: missing
- `COLL_PROC_RPT_CURR`
  - QA: missing
  - Master guide: missing

### Payments / Cashiering
- `PAY_TNDR_CASH_RPT_CURR`
  - QA: complete
  - Master guide: complete

## Operating Order
Use this order to finish the remaining governed snapshots:
1. `ACCT_DEBT_RPT_CURR`
2. `COLL_PROC_RPT_CURR`
3. `PAY_TNDR_CASH_RPT_CURR`

## Completion Standard
A snapshot is only fully complete when all of these exist and are aligned:
- snapshot SQL package
- workspace Domain XML
- importable Domain XML
- completed QA results document
- completed master technical guide
- README reflecting the final release shape
