# COLL_PROC_RPT_CURR Ad Hoc Build Recipes

Use the Domain or Topic backed by `COLL_PROC_RPT_CURR` as the starting source.

## Global rules
- Add `Collection Process Create Date Time` (`coll_proc_cre_dttm`) as the first filter in every view.
- Default to a bounded recent window such as the last 30, 60, or 90 days.
- Treat this as a collection-process fact: one row per `COLL_PROC_ID`.
- Use `Count of Collection Process ID` as the default KPI.
- Use `Process Arrears Amount` as a secondary measure when the question is about process-level arrears exposure, not account debt truth.
- Use a table for workflow detail and event trace views.

## View 1: Collection Status Monitor
### Visual
- Stacked bar chart

### Category
- `Collection Status` (`coll_status_desc`)

### Series
- `Collection Process Template` (`coll_proc_tmpl_desc`)

### Measure
- `Count of Collection Process ID` (`coll_proc_id`)

### Filters
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Collection Status Code` (`coll_status_flg`)
- `Collection Process Template Code` (`coll_proc_tmpl_cd`)
- `Collection Class Code` (`coll_cl_cd`)

### Best use
- Monitoring current process volume by status and template

## View 2: Collection Template Arrears Mix
### Visual
- Horizontal bar chart

### Category
- `Collection Process Template` (`coll_proc_tmpl_desc`)

### Measures
- `Count of Collection Process ID` (`coll_proc_id`)
- `Sum of Process Arrears Amount` (`ars_amt`)

### Filters
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Collection Status Code` (`coll_status_flg`)
- `Collection Class Code` (`coll_cl_cd`)

### Sort
- Descending by `Count of Collection Process ID`

### Best use
- Seeing which templates are driving the most process volume and arrears

## View 3: Next Open Event Queue
### Visual
- Table

### Columns
- `Collection Process ID` (`coll_proc_id`)
- `Account ID` (`acct_id`)
- `Customer Name` (`customer_name`)
- `Collection Status` (`coll_status_desc`)
- `Next Event Sequence` (`next_event_seq`)
- `Next Event Type` (`next_event_type_desc`)
- `Next Event Status` (`next_event_status_desc`)
- `Next Event Trigger Date` (`next_event_trigger_dt`)
- `Collection Process Template` (`coll_proc_tmpl_desc`)
- `Process Arrears Amount` (`ars_amt`)

### Filters
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Next Event Sequence` (`next_event_seq`)
- `Next Event Type Code` (`next_event_type_cd`)
- `Next Event Status Code` (`next_event_status_flg`)

### Sort
- `Next Event Trigger Date` ascending

### Best use
- Operational queue of open or upcoming collection events

## View 4: Latest Event Outcome Summary
### Visual
- Vertical bar chart

### Category
- `Latest Event Status` (`latest_event_status_desc`)

### Series
- `Latest Event Type` (`latest_event_type_desc`)

### Measure
- `Count of Collection Process ID` (`coll_proc_id`)

### Filters
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Collection Status Code` (`coll_status_flg`)
- `Collection Process Template Code` (`coll_proc_tmpl_cd`)

### Best use
- Seeing how recent process activity is ending

## View 5: Class And Cycle Profile
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Collection Class` (`coll_cl_desc`)
- Columns: `Bill Cycle` (`bill_cyc_desc`)
- Measure: `Count of Collection Process ID` (`coll_proc_id`)

### Table layout
- Rows: `Collection Class` (`coll_cl_desc`), `Bill Cycle` (`bill_cyc_desc`)
- Measures: `Count of Collection Process ID` (`coll_proc_id`), `Sum of Process Arrears Amount` (`ars_amt`)

### Filters
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Customer Class Code` (`cust_cl_cd`)
- `Account Management Group Code` (`acct_mgmt_grp_cd`)

### Best use
- Process segmentation by class and bill-cycle pattern

## View 6: Event Density By Process
### Visual
- Bar chart

### Category
- `Open Event Count` (`open_event_count`)

### Measure
- `Count of Collection Process ID` (`coll_proc_id`)

### Companion table
- Rows: `Open Event Count` (`open_event_count`), `Completed Event Count` (`completed_event_count`)
- Measures: `Count of Collection Process ID` (`coll_proc_id`)

### Filters
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Collection Status Code` (`coll_status_flg`)
- `Collection Process Template Code` (`coll_proc_tmpl_cd`)

### Best use
- Understanding how many processes are still carrying open-event workload

## View 7: Collection Process Trace
### Visual
- Table

### Columns
- `Collection Process ID` (`coll_proc_id`)
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Account ID` (`acct_id`)
- `Person ID` (`per_id`)
- `Customer Name` (`customer_name`)
- `Collection Process Template` (`coll_proc_tmpl_desc`)
- `Collection Status` (`coll_status_desc`)
- `Collection Status Reason` (`coll_stat_rsn_desc`)
- `Collection Condition Priority` (`coll_cat_prio_desc`)
- `Critical Priority` (`crit_prio_desc`)
- `Process Arrears Date` (`coll_ars_dt`)
- `Process Arrears Amount` (`ars_amt`)
- `Event Count` (`event_count`)
- `Open Event Count` (`open_event_count`)
- `Completed Event Count` (`completed_event_count`)
- `Latest Event Type` (`latest_event_type_desc`)
- `Latest Event Status` (`latest_event_status_desc`)
- `Latest Event Completion Date` (`latest_event_completion_dt`)

### Filters
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Collection Process ID` (`coll_proc_id`)
- `Account ID` (`acct_id`)
- `Customer Name` (`customer_name`)
- `Collection Status Code` (`coll_status_flg`)

### Sort
- `Collection Process Create Date Time` descending

### Best use
- One-row trace of a collection process and its current state

## Recommended common prompt set
- `Collection Process Create Date Time` (`coll_proc_cre_dttm`)
- `Collection Status Code` (`coll_status_flg`)
- `Collection Process Template Code` (`coll_proc_tmpl_cd`)
- `Collection Class Code` (`coll_cl_cd`)
- `Customer Class Code` (`cust_cl_cd`)
- `Bill Cycle Code` (`bill_cyc_cd`)
- `Account ID` (`acct_id`)

## Measure guidance
- `Count of Collection Process ID` (`coll_proc_id`): default process KPI
- `Sum of Process Arrears Amount` (`ars_amt`): process-level arrears context, not account debt truth
- `Sum of Open Event Count` (`open_event_count`): valid only when the business wants process-event workload, not unique event rows
- `Sum of Completed Event Count` (`completed_event_count`): same caution as open-event count

## Avoid
- Treating `ARS_AMT` as the same thing as governed account debt
- Using this snapshot for one-row-per-event workflow analysis
- Starting with no create-date filter
- Summing event counts when the business really wants unique processes

For account debt prioritization, use `ACCT_DEBT_RPT_CURR`.
