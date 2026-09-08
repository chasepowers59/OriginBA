# FT_GL_DISTRIBUTION_RPT_CURR Ad Hoc Build Recipes

Use the `FT_GL_DISTRIBUTION_RPT_CURR` Domain or Topic as the starting source.

## Global rules
- Add `Accounting Date` as the first filter in every GL-line Ad Hoc view.
- Default to a bounded range such as the last 30, 60, or 90 days.
- Use `GL Amount` as the default financial measure.
- Use `Statistic Amount` only when the business question is specifically about the statistic quantity/amount field.
- Use a table for trace/detail views.
- Use a bar chart first for summary comparisons, then save a table companion view.
- Do not sum `Current Amount` or `Payoff Amount` as if they were GL-line-additive measures. Those repeat across multiple GL lines by design.

## View 1: GL Account By FT Type
### Visual
- Vertical bar chart

### Category
- `GL Account`

### Series
- `Financial Transaction Type`

### Measure
- `Sum of GL Amount`

### Filters
- `Accounting Date`
- `GL Account`
- `Financial Transaction Type`
- `GL Distribution Status`
- `Bill Cycle Code`
- `Service Type Code`

### Sort
- Descending by `Sum of GL Amount`

### Best use
- Fast view of which FT types are feeding each GL account

## View 2: Distribution Code Mix
### Visual
- Horizontal bar chart

### Category
- `Distribution Code`

### Series
- `Financial Transaction Type`

### Measure
- `Sum of GL Amount`

### Companion table
- Rows: `Distribution Code`, `Financial Transaction Type`
- Measures: `Count of Financial Transaction ID`, `Sum of GL Amount`, `Sum of Statistic Amount`

### Filters
- `Accounting Date`
- `Distribution Code ID`
- `GL Account`
- `Financial Transaction Type`
- `Service Type Code`

### Best use
- Understanding which distribution codes drive posted GL amounts

## View 3: GL Distribution Status Monitor
### Visual
- Stacked bar chart

### Category
- `GL Distribution Status`

### Series
- `Financial Transaction Type`

### Measure
- `Sum of GL Amount`

### Alternative table
- Rows: `GL Distribution Status`, `Financial Transaction Type`
- Measures: `Count of Financial Transaction ID`, `Sum of GL Amount`

### Filters
- `Accounting Date`
- `GL Division`
- `Bill Cycle Code`
- `Service Type Code`

### Best use
- Operational monitor for distributed vs non-distributed GL activity

## View 4: Service Type And GL Account Summary
### Visual
- Crosstab or table

### Crosstab layout
- Rows: `Service Type`
- Columns: `GL Account`
- Measure: `Sum of GL Amount`

### Table layout
- Rows: `Service Type`, `GL Account`
- Measures: `Sum of GL Amount`, `Count of Financial Transaction ID`

### Filters
- `Accounting Date`
- `Financial Transaction Type`
- `Bill Cycle Code`
- `Customer Class Code`

### Best use
- Finance and billing review of how service lines feed different accounts

## View 5: Bill Cycle GL Summary
### Visual
- Bar chart

### Category
- `Bill Cycle`

### Series
- `GL Account`

### Measure
- `Sum of GL Amount`

### Companion table
- Rows: `Bill Cycle`, `GL Account`
- Measures: `Sum of GL Amount`, `Sum of Statistic Amount`, `Count of Financial Transaction ID`

### Filters
- `Accounting Date`
- `Financial Transaction Type`
- `Distribution Code ID`
- `Service Type Code`

### Best use
- Cycle-level accounting pattern review and unusual variance detection

## View 6: Adjustment To GL Trace
### Visual
- Table

### Columns
- `Accounting Date`
- `Financial Transaction ID`
- `GL Sequence Number`
- `GL Account`
- `Distribution Code`
- `GL Amount`
- `Account ID`
- `Service Agreement ID`
- `Adjustment ID`
- `Adjustment Type`
- `Adjustment Status`
- `Transfer Adjustment ID`
- `Customer Name`
- `Bill ID`

### Filters
- `Accounting Date`
- `Financial Transaction Type` = `AD`
- `Adjustment ID`
- `Adjustment Type Code`
- `Adjustment Status Code`
- `GL Account`
- `Account ID`

### Sort
- `Accounting Date` descending
- Then `Financial Transaction ID`
- Then `GL Sequence Number`

### Best use
- Detailed adjustment-to-GL reconciliation and trace work

## View 7: Payment Segment To GL Trace
### Visual
- Table

### Columns
- `Accounting Date`
- `Financial Transaction ID`
- `GL Sequence Number`
- `GL Account`
- `Distribution Code`
- `GL Amount`
- `Payment Segment ID`
- `Payment ID`
- `Payment Segment Amount`
- `Account ID`
- `Service Agreement ID`
- `Bill ID`

### Filters
- `Accounting Date`
- `Payment ID`
- `Payment Segment ID`
- `GL Account`
- `Financial Transaction Type`

### Best use
- Payment-linked GL detail research

## View 8: FT Header To GL Detail
### Visual
- Table

### Columns
- `Accounting Date`
- `Financial Transaction ID`
- `Financial Transaction Type`
- `GL Sequence Number`
- `GL Account`
- `Distribution Code`
- `GL Amount`
- `Statistic Amount`
- `Current Amount`
- `Payoff Amount`
- `GL Distribution Status`
- `Freeze Date Time`
- `Freeze User Name`

### Filters
- `Accounting Date`
- `Financial Transaction ID`
- `Financial Transaction Type`
- `GL Account`
- `Distribution Code ID`

### Best use
- Reconciling the FT header to its posted GL lines

## Recommended common prompt set
For most FT/GL views, use these filters:
- `Accounting Date`
- `GL Account`
- `Distribution Code ID`
- `Financial Transaction Type`
- `GL Distribution Status`
- `Bill Cycle Code`
- `Service Type Code`
- `Account ID`

## Measure guidance
Use these measures this way:
- `Sum of GL Amount`: default additive financial measure
- `Sum of Statistic Amount`: secondary additive measure when statistic logic matters
- `Count of Financial Transaction ID`: safest volume KPI
- `Current Amount` and `Payoff Amount`: display-only context in GL-line views, not default additive measures
- `Adjustment Amount` and `Payment Segment Amount`: use only in trace-specific views

## Avoid
- Summing `Current Amount` or `Payoff Amount` in broad GL-line summaries
- Starting with no `Accounting Date` filter
- Using this domain for one-row-per-FT analytics

For unduplicated FT-header analysis, use `FT_RPT_CURR` instead.
