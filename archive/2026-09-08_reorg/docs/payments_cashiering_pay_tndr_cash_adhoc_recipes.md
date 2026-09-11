# PAY_TNDR_CASH_RPT_CURR Ad Hoc Build Recipes

Use the Domain or Topic backed by `PAY_TNDR_CASH_RPT_CURR` as the starting source.

## Global rules
- Add `Payment Date` (`pay_dt`) as the first filter in every view.
- Default to a bounded range such as the last 30, 60, or 90 days for operational views.
- Treat this as a tender fact: one row per `PAY_TENDER_ID`.
- Use `Tender Amount` as the default additive measure.
- Use a table for trace/detail views.
- Do not sum event-level overlays or deposit-control balances as if they were tender-additive measures.

## View 1: Source Family Mix
### Visual
- Vertical bar chart

### Category
- `Source Family` (`source_family_desc`)

### Measures
- `Count of Pay Tender ID` (`pay_tender_id`)
- `Sum of Tender Amount` (`tender_amt`)

### Filters
- `Payment Date` (`pay_dt`)
- `Source Family Code` (`source_family_cd`)
- `Tender Type Code` (`tender_type_cd`)
- `Tender Status Code` (`tndr_status_flg`)

### Sort
- Descending by `Sum of Tender Amount`

### Best use
- High-level channel mix across OriginPay, legacy auto-pay, staged external, and other cashiering sources

## View 2: Tender Source Performance
### Visual
- Horizontal bar chart

### Category
- `Tender Source` (`tndr_source_desc`)

### Series
- `Tender Type` (`tender_type_desc`)

### Measure
- `Sum of Tender Amount` (`tender_amt`)

### Companion table
- Rows: `Tender Source` (`tndr_source_desc`), `Tender Type` (`tender_type_desc`)
- Measures: `Count of Pay Tender ID` (`pay_tender_id`), `Sum of Tender Amount` (`tender_amt`)

### Filters
- `Payment Date` (`pay_dt`)
- `Source Family Code` (`source_family_cd`)
- `Tender Source Type Code` (`tndr_srce_type_flg`)
- `Tender Status Code` (`tndr_status_flg`)

### Best use
- Comparing cashier stations, mail, lockbox, OriginPay, and ACH-like sources

## View 3: Tender Status Monitor
### Visual
- Stacked bar chart

### Category
- `Tender Type` (`tender_type_desc`)

### Series
- `Tender Status Code` (`tndr_status_flg`)

### Measure
- `Count of Pay Tender ID` (`pay_tender_id`)

### Filters
- `Payment Date` (`pay_dt`)
- `Source Family Code` (`source_family_cd`)
- `Tender Source Code` (`tndr_source_cd`)

### Best use
- Monitoring tender volume by type and status

