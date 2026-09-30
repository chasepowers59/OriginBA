# FT_RPT_CURR Ad Hoc Build Recipes

Use the `FT_RPT_CURR` Domain or Topic as the starting source.

## Global rules
- Add `Accounting Date` as the first filter in every FT Ad Hoc view.
- Default to a bounded range such as the last 30, 60, or 90 days.
- Use `Current Amount` as the default money measure.
- Use `Payoff Amount` only when the business question is specifically about payoff exposure.
- Use a table for detail views.
- Use a bar chart first for summary comparisons, then save a table companion view.

## View 1: FT Type Volume And Dollars
### Visual
- Vertical bar chart

### Group field
- `Financial Transaction Type`

### Measures
- `Count of Financial Transaction ID`
- `Sum of Current Amount`
- Optional: `Sum of Payoff Amount`

### Filters
- `Accounting Date`
- `Financial Transaction Type`
- `GL Distribution Status`
- `Service Type Code`
- `Bill Cycle Code`

### Sort
- Descending by `Sum of Current Amount`

### Best use
- Quick finance overview of which FT types are driving volume and dollar activity

## View 2: FT Distribution Status Monitor
### Visual
- Stacked bar chart

### Category
- `GL Distribution Status`

### Series
- `Financial Transaction Type`

### Measure
- `Count of Financial Transaction ID`

### Alternative table
- Rows: `GL Distribution Status`, `Financial Transaction Type`
- Measures: `Count of Financial Transaction ID`, `Sum of Current Amount`

### Filters
- `Accounting Date`
- `Financial Transaction Type`
- `Bill Cycle Code`
- `Service Type Code`

### Best use
- Operations view for what is distributed vs not distributed by FT type

## View 3: Service Type FT Summary
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Service Type`
- Columns: `Financial Transaction Type`
- Measures: `Count of Financial Transaction ID`, `Sum of Current Amount`

### Table layout
- Rows: `Service Type`, `Financial Transaction Type`
- Measures: `Count of Financial Transaction ID`, `Sum of Current Amount`

### Filters
- `Accounting Date`
- `GL Distribution Status`
- `Bill Cycle Code`
- `Service Agreement Status Code`

### Best use
- Finance and billing teams comparing FT mix across utilities and SA types

## View 4: Bill Cycle FT Health
### Visual
- Bar chart

### Category
- `Bill Cycle Code`

### Series
- `Financial Transaction Type`

### Measure
- `Sum of Current Amount`

### Companion table
- Rows: `Bill Cycle Code`, `Financial Transaction Type`
- Measures: `Count of Financial Transaction ID`, `Sum of Current Amount`, `Sum of Payoff Amount`

### Filters
- `Accounting Date`
- `GL Distribution Status`
- `Service Type Code`

### Best use
- Cycle-level monitoring of FT activity and unusual spikes

## View 5: Adjustment Trace Detail
### Visual
- Table

### Columns
- `Accounting Date`
- `Financial Transaction ID`
- `Financial Transaction Type`
- `Account ID`
- `Service Agreement ID`
- `Adjustment ID`
- `Adjustment Type`
- `Adjustment Status`
- `Current Amount`
- `Adjustment Amount`
- `Bill ID`
- `Sibling ID`
- `Parent ID`

### Filters
- `Accounting Date`
- `Financial Transaction Type` = `AD`
- `Adjustment ID`
- `Adjustment Type Code`
- `Adjustment Status Code`
- `Account ID`
- `Service Agreement ID`

### Sort
- `Accounting Date` descending
- Then `Financial Transaction ID`

### Best use
- Detailed adjustment research and trace work

## View 6: Payment Segment Trace Detail
### Visual
- Table

### Columns
- `Accounting Date`
- `Financial Transaction ID`
- `Financial Transaction Type`
- `Account ID`
- `Service Agreement ID`
- `Payment Segment ID`
- `Payment ID`
- `Payment Segment Amount`
- `Current Amount`
- `Bill ID`

### Filters
- `Accounting Date`
- `Financial Transaction Type`
- `Payment ID`
- `Payment Segment ID`
- `Account ID`

### Best use
- Payment-linked FT analysis

## View 7: Bill Segment FT Detail
### Visual
- Table

### Columns
- `Accounting Date`
- `Financial Transaction ID`
- `Financial Transaction Type`
- `Bill Segment ID`
- `Bill Segment Status`
- `Bill Segment Start Date`
- `Bill Segment End Date`
- `Service Agreement ID`
- `Service Type`
- `Current Amount`
- `Bill ID`

### Filters
- `Accounting Date`
- `Bill Segment ID`
- `Bill Segment Status Code`
- `Service Type Code`
- `Bill Cycle Code`

### Best use
- Bill-segment-linked FT review

## Recommended common prompt set
For most FT views, use these filters:
- `Accounting Date`
- `Financial Transaction Type`
- `GL Distribution Status`
- `Service Type Code`
- `Bill Cycle Code`
- `Account ID`
- `Service Agreement ID`

## Measure guidance
Use these measures this way:
- `Count of Financial Transaction ID`: safest volume KPI
- `Sum of Current Amount`: default dollar KPI
- `Sum of Payoff Amount`: only when payoff is the business question
- `Sum of Adjustment Amount`: only in adjustment-focused views
- `Sum of Payment Segment Amount`: only in payment-focused views

## Avoid
- Mixing `Adjustment Amount` and `Payment Segment Amount` into broad all-FT summary charts
- Starting with no `Accounting Date` filter
- Using the FT domain for GL-account analysis

For `GL Account`, `Distribution Code`, and `GL Amount` analysis, use `FT_GL_DISTRIBUTION_RPT_CURR` instead.
