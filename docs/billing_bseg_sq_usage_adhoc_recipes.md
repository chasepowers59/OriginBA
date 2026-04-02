# BSEG_SQ_USAGE_RPT_CURR Ad Hoc Build Recipes

Use the Domain or Topic backed by `BSEG_SQ_USAGE_RPT_CURR` as the starting source.

## Global rules
- Add `Bill Date` (`bill_dt`) as the first filter in every view.
- Default to a bounded range such as the last 1, 3, or 6 bill months.
- Use `Total Billed Usage` (`total_bill_sq`) as the default quantity measure.
- This is the UOM-safe billed-usage source because the grain is one row per `BSEG_ID + UOM_CD + TOU_CD + SQI_CD`.
- Use a table for determinant trace/detail views.
- Use a bar chart first for summary comparisons, then save a table companion view.

## View 1: Billed Usage By UOM
### Visual
- Vertical bar chart

### Category
- `Unit Of Measure` (`uom_desc`)

### Measures
- `Sum of Total Billed Usage` (`total_bill_sq`)
- Optional: `Count of Bill Segment ID` (`bseg_id`)

### Filters
- `Bill Date` (`bill_dt`)
- `Unit Of Measure Code` (`uom_cd`)
- `Service Type Code` (`sa_type_cd`)
- `Bill Cycle Code` (`bill_bill_cyc_cd`)
- `Customer Class Code` (`cust_cl_cd`)

### Sort
- Descending by `Sum of Total Billed Usage`

### Best use
- Safe UOM reporting across the billed-usage population

