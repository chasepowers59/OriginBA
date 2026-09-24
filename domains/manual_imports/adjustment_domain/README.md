# Adjustment - Domain (Standard Offering, built 2026-09-24)

`/SmartCity/Report/Standard_Offering/Finance/Adjustments/Adjustment___Domain`: one row per
adjustment with everything a report about adjustments needs, so no adjustment report has to start
from the FT snapshot domains (FT / GL-line grain, frozen FTs only) or the hidden Workstreams domain.

Chase's ask: take the Workstreams "Adjustment - Domain", put it in the Standard Offering, and make
it comprehensive -- customer information, every lookup, flags, adjustment types. Built by
`scripts/jaspersoft/build_adjustment_domain.py` (tables, joins, calculated fields, sets as Python;
`domain_schema.py` emits the XML that `build_adj_ap_request_domain.py` shares), tests in
`tests/test_adjustment_domain.py`, schema for Origin_DEV in `schema.Origin_DEV_DS.xml`.

## What changed against the Workstreams domain

| Workstreams domain | This domain |
| --- | --- |
| Inner joins to SA, account, customer, labels: an adjustment whose SA is gone, or whose code has no label, vanished (2 of 16 on Odessa) | Root `CI_ADJ`, EVERY join outer: the row count is the adjustment count |
| Second join tree over a client-built view (`CMS_CI_APPR_REQ_BODA_VW`) and To Do entries | Approval request from `CI_APPR_REQ` with profile and BO-status labels; no CMS_* view |
| No adjustment-type configuration, no FT link, no premise, no division labels, no flags | 1.1 type configuration (A/P request type, distribution code, approval profile, freeze option, amount type), 1.2 the adjustment's FTs folded to one row, 1.3 characteristics folded to one row, 1.4 approval, 1.5 transfer partner, 2 A/P request, 3/3.1 SA + SA type (service type, special role), 4 account + every class label, 5 main customer + person facts, 6 characteristic and mailing premise, 7 flags |

Sets: 14, items: 221 (13 dimension sets + Measures). Secrets (`ALERT_INFO`, `WEB_PASSWD*`) are not declared.

## Facts the design rests on (Origin_DEV's database = Ellensburg 25.4 test, read-only, 2026-09-24)

- 501,193 adjustments; statuses 50 Frozen 478,372 / 60 Canceled 22,780 / 30 Freezable 27 / 10 Incomplete 14.
- Main-customer chain (`MAIN_CUST_SW = 'Y'` -> `NAME_TYPE_FLG = 'PRIM'`) resolves 501,193 of 501,193, no fan-out.
- At most 2 FTs per adjustment (AD frozen + AX cancellation) and 3 characteristics: both folded by
  derived tables (`ADJ_FT`, `ADJ_CHAR`) so the grain stays one row per adjustment.
- 261,050 transfers (`XFER_ADJ_ID`), 24,904 with an approval request, 748 on an A/P adjustment type
  (= the 748 A/P requests), 17,399 with characteristics, 501,175 with an FT.
- A CHAR key that is unset holds SPACES, not null: the blank-key flags test `IsNull(x) or x == ' '`.
- Column lists are from `ALL_TAB_COLUMNS` on that database, never from memory.

## Proofs (all EXACT against Oracle)

Full population, through pushed-down distinct counts (`jrs_domain_query.py --org ROOT --agg ...`):
status 478,372 / 22,780 / 27 / 14; transfer Y 261,050; approval Y 24,904; A/P type Y 748 = has
request Y 748; person 431,957 / business 69,236; characteristics Y 17,399; FT Y 501,175; SA active
197,150; non-revenue SA 40,709; open over 30 days 41.

2026 window (`--where "SET_ADJUSTMENT.ADJ_CRE_DT >= ts'2026-01-01 00:00:00'"`), where sums are
valid: 75,906 adjustments, 1,243,764.59; by status 9 / 15 / 73,904 / 1,978 with their sums; credit
21,636 / -1,145,488.98; frozen current amount 1,243,596.28, net after cancellation 1,223,860.59;
average days to freeze -1.4464; 308 A/P requests paid 79,716.79; open over 30 = 24; max days old 266.

## Two server facts learned here (also in the jaspersoft-server-operations skill)

- **The Ad Hoc engine caps in-memory work at 300,000 rows (Chase: a server setting, can be raised).**
  A distinct count is pushed to the database and counts everything (2,237,269 on the FT and GL
  snapshot domain); a query with a Sum, CountAll, or a group on a non-pushable field is evaluated
  in memory and stops at 300,001. QA therefore ties counts on the full population and money on a
  window under the cap. Ad Hoc users see the same cap on every domain.
- **`ElapsedDays(Today(0), ...)` is not pushable**: grouping on a flag that used it returned
  478,372 of 501,193 rows. Age lives in SQL now (`ADJ_AGE`: days old, open over 30 days;
  `ADJ_FT.DAYS_TO_FREEZE`), where the database computes it and every row counts.

## Rolling to another org

```bash
scripts/jaspersoft/jrs.sh jrs_promote.py --from test:Origin_DEV --to test:<Org> \
    --resource /SmartCity/Report/Standard_Offering/Finance/Adjustments/Adjustment___Domain \
    --resource /SmartCity/Report/Standard_Offering/Finance/adj_ap_requests_control \
    --into /SmartCity/Report/Standard_Offering/Finance/Adjustments --ds <Org>_DS \
    --param FROM_DT=2026-01-01 --param TO_DT=2026-09-30 [--dry-run] [--i-mean-prod]
```
Then the short QA: `jrs_domain_query.py --env X --org ROOT --domain <abs uri> --agg SET_ADJUSTMENT.ADJ_ID:CountDistinct`
must equal `count(*) from cisadm.ci_adj` on that client's database.
