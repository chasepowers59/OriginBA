# D1_USAGE_RPT_CURR Ad Hoc Build Recipes

Use the Domain or Topic backed by `D1_USAGE_RPT_CURR` as the starting source.

## Global rules
- Add `Usage Start Date/Time` (`start_dttm`) or `Usage Status Date/Time` (`status_upd_dttm`) as the first filter in every view.
- Default to a bounded recent window such as the last 7, 30, or 90 days.
- Treat this as a usage-header fact: one row per `D1_USAGE_ID`.
- Use this snapshot for process monitoring and segmentation, not quantity.
- Use a table for exception and trace views.

## View 1: Usage Status Monitor
### Visual
- Vertical bar chart

### Category
- `Usage Status` (`bo_status_desc`)

### Measure
- `Count of Usage Transaction ID` (`d1_usage_id`)

### Series
- Optional: `Usage Source` (`usg_src_desc`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Service Provider` (`d1_spr_cd`)
- `Measurement Cycle` (`msrmt_cyc_cd`)

### Best use
- Monitoring usage-transaction volume by status

## View 2: Used On Bill Vs Linked To Frozen Segment
### Visual
- Stacked bar chart

### Category
- `Used On Bill` (`used_on_bill_desc`)

### Series
- `Linked To Frozen Bill Segment` (`linked_to_frzn_bseg_desc`)

### Measure
- `Count of Usage Transaction ID` (`d1_usage_id`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Service Provider` (`d1_spr_cd`)
- `Bill Cycle Code` (`d1_bill_cyc_cd`)

### Best use
- Seeing how much processed usage actually bridges into billing

## View 3: Customer Class Usage Volume
### Visual
- Horizontal bar chart

### Category
- `Customer Class Description` (`cust_cl_desc`)

### Measure
- `Count of Usage Transaction ID` (`d1_usage_id`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Service Provider` (`d1_spr_cd`)
- `SA Type` (`sa_type_cd`)

### Best use
- Comparing usage-transaction volume by customer class

## View 4: Route And Cycle Operational Workload
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Measurement Cycle` (`msrmt_cyc_desc`)
- Columns: `Route` (`msrmt_cyc_rte_desc`)
- Measure: `Count of Usage Transaction ID` (`d1_usage_id`)

### Table layout
- Rows: `Measurement Cycle` (`msrmt_cyc_desc`), `Route` (`msrmt_cyc_rte_desc`)
- Measure: `Count of Usage Transaction ID` (`d1_usage_id`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Service Provider` (`d1_spr_cd`)

### Best use
- Operational workload by route and cycle

## View 5: Billing Bridge Coverage
### Visual
- Bar chart

### Category
- `Bridge Method` (`bridge_method`)

### Measure
- `Count of Usage Transaction ID` (`d1_usage_id`)

### Companion table
- Rows: `Bridge Method` (`bridge_method`), `C1 Usage Status Code` (`c1_bo_status_cd`)
- Measures: `Count of Usage Transaction ID` (`d1_usage_id`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Used On Bill` (`used_on_bill_flg`)

### Best use
- Validating how the usage header is resolving into billing context

## View 6: Unbridged Usage Exceptions
### Visual
- Table

### Columns
- `Usage Transaction ID` (`d1_usage_id`)
- `Usage Start Date/Time` (`start_dttm`)
- `Usage End Date/Time` (`end_dttm`)
- `Usage Status` (`bo_status_desc`)
- `Usage Status Reason` (`bo_status_reason_cd`)
- `Usage Source` (`usg_src_desc`)
- `Calculation Group` (`usg_grp_desc`)
- `Measurement Cycle` (`msrmt_cyc_desc`)
- `Route` (`msrmt_cyc_rte_desc`)
- `Used On Bill` (`used_on_bill_desc`)
- `Linked To Frozen Bill Segment` (`linked_to_frzn_bseg_desc`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Bridge Method` is null
- `Usage Status` (`bo_status_cd`)
- `Used On Bill` (`used_on_bill_flg`)

### Best use
- Investigating usage transactions that did not bridge into billing context

## View 7: Usage Header Trace
### Visual
- Table

### Columns
- `Usage Transaction ID` (`d1_usage_id`)
- `Usage Subscription ID` (`us_id`)
- `Usage External ID` (`usg_ext_id`)
- `Usage Status` (`bo_status_desc`)
- `Usage Calculation Type` (`d1_usg_cal_type_desc`)
- `Calculation Group` (`usg_grp_desc`)
- `Service Provider` (`d1_spr_desc`)
- `Usage Start Date/Time` (`start_dttm`)
- `Usage End Date/Time` (`end_dttm`)
- `Bridge Method` (`bridge_method`)
- `Service Agreement ID` (`sa_id`)
- `Account ID` (`acct_id`)
- `Customer Name` (`customer_name`)
- `Customer Class Description` (`cust_cl_desc`)
- `Premise ID` (`prem_id`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Usage Transaction ID` (`d1_usage_id`)
- `Usage Subscription ID` (`us_id`)
- `Service Agreement ID` (`sa_id`)
- `Account ID` (`acct_id`)

### Sort
- `Usage Start Date/Time` descending

### Best use
- Header-level usage transaction research

## Recommended common prompt set
- `Usage Start Date/Time` (`start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Calculation Group` (`usg_grp_cd`)
- `Usage Calculation Type` (`d1_usg_cal_type_cd`)
- `Service Provider` (`d1_spr_cd`)
- `Measurement Cycle` (`msrmt_cyc_cd`)
- `Route` (`msrmt_cyc_rte_cd`)
- `Used On Bill` (`used_on_bill_flg`)
- `Customer Class` (`cust_cl_cd`)

## Measure guidance
- `Count of Usage Transaction ID` (`d1_usage_id`): safest and primary KPI for the header snapshot

## Avoid
- Treating this as determinant-grain quantity truth
- Summing usage quantity from this snapshot
- Assuming every row has valid billing context
- Starting with no date filter

For quantity analysis, use `D1_USAGE_SCALAR_DTL_RPT_CURR`.