## View 4: Deposit Control Exposure
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Tender Source` (`tndr_source_desc`)
- Columns: `Deposit Control Status Code` (`dep_ctl_status_flg`)
- Measure: `Count of Pay Tender ID` (`pay_tender_id`)

### Table layout
- Rows: `Tender Source` (`tndr_source_desc`), `Deposit Control Status Code` (`dep_ctl_status_flg`)
- Measures: `Count of Pay Tender ID` (`pay_tender_id`), `Sum of Tender Amount` (`tender_amt`)

### Filters
- `Payment Date` (`pay_dt`)
- `Deposit Control ID` (`dep_ctl_id`)
- `Deposit Control Source Type Code` (`dep_ctl_srce_type_flg`)
- `Source Family Code` (`source_family_cd`)

### Best use
- Operational review of tender populations tied to deposit-control states

## View 5: Staged External Tender Monitor
### Visual
- Table

### Columns
- `Payment Date` (`pay_dt`)
- `Pay Tender ID` (`pay_tender_id`)
- `Payment Event ID` (`pay_event_id`)
- `Payor Account ID` (`payor_acct_id`)
- `Customer Name` (`customer_name`)
- `Tender Source` (`tndr_source_desc`)
- `Tender Type` (`tender_type_desc`)
- `Tender Amount` (`tender_amt`)
- `Staged Tender Switch` (`staged_tender_sw`)
- `Staged Tender Status Code` (`pay_tnd_stg_st_flg`)
- `External Source ID` (`ext_source_id`)
- `Auto Pay Source Name` (`apay_src_name`)
- `Source Family` (`source_family_desc`)

### Filters
- `Payment Date` (`pay_dt`)
- `Staged Tender Switch` (`staged_tender_sw`)
- `External Source ID` (`ext_source_id`)
- `Auto Pay Source Code` (`apay_src_cd`)

### Sort
- `Payment Date` descending

### Best use
- Monitoring inbound staged tenders and their mapped external sources

## View 6: Legacy Auto Pay Vs OriginPay
### Visual
- Vertical bar chart

### Category
- `Source Family` (`source_family_desc`)

### Measures
- `Count of Pay Tender ID` (`pay_tender_id`)
- `Sum of Tender Amount` (`tender_amt`)

### Filters
- `Payment Date` (`pay_dt`)
- `Source Family Code` in `ORIGINPAY`, `LEGACY_APAY`
- `Tender Type Code` (`tender_type_cd`)

### Best use
- Comparing historical legacy auto-pay volume to OriginPay volume

## View 7: Payment Application Overlay
### Visual
- Table

### Columns
- `Payment Date` (`pay_dt`)
- `Pay Tender ID` (`pay_tender_id`)
- `Payment Event ID` (`pay_event_id`)
- `Sole Pay ID` (`sole_pay_id`)
- `Event Pay Status` (`event_pay_status_desc`)
- `Event Pay Count` (`event_pay_count`)
- `Event Pay Amount` (`event_pay_amt`)
- `Event Tender Count` (`event_tender_count`)
- `Event Tender Amount` (`event_tender_amt`)
- `Event Pay Segment Count` (`event_pay_seg_count`)
- `Event Pay Segment Amount` (`event_pay_seg_amt`)
- `Event Match Event Count` (`event_match_evt_count`)
- `Tender Amount` (`tender_amt`)

### Filters
- `Payment Date` (`pay_dt`)
- `Payment Event ID` (`pay_event_id`)
- `Sole Pay ID` (`sole_pay_id`)
- `Source Family Code` (`source_family_cd`)

### Best use
- Researching how a tender sits inside payment-event and application context

## View 8: Tender Trace
### Visual
- Table

### Columns
- `Payment Date` (`pay_dt`)
- `Pay Tender ID` (`pay_tender_id`)
- `Payment Event ID` (`pay_event_id`)
- `Payor Account ID` (`payor_acct_id`)
- `Person ID` (`per_id`)
- `Customer Name` (`customer_name`)
- `Tender Type` (`tender_type_desc`)
- `Tender Status Code` (`tndr_status_flg`)
- `Tender Amount` (`tender_amt`)
- `Source Family` (`source_family_desc`)
- `Tender Source` (`tndr_source_desc`)
- `Tender Control ID` (`tndr_ctl_id`)
- `Deposit Control ID` (`dep_ctl_id`)
- `Deposit Control Status Code` (`dep_ctl_status_flg`)
- `External Source ID` (`ext_source_id`)
- `Auto Pay Source Name` (`apay_src_name`)

### Filters
- `Payment Date` (`pay_dt`)
- `Pay Tender ID` (`pay_tender_id`)
- `Payment Event ID` (`pay_event_id`)
- `Payor Account ID` (`payor_acct_id`)
- `Source Family Code` (`source_family_cd`)

### Sort
- `Payment Date` descending

### Best use
- One-row tender research before moving into raw payment or accounting detail

## Recommended common prompt set
- `Payment Date` (`pay_dt`)
- `Source Family Code` (`source_family_cd`)
- `Tender Source Code` (`tndr_source_cd`)
- `Tender Type Code` (`tender_type_cd`)
- `Tender Status Code` (`tndr_status_flg`)
- `Staged Tender Switch` (`staged_tender_sw`)
- `Payor Account ID` (`payor_acct_id`)

## Measure guidance
- `Sum of Tender Amount` (`tender_amt`): default additive KPI
- `Count of Pay Tender ID` (`pay_tender_id`): safest volume KPI
- `Event Pay Amount` (`event_pay_amt`): overlay only, repeated across all tenders in the same event
- `Event Tender Amount` (`event_tender_amt`): overlay only, not additive across tender rows
- `Event Pay Segment Amount` (`event_pay_seg_amt`): overlay only, not additive across tender rows
- deposit-control balances and deposit amounts: operational overlays, not tender-additive measures

## Avoid
- Summing event-level or deposit-level overlays in broad tender summaries
- Treating this as one-row-per-payment or one-row-per-pay-segment truth
- Starting with no `Payment Date` filter
- Ignoring `Source Family` when comparing channel performance

For payment application detail at lower grain, build or use a `PAY_SEG`-level artifact.
