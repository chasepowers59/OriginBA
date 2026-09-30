# BSEG_BILLED_USAGE_RPT_CURR Ad Hoc Build Recipes

Use the `BSEG_BILLED_USAGE_RPT_CURR` Domain or Topic as the starting source.

## Global rules
- Add `Bill Date` as the first filter in every billed-usage Ad Hoc view.
- Default to a bounded range such as the last 1, 3, or 6 bill months.
- Use `Total Billed Usage` as the default quantity measure.
- Use `Total Billed Amount` as the default billed-dollar proxy at this grain.
- Use a table for bill-segment trace/detail views.
- Use a bar chart first for summary comparisons, then save a table companion view.
- Remember this snapshot is one row per `Bill Segment ID`, not one row per determinant.

## Important grain warning
- `Total Billed Usage` is safe at bill-segment grain.
- `Unit Of Measure`, `Time Of Use`, and `Service Quantity Identifier` are only reliable when the segment has one determinant combination.
- Do not use this domain for full UOM breakdown reporting across mixed segments.
- For true determinant-level quantity analysis, use `BSEG_SQ_USAGE_RPT_CURR` instead.

## View 1: Billed Usage By Service Type
### Visual
- Vertical bar chart

### Category
- `Service Type`

### Measures
- `Sum of Total Billed Usage`
- Optional second measure: `Sum of Total Billed Amount`

### Filters
- `Bill Date`
- `Service Type Code`
- `Utility / Service Category Code`
- `Bill Cycle Code`
- `Customer Class Code`

### Sort
- Descending by `Sum of Total Billed Usage`

### Best use
- High-level billed usage monitoring by service type

## View 2: Bill Cycle Usage And Revenue
### Visual
- Bar chart

### Category
- `Bill Cycle`

### Measures
- `Sum of Total Billed Usage`
- `Sum of Total Billed Amount`

### Filters
- `Bill Date`
- `Service Type Code`
- `Customer Class Code`
- `Collection Class Code`

### Best use
- Cycle-level view of billed usage and billed amount

## View 3: Customer Class Usage Summary
### Visual
- Horizontal bar chart

### Category
- `Customer Class`

### Series
- `Service Type`

### Measure
- `Sum of Total Billed Usage`

### Companion table
- Rows: `Customer Class`, `Service Type`
- Measures: `Sum of Total Billed Usage`, `Sum of Total Billed Amount`, `Count of Bill Segment ID`

### Filters
- `Bill Date`
- `Bill Cycle Code`
- `Utility / Service Category Code`
- `Estimated Segment`

### Best use
- Comparing billed usage across customer segments

## View 4: Segment Determinant Complexity Monitor
### Visual
- Bar chart

### Category
- `Determinant Count`

### Measure
- `Count of Bill Segment ID`

### Alternative table
- Rows: `Determinant Count`, `Service Type`
- Measures: `Count of Bill Segment ID`, `Sum of Total Billed Usage`

### Filters
- `Bill Date`
- `Service Type Code`
- `Bill Cycle Code`

### Best use
- Identifying how much of the billed-usage population is single-determinant vs mixed

## View 5: Single Determinant UOM Review
### Visual
- Table or bar chart

### Table layout
- Rows: `Unit Of Measure`, `Service Type`
- Measures: `Count of Bill Segment ID`, `Sum of Total Billed Usage`

### Required filters
- `Bill Date`
- `Determinant Count` = `1`
- Optional: `Unit Of Measure Code`
- Optional: `Service Type Code`

### Best use
- Safe interim UOM reporting only for single-determinant segments

## View 6: Estimated Segment Monitor
### Visual
- Stacked bar chart

### Category
- `Service Type`

### Series
- `Estimated Segment`

### Measure
- `Count of Bill Segment ID`

### Companion table
- Rows: `Service Type`, `Estimated Segment`
- Measures: `Count of Bill Segment ID`, `Sum of Total Billed Usage`, `Sum of Total Billed Amount`

### Filters
- `Bill Date`
- `Bill Cycle Code`
- `Customer Class Code`

### Best use
- Monitoring estimated billed segments by service type

## View 7: Bill Segment Detail Trace
### Visual
- Table

### Columns
- `Bill Date`
- `Bill ID`
- `Bill Segment ID`
- `Account ID`
- `Customer Name`
- `Service Agreement ID`
- `Service Type`
- `Bill Segment Status`
- `Bill Segment Start Date`
- `Bill Segment End Date`
- `Total Billed Usage`
- `Total Billed Amount`
- `Determinant Count`
- `Unit Of Measure`

### Filters
- `Bill Date`
- `Bill ID`
- `Bill Segment ID`
- `Account ID`
- `Service Agreement ID`
- `Service Type Code`

### Sort
- `Bill Date` descending
- Then `Bill Segment ID`

### Best use
- Segment-level research and audit support

## View 8: Read And Calculation Timing Review
### Visual
- Table

### Columns
- `Bill Date`
- `Bill Segment ID`
- `Service Type`
- `First Read Start Date Time`
- `Last Read End Date Time`
- `First Calculation Effective Date`
- `Last Calculation Effective Date`
- `Read Line Count`
- `Calculation Header Count`
- `Total Measured Quantity`
- `Total Final Register Quantity`

### Filters
- `Bill Date`
- `Service Type Code`
- `Bill Segment ID`
- `Estimated Segment`

### Best use
- Reviewing the read/calc timing context behind billed segments

## View 9: Exception And Rebill Monitor
### Visual
- Table

### Columns
- `Bill Date`
- `Bill Segment ID`
- `Service Type`
- `Bill Segment Status`
- `Cancel Reason`
- `Rebill Segment ID`
- `Cancelled Bill Segment ID`
- `Master Bill Segment ID`
- `Service Quantity Override`
- `Item Override`
- `Closing Bill Segment`
- `Total Billed Usage`
- `Total Billed Amount`

### Filters
- `Bill Date`
- `Cancel Reason Code`
- `Rebill Segment ID`
- `Cancelled Bill Segment ID`
- `Service Quantity Override`
- `Item Override`

### Best use
- Billed-usage exception and rebill analysis

## Recommended common prompt set
For most billed-usage views, use these filters:
- `Bill Date`
- `Service Type Code`
- `Utility / Service Category Code`
- `Bill Cycle Code`
- `Customer Class Code`
- `Collection Class Code`
- `Account ID`
- `Service Agreement ID`

## Measure guidance
Use these measures this way:
- `Sum of Total Billed Usage`: default quantity KPI
- `Sum of Total Billed Amount`: default billed-dollar proxy at segment grain
- `Count of Bill Segment ID`: safest volume KPI
- `Sum of Total Measured Quantity` and `Sum of Total Final Register Quantity`: supporting operational measures, not the primary billed-usage KPI
- `Service Quantity Line Count`, `Read Line Count`, `Calculation Header Count`, and `Determinant Count`: structural diagnostics, not dollar or usage KPIs

## Avoid
- Treating `Service Type` as a guaranteed unit family
- Using `Unit Of Measure` without controlling for `Determinant Count = 1`
- Starting with no `Bill Date` filter
- Using this domain for determinant-level UOM / TOU / SQI reporting

For true unit-level billed usage analysis, use `BSEG_SQ_USAGE_RPT_CURR` instead.
