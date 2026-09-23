# Adjustment A/P Requests: control report and Ad Hoc domain (built 2026-09-23)

The ask: a Standard Offering report for "cancelled refund A/P requests", i.e. `CISADM.CI_ADJ_APREQ`
rows the ERP canceled (`PYMNT_SEL_STAT_FLG = 'X'`) whose adjustment is still open, so a user still
has to cancel the adjustment. Nothing in the Standard Offering read that table.

## What exists now, on test Origin_DEV

| Deliverable | Where | Built by |
| --- | --- | --- |
| Report unit **Adjustment A/P Requests - Control** | `/SmartCity/Report/Standard_Offering/Finance/adj_ap_requests_control` | spec `adj_ap_requests_control` in `scripts/jaspersoft/generate_sql_report_pack.py`; deployed with `jrs_deploy_report_units.py --only adj_ap_requests_control` |
| Domain **Adjustment A/P Request - Domain** | `/SmartCity/Report/Standard_Offering/Finance/Adjustments/Adjustment_AP_Request___Domain` | `scripts/jaspersoft/build_adj_ap_request_domain.py --ds <Org>_DS`, imported with `jrs_import_domain.py` |

The report groups every request in an adjustment-created-date window by request status x adjustment
status and names the action per combination -- "Cancel the adjustment: its A/P request was
canceled" (request X, adjustment 30 freezable or 50 frozen) and "Paid, but the adjustment was
canceled: recover" (request P, adjustment 60) -- action rows first, the requests listed under each
with payee, account, amounts and dates. Controls: the date window, request status and adjustment
status pick-lists (codes with activity in the last three years), an action-only switch, account.

The domain gives Ad Hoc the same facts row by row: A/P Request, Adjustment, Adjustment Type
Configuration, Service Agreement / Account / Customer, and Formulas with **Action Needed** and
**Paid But Adjustment Canceled** flags plus request count and amount measures.

## Facts the design rests on (Oracle, read-only, 2026-09-23)

- Odessa: 16 requests, 16 distinct adjustments, 0 requests without an adjustment: the request ->
  adjustment link is one-to-one, so it is the only inner join. 2 of 16 adjustments point at a
  service agreement that no longer exists: SA, account and customer are outer.
- Odessa is the live case: 2 requests X with adjustments frozen (201.00), 3 X already resolved
  (adjustment 60). Ellensburg (Origin_DEV's database): no open case, 14 resolved, 5 paid-but-canceled.
- Statuses decoded from `CI_LOOKUP_VAL_L`: PYMNT_SEL_STAT_FLG N/R/H/P/X/C/D/V, ADJ_STATUS_FLG
  05/10/20/30/50/60 -- base-product lifecycles, the only literals in the SQL.

## Proofs

- Report: created on Origin_DEV (201) with six controls; rendered as PDF over 2024-01-01..2026-12-31,
  19 pages, action rows first (5 paid-but-canceled, 3,125.89), then 441 paid/frozen etc.
- Report query on Odessa through the read-only connection: first row X / Frozen / "Cancel the
  adjustment" / 2 requests / 201.00 -- the two live cases.
- Domain: 748 rows on Origin_DEV = Oracle's own count for Ellensburg (441 + 288 + 14 + 5); every row
  carries the main customer name and both decoded statuses; Paid But Adjustment Canceled = Y on
  exactly the 5 P/60 rows; tests in `tests/test_adj_ap_request_domain.py`.

## Lessons (each cost a round trip)

- A domain's `<joinInfo alias=...>` is the ROOT TABLE id, not the join tree: with the tree's id the
  query engine answers 500 "when ordering original minJoins".
- Never emit an empty `<filterString></filterString>`: "exception parsing filter string ''".
- A report unit description over 250 characters is refused (`illegal.parameter.value.error`); the
  deploy tool now clips at 240, as the domain packager already did.

## Rolling to another org

```bash
python3 scripts/jaspersoft/build_adj_ap_request_domain.py --ds <Org>_DS --out /tmp/apreq.xml
scripts/jaspersoft/jrs.sh jrs_import_domain.py --env test --org <Org> --ds <Org>_DS \
    --folder /SmartCity/Report/Standard_Offering/Finance/Adjustments --name Adjustment_AP_Request___Domain \
    --label "Adjustment A/P Request - Domain" --schema /tmp/apreq.xml
scripts/jaspersoft/jrs.sh jrs_deploy_report_units.py --org <Org> --datasource <Org>_DS --only adj_ap_requests_control --run 2024-01-01 2026-12-31
```
Or promote the two objects with the Standard Offering folder as usual. Prod needs `--i-mean-prod`.
