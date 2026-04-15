# D1_USAGE_SCALAR_DTL_RPT_CURR Ad Hoc Build Recipes

Use the Domain or Topic backed by `D1_USAGE_SCALAR_DTL_RPT_CURR` as the starting source.

## Global rules
- Add `Usage Start Date/Time` (`usage_start_dttm`) as the first filter in every view.
- Default to a bounded recent window such as the last 7, 30, or 90 days.
- Treat this as a scalar-detail fact: one row per `D1_USAGE_ID + SEQ_NUM`.
- Use `Final Quantity` (`final_quantity`) as the default measure when the business question is billed/derived usage.
- Use `Quantity` (`quantity`) when the raw scalar quantity itself is the question.

## View 1: Customer Class Consumption By Final UOM
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Customer Class Description` (`cust_cl_desc`)
- Columns: `Final UOM Description` (`d1_final_uom_desc`)
- Measure: `Sum of Final Quantity` (`final_quantity`)

### Table layout
- Rows: `Customer Class Description` (`cust_cl_desc`), `Final UOM Description` (`d1_final_uom_desc`)
- Measures: `Sum of Final Quantity` (`final_quantity`), `Count of Scalar Rows`

### Filters
- `Usage Start Date/Time` (`usage_start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Final UOM Code` (`d1_final_uom_cd`)
- `Service Type` (`sa_type_cd`)

### Best use
- Customer-class consumption reporting by final unit of measure

## View 2: Premise Consumption Trace
### Visual
- Table

### Columns
- `Usage Transaction ID` (`d1_usage_id`)
- `Sequence` (`seq_num`)
- `Premise ID` (`prem_id`)
- `Address` (`address1`)
- `City` (`city`)
- `Service Point ID` (`d1_sp_id`)
- `Measuring Component ID` (`measr_comp_id`)
- `Final UOM Description` (`d1_final_uom_desc`)
- `Final TOU Description` (`d1_final_tou_desc`)
- `Final SQI Description` (`d1_final_sqi_desc`)
- `Final Quantity` (`final_quantity`)

### Filters
- `Usage Start Date/Time` (`usage_start_dttm`)
- `Premise ID` (`prem_id`)
- `Final UOM Code` (`d1_final_uom_cd`)

### Best use
- Premise-level consumption research

## View 3: Service Type Quantity Trend By UOM
### Visual
- Stacked bar chart

### Category
- `Service Type Description` (`sa_type_desc`)

### Series
- `Final UOM Description` (`d1_final_uom_desc`)

### Measure
- `Sum of Final Quantity` (`final_quantity`)

### Filters
- `Usage Start Date/Time` (`usage_start_dttm`)
- `Customer Class` (`cust_cl_cd`)
- `Usage Status` (`bo_status_cd`)

### Best use
- Comparing quantity mix across service types

## View 4: Measuring Component Usage Breakdown
### Visual
- Table

### Columns
- `Measuring Component ID` (`measr_comp_id`)
- `Service Point ID` (`d1_sp_id`)
- `Usage Transaction ID` (`d1_usage_id`)
- `Sequence` (`seq_num`)
- `Usage Flag Description` (`d1_usage_desc`)
- `Measure Component Usage Description` (`measr_comp_usage_desc`)
- `Final UOM Description` (`d1_final_uom_desc`)
- `Final Quantity` (`final_quantity`)

### Filters
- `Usage Start Date/Time` (`usage_start_dttm`)
- `Measuring Component ID` (`measr_comp_id`)
- `Final UOM Code` (`d1_final_uom_cd`)

### Best use
- Meter-side scalar quantity research by measuring component

## View 5: Raw Vs Final Quantity Comparison
### Visual
- Table

### Columns
- `Usage Transaction ID` (`d1_usage_id`)
- `Sequence` (`seq_num`)
- `Raw UOM Description` (`d1_uom_desc`)
- `Quantity` (`quantity`)
- `Final UOM Description` (`d1_final_uom_desc`)
- `Final Quantity` (`final_quantity`)
- `Applied Multiplier` (`applied_mltr`)
- `Use Percent` (`use_percent`)
- `Usage Rule Description` (`usg_rule_desc`)

### Filters
- `Usage Start Date/Time` (`usage_start_dttm`)
- `Final UOM Code` (`d1_final_uom_cd`)
- `Usage Rule` (`usg_rule_cd`)

### Best use
- Understanding scalar transformation from raw to final quantity

## View 6: Billing-Linked Scalar Trace
### Visual
- Table

### Columns
- `Usage Transaction ID` (`d1_usage_id`)
- `Sequence` (`seq_num`)
- `Bridge Method` (`bridge_method`)
- `C1 Usage ID` (`c1_usage_id`)
- `Bill Segment ID` (`c1_bseg_id`)
- `Service Agreement ID` (`sa_id`)
- `Account ID` (`acct_id`)
- `Customer Name` (`customer_name`)
- `Final UOM Description` (`d1_final_uom_desc`)
- `Final Quantity` (`final_quantity`)

### Filters
- `Usage Start Date/Time` (`usage_start_dttm`)
- `Bridge Method`
- `Account ID` (`acct_id`)
- `Service Agreement ID` (`sa_id`)

### Best use
- Tracing scalar quantities into billing context

## Recommended common prompt set
- `Usage Start Date/Time` (`usage_start_dttm`)
- `Usage Status` (`bo_status_cd`)
- `Final UOM Code` (`d1_final_uom_cd`)
- `Final TOU Code` (`d1_final_tou_cd`)
- `Final SQI Code` (`d1_final_sqi_cd`)
- `Customer Class` (`cust_cl_cd`)
- `Service Type` (`sa_type_cd`)
- `Premise ID` (`prem_id`)

## Measure guidance
- `Sum of Final Quantity` (`final_quantity`): default quantity measure
- `Sum of Quantity` (`quantity`): raw quantity measure
- `Count of Scalar Rows`: detail activity / volume proxy

## Avoid
- Treating this as one row per usage header
- Using it for pure process monitoring without detail context

Use `D1_USAGE_RPT_CURR` for the header/process view.
