# Prefilter Candidate Summary

## Totals
- Indexed column rows analyzed: 10339
- Leading indexed columns: 5127
- Valid + visible index column rows: 10339
- Recommended prefilter candidates: 5127
- Candidate columns that are date-like: 58
- Candidate columns in domain metadata: 161

## Top Tables By Candidate Count
- W1_ACTIVITY: 19
- W1_WO: 15
- W1_NODE: 13
- W1_PROJECT: 13
- C1_CS_REQ_PREM: 11
- CI_FT: 11
- W1_SVC_HIST: 10
- C1_CS_REQ_SA: 9
- C1_CS_REQ_SVC_LOC: 9
- CI_BILL: 9
- F1_CALENDAR_D: 9
- W1_ASSET: 9
- W1_CMPL_EVT: 9
- W1_PO_LINE: 9
- W1_WORK_REQ: 9
- C1_CS_REQ_CONT_PROD: 8
- C1_MKT_RP: 8
- CI_PAY_TNDR: 8
- CI_PREM: 8
- CI_TD_ENTRY: 8

## Usage Notes
- Use leading indexed date columns first for rolling-window domain pre-filters.
- For non-date candidates, use equality/IN pre-filters and pair with a date window when possible.
- After pre-filtering on indexed columns, include additional business fields freely in the report.
