# D1_USAGE_RPT_CURR Ad Hoc Build Recipes

Use the Domain or Topic backed by `D1_USAGE_RPT_CURR` as the starting source.

## Global rules
- Add `Usage Start Date/Time` (`start_dttm`) or `Usage Status Date/Time` (`status_upd_dttm`) as the first filter in every view.
- Default to a bounded recent window such as the last 7, 30, or 90 days.
- Treat this as a usage-header fact: one row per `D1_USAGE_ID`.
- Use aggregated quantity fields from the header snapshot, not child-row counts, for quantity summaries.
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

## View 3: Estimate And Skip Monitor
### Visual
- Stacked bar chart

### Category
- `Is Estimated` (`is_estimate_desc`)

### Series
- `Skip Flag` (`skip_flg`)

### Measure
- `Count of Usage Transaction ID` (`d1_usage_id`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Calculation Group` (`usg_grp_cd`)
- `Measurement Cycle` (`msrmt_cyc_cd`)
- `Route` (`msrmt_cyc_rte_cd`)

### Best use
- Monitoring estimate and skip behavior in the usage process

## View 4: Usage Quantity By Sole UOM
### Visual
- Horizontal bar chart

### Category
- `Period SQ Sole UOM Code` (`period_sq_sole_uom_cd`)

### Measure
- `Sum of Period SQ Total Quantity` (`period_sq_total_quantity`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Period SQ Sole UOM Code` (`period_sq_sole_uom_cd`)
- `Calculation Group` (`usg_grp_cd`)
- `Service Provider` (`d1_spr_cd`)

### Best use
- High-level usage quantity by sole resolved UOM at header grain

## View 5: Route And Cycle Operational Workload
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Measurement Cycle` (`msrmt_cyc_desc`)
- Columns: `Route` (`msrmt_cyc_rte_desc`)
- Measure: `Count of Usage Transaction ID` (`d1_usage_id`)

### Table layout
- Rows: `Measurement Cycle` (`msrmt_cyc_desc`), `Route` (`msrmt_cyc_rte_desc`)
- Measures: `Count of Usage Transaction ID` (`d1_usage_id`), `Sum of Period SQ Total Quantity` (`period_sq_total_quantity`)

### Filters
- `Usage Start Date/Time` (`start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Service Provider` (`d1_spr_cd`)

### Best use
- Operational workload by route and cycle

## View 6: Billing Bridge Coverage
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

## View 7: Unbridged Usage Exceptions
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

## View 8: Usage Header Trace
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
- `Period SQ Total Quantity` (`period_sq_total_quantity`)
- `Scalar Total Final Quantity` (`scalar_total_final_quantity`)
- `Bridge Method` (`bridge_method`)
- `Service Agreement ID` (`sa_id`)
- `Account ID` (`acct_id`)
- `Customer Name` (`customer_name`)

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

## Measure guidance
- `Count of Usage Transaction ID` (`d1_usage_id`): safest volume KPI
- `Sum of Period SQ Total Quantity` (`period_sq_total_quantity`): default aggregated usage quantity
- `Sum of Scalar Total Final Quantity` (`scalar_total_final_quantity`): scalar-detail quantity proxy
- `Period SQ Row Count` and `Scalar Row Count`: structural detail measures, not the primary KPI

## Avoid
- Treating this as determinant-grain quantity truth
- Assuming every row has valid billing context
- Starting with no date filter

For determinant-level usage analysis, use a future child snapshot such as `D1_USAGE_PERIOD_SQ_RPT_CURR` or `D1_USAGE_SCALAR_DTL_RPT_CURR`.
