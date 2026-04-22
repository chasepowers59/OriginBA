# Workstream Coverage Matrix

Use this matrix to record what is covered today and where reporting still has semantic or performance gaps.

| Workstream | Primary Business Questions | Current Governed Artifact | Source Tables Actually Used | Client-Specific Config Tables / Codes | Known Gaps | Recommended Next Artifact |
|---|---|---|---|---|---|---|
| Finance |  |  |  |  |  |  |
| Billing and Rates |  |  |  |  |  |  |
| Meter Operations |  |  |  |  |  |  |
| Payments and Cashiering |  |  |  |  |  |  |
| Debt Management / Collections |  |  |  |  |  |  |
| Customer / Account |  |  |  |  |  |  |
| Service Point / Device / Asset |  |  |  |  |  |  |

## What to capture
- **Current Governed Artifact**: snapshot table, Domain, Topic, report SQL, or `none`
- **Source Tables Actually Used**: proven source tables, not guessed tables
- **Client-Specific Config Tables / Codes**: types, statuses, cycles, units, source-status values, tender or debt codes, and any non-standard local configuration
- **Known Gaps**: row-multiplication risk, missing truth layer, missing additive measures, stale lookup coverage, slow raw-table joins, missing dimensions
- **Recommended Next Artifact**: snapshot, Topic, derived table, Domain cleanup, or direct report SQL