## View 2: Service Type By UOM
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Service Type` (`sa_type_desc`)
- Columns: `Unit Of Measure` (`uom_desc`)
- Measure: `Sum of Total Billed Usage` (`total_bill_sq`)

### Table layout
- Rows: `Service Type` (`sa_type_desc`), `Unit Of Measure` (`uom_desc`)
- Measures: `Sum of Total Billed Usage` (`total_bill_sq`), `Count of Bill Segment ID` (`bseg_id`)

### Filters
- `Bill Date` (`bill_dt`)
- `Bill Cycle Code` (`bill_bill_cyc_cd`)
- `Utility / Service Category Code` (`utility_type_cd`)

### Best use
- Identifying which service types mix or separate unit families

## View 3: UOM And TOU Summary
### Visual
- Horizontal bar chart

### Category
- `Unit Of Measure` (`uom_desc`)

### Series
- `Time Of Use` (`tou_desc`)

### Measure
- `Sum of Total Billed Usage` (`total_bill_sq`)

### Filters
- `Bill Date` (`bill_dt`)
- `Service Type Code` (`sa_type_cd`)
- `Unit Of Measure Code` (`uom_cd`)
- `Time Of Use Code` (`tou_cd`)

### Best use
- Quantity analysis by UOM and TOU where TOU matters operationally

## View 4: SQI Profile
### Visual
- Bar chart

### Category
- `Service Quantity Identifier` (`sqi_desc`)

### Measure
- `Sum of Total Billed Usage` (`total_bill_sq`)

### Companion table
- Rows: `Service Quantity Identifier` (`sqi_desc`), `Unit Of Measure` (`uom_desc`)
- Measures: `Sum of Total Billed Usage` (`total_bill_sq`), `Count of Bill Segment ID` (`bseg_id`)

### Filters
- `Bill Date` (`bill_dt`)
- `Service Type Code` (`sa_type_cd`)
- `Unit Of Measure Code` (`uom_cd`)

### Best use
- Understanding which determinant families are driving billed usage

## View 5: Bill Cycle UOM Monitor
### Visual
- Stacked bar chart

### Category
- `Bill Cycle` (`bill_bill_cyc_desc`)

### Series
- `Unit Of Measure` (`uom_desc`)

### Measure
- `Sum of Total Billed Usage` (`total_bill_sq`)

### Filters
- `Bill Date` (`bill_dt`)
- `Service Type Code` (`sa_type_cd`)
- `Customer Class Code` (`cust_cl_cd`)

### Best use
- Cycle-level operational monitoring of usage mix by unit

## View 6: Determinant Density By Segment
### Visual
- Bar chart

### Category
- `Bill Segment Determinant Count` (`bseg_determinant_count`)

### Measure
- `Count of Bill Segment ID` (`bseg_id`)

### Alternative table
- Rows: `Bill Segment Determinant Count` (`bseg_determinant_count`), `Service Type` (`sa_type_desc`)
- Measures: `Count of Bill Segment ID` (`bseg_id`), `Sum of Total Billed Usage` (`total_bill_sq`)

### Filters
- `Bill Date` (`bill_dt`)
- `Service Type Code` (`sa_type_cd`)
- `Unit Of Measure Code` (`uom_cd`)

### Best use
- Seeing how much of the billed-usage population is multi-determinant

## View 7: Determinant Detail Trace
### Visual
- Table

### Columns
- `Bill Date` (`bill_dt`)
- `Bill ID` (`bill_id`)
- `Bill Segment ID` (`bseg_id`)
- `Account ID` (`acct_id`)
- `Customer Name` (`customer_name`)
- `Service Agreement ID` (`sa_id`)
- `Service Type` (`sa_type_desc`)
- `Unit Of Measure` (`uom_desc`)
- `Time Of Use` (`tou_desc`)
- `Service Quantity Identifier` (`sqi_desc`)
- `Total Billed Usage` (`total_bill_sq`)
- `Total Initial Usage` (`total_init_sq`)
- `SQ Line Count` (`sq_line_count`)

### Filters
- `Bill Date` (`bill_dt`)
- `Bill Segment ID` (`bseg_id`)
- `Account ID` (`acct_id`)
- `Service Agreement ID` (`sa_id`)
- `Unit Of Measure Code` (`uom_cd`)
- `Time Of Use Code` (`tou_cd`)
- `Service Quantity Identifier Code` (`sqi_cd`)

### Sort
- `Bill Date` descending
- Then `Bill Segment ID`

### Best use
- Determinant-level billed usage trace and audit support

## View 8: Segment Exceptions With UOM Context
### Visual
- Table

### Columns
- `Bill Date` (`bill_dt`)
- `Bill Segment ID` (`bseg_id`)
- `Service Type` (`sa_type_desc`)
- `Unit Of Measure` (`uom_desc`)
- `Total Billed Usage` (`total_bill_sq`)
- `Estimated Segment` (`est_sw`)
- `Closing Bill Segment` (`closing_bseg_sw`)
- `Service Quantity Override` (`sq_override_sw`)
- `Item Override` (`item_override_sw`)
- `Cancel Reason` (`can_rsn_desc`)
- `Rebill Segment ID` (`rebill_seg_id`)

### Filters
- `Bill Date` (`bill_dt`)
- `Estimated Segment` (`est_sw`)
- `Service Quantity Override` (`sq_override_sw`)
- `Item Override` (`item_override_sw`)
- `Cancel Reason Code` (`can_rsn_cd`)

### Best use
- Reviewing exception-heavy determinant rows with unit context

## Recommended common prompt set
- `Bill Date` (`bill_dt`)
- `Service Type Code` (`sa_type_cd`)
- `Unit Of Measure Code` (`uom_cd`)
- `Time Of Use Code` (`tou_cd`)
- `Service Quantity Identifier Code` (`sqi_cd`)
- `Bill Cycle Code` (`bill_bill_cyc_cd`)
- `Customer Class Code` (`cust_cl_cd`)
- `Account ID` (`acct_id`)

## Measure guidance
- `Sum of Total Billed Usage` (`total_bill_sq`): default quantity KPI
- `Sum of Total Initial Usage` (`total_init_sq`): supporting pre-bill quantity
- `Count of Bill Segment ID` (`bseg_id`): safest volume KPI
- `SQ Line Count` (`sq_line_count`): structural detail measure, not a usage KPI

## Avoid
- Treating this as a billed-dollar source
- Using `Count of rows` as a replacement for `Count of Bill Segment ID` when segment duplication matters
- Starting with no `Bill Date` filter

For additive billed dollars, stay on `BSEG_BILLED_USAGE_RPT_CURR` or another billed-amount artifact.
