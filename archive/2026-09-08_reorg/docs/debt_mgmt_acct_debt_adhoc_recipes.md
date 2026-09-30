# ACCT_DEBT_RPT_CURR Ad Hoc Build Recipes

Use the Domain or Topic backed by `ACCT_DEBT_RPT_CURR` as the starting source.

## Global rules
- Add `Total Debt` as a positive-value filter or sort in most debt views.
- Default to a bounded business slice such as one collection class, one debt class, or one bill-cycle segment before expanding to all accounts.
- Treat this as an account-debt fact: one row per `ACCT_ID`.
- Use `Total Debt` as the default additive financial measure.
- Use a table for outreach and trace views.
- Do not sum latest collection or latest write-off fields as if they were population-wide debt truth.

## View 1: Collection Class Debt Exposure
### Visual
- Horizontal bar chart

### Category
- `Collection Class` (`coll_cl_desc`)

### Measure
- `Sum of Total Debt` (`total_debt`)

### Companion table
- Rows: `Collection Class` (`coll_cl_desc`)
- Measures: `Count of Account ID` (`acct_id`), `Sum of Total Debt` (`total_debt`)

### Filters
- `Collection Class Code` (`coll_cl_cd`)
- `Sole Debt Class Code` (`sole_debt_cl_cd`)
- `Last Bill Date` (`last_bill_dt`)

### Sort
- Descending by `Sum of Total Debt`

### Best use
- Ranking debt exposure across account collection segments

## View 2: Aging Bucket Mix
### Visual
- Stacked bar chart

### Category
- `Collection Class` (`coll_cl_desc`)

### Measures
- `Sum of Debt 0 To 30 Days` (`debt_0_30`)
- `Sum of Debt 31 To 60 Days` (`debt_31_60`)
- `Sum of Debt 61 To 90 Days` (`debt_61_90`)
- `Sum of Debt Over 90 Days` (`debt_over_90`)

### Filters
- `Collection Class Code` (`coll_cl_cd`)
- `Sole Debt Class Code` (`sole_debt_cl_cd`)
- `Oldest Age Days` (`oldest_age_days`)

### Best use
- Seeing whether a population is early-stage or long-aged debt

## View 3: Debt Class Profile
### Visual
- Vertical bar chart

### Category
- `Sole Debt Class` (`sole_debt_cl_desc`)

### Measures
- `Count of Account ID` (`acct_id`)
- `Sum of Total Debt` (`total_debt`)

### Filters
- `Debt Class Count` (`debt_cl_count`)
- `Collection Class Code` (`coll_cl_cd`)
- `Governed Arrears Service Agreement Count` (`governed_arrears_sa_count`)

### Best use
- Comparing single-class debt populations and isolating mixed-class accounts

