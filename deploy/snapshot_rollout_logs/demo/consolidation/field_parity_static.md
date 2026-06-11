# Consolidation Snapshot Field Parity (Static)

Compares snapshot DDL columns to legacy domain `source_column` values.

| Snapshot | Snapshot cols | Domain cols | Overlap |
|---|---:|---:|---:|
| `ACCT_CUSTOMER` | 59 | 42 | 10 (24%) |
| `CASE_PREM_CONTACT` | 90 | 143 | 35 (24%) |
| `PIPELINE` | 84 | 95 | 50 (53%) |
| `FIELD_ACTIVITY` | 103 | 78 | 55 (71%) |
| `CREW_OPS` | 35 | 52 | 7 (13%) |
| `DEVICE_SP` | 108 | 176 | 29 (16%) |
| `PAY_EVENT` | 32 | 50 | 15 (30%) |
| `BILLABLE_CHARGE` | 37 | 75 | 22 (29%) |
| `SA_AGED_BAL` | 42 | 103 | 17 (17%) |
| `WO_PROC` | 62 | 76 | 22 (29%) |
| `OPS_EXCEPTION` | 92 | 137 | 31 (23%) |
| `WORKFLOW_QUEUE` | 81 | 72 | 27 (38%) |