## View 4: Collection And Write Off Overlay
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Latest Collection Status` (`latest_coll_status_desc`)
- Columns: `Latest Write Off Status` (`latest_wo_status_desc`)
- Measure: `Count of Account ID` (`acct_id`)

### Table layout
- Rows: `Latest Collection Status` (`latest_coll_status_desc`), `Latest Write Off Status` (`latest_wo_status_desc`)
- Measures: `Count of Account ID` (`acct_id`), `Sum of Total Debt` (`total_debt`)

### Filters
- `Collection Process Count` (`coll_proc_count`)
- `Write Off Process Count` (`wo_proc_count`)
- `Collection Class Code` (`coll_cl_cd`)

### Best use
- Understanding how current debt aligns to latest process state

## View 5: Credit Review And Postpone Queue
### Visual
- Table

### Columns
- `Account ID` (`acct_id`)
- `Customer Name` (`customer_name`)
- `Collection Class` (`coll_cl_desc`)
- `Credit Review Date` (`cr_review_dt`)
- `Postpone Credit Review Date` (`postpone_cr_rvw_dt`)
- `Total Debt` (`total_debt`)
- `Debt Over 90 Days` (`debt_over_90`)
- `Collection Process Count` (`coll_proc_count`)
- `Latest Collection Status` (`latest_coll_status_desc`)

### Filters
- `Credit Review Date` (`cr_review_dt`)
- `Postpone Credit Review Date` (`postpone_cr_rvw_dt`)
- `Collection Class Code` (`coll_cl_cd`)
- `Latest Collection Status Code` (`latest_coll_status_flg`)

### Sort
- `Credit Review Date` ascending
- Then `Total Debt` descending

### Best use
- Building operational outreach and credit-review worklists

## View 6: Largest Debt Accounts
### Visual
- Table

### Columns
- `Account ID` (`acct_id`)
- `Person ID` (`per_id`)
- `Customer Name` (`customer_name`)
- `Collection Class` (`coll_cl_desc`)
- `Active Service Agreement Count` (`active_sa_count`)
- `Debt Class Count` (`debt_cl_count`)
- `Sole Debt Class` (`sole_debt_cl_desc`)
- `Governed Arrears Financial Transaction Count` (`governed_arrears_ft_count`)
- `Governed Arrears Service Agreement Count` (`governed_arrears_sa_count`)
- `Total Debt` (`total_debt`)
- `Debt Over 90 Days` (`debt_over_90`)
- `Oldest Arrears Date` (`oldest_ars_dt`)
- `Newest Arrears Date` (`newest_ars_dt`)
- `Last Bill Date` (`last_bill_dt`)

### Filters
- `Account ID` (`acct_id`)
- `Collection Class Code` (`coll_cl_cd`)
- `Sole Debt Class Code` (`sole_debt_cl_cd`)
- `Oldest Age Days` (`oldest_age_days`)

### Sort
- `Total Debt` descending

### Best use
- Prioritizing the highest-risk debt accounts for action

## View 7: Account Debt Trace
### Visual
- Table

### Columns
- `Account ID` (`acct_id`)
- `Customer Name` (`customer_name`)
- `Collection Class` (`coll_cl_desc`)
- `Credit Review Date` (`cr_review_dt`)
- `Latest Collection Process ID` (`latest_coll_proc_id`)
- `Latest Collection Status` (`latest_coll_status_desc`)
- `Latest Collection Process Template` (`latest_coll_proc_tmpl_desc`)
- `Latest Write Off Process ID` (`latest_wo_proc_id`)
- `Latest Write Off Status` (`latest_wo_status_desc`)
- `Latest Write Off Process Template` (`latest_wo_proc_tmpl_desc`)
- `Collection Agency Reference Count` (`coll_agy_ref_count`)
- `Total Debt` (`total_debt`)
- `Debt 0 To 30 Days` (`debt_0_30`)
- `Debt 31 To 60 Days` (`debt_31_60`)
- `Debt 61 To 90 Days` (`debt_61_90`)
- `Debt Over 90 Days` (`debt_over_90`)

### Filters
- `Account ID` (`acct_id`)
- `Latest Collection Process ID` (`latest_coll_proc_id`)
- `Latest Write Off Process ID` (`latest_wo_proc_id`)
- `Customer Name` (`customer_name`)

### Best use
- One-row account research before moving into lower-grain process detail

## Recommended common prompt set
- `Collection Class Code` (`coll_cl_cd`)
- `Sole Debt Class Code` (`sole_debt_cl_cd`)
- `Credit Review Date` (`cr_review_dt`)
- `Last Bill Date` (`last_bill_dt`)
- `Latest Collection Status Code` (`latest_coll_status_flg`)
- `Latest Write Off Status Code` (`latest_wo_status_flg`)
- `Account ID` (`acct_id`)

## Measure guidance
- `Sum of Total Debt` (`total_debt`): default additive debt KPI
- `Sum of Debt Over 90 Days` (`debt_over_90`): best severe-aging KPI
- `Count of Account ID` (`acct_id`): safest population KPI
- `Governed Arrears Financial Transaction Count` (`governed_arrears_ft_count`): supporting density measure, not a debt measure
- latest process arrears amounts: descriptive overlays, not account-debt truth

## Avoid
- Treating latest collection/write-off fields as replacements for account debt truth
- Summing process overlays instead of `Total Debt`
- Using this snapshot for row-per-process analysis
- Starting broad outreach views with no segmentation or sort

For row-per-process analysis, use `COLL_PROC_RPT_CURR`.
