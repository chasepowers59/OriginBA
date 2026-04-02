# D1_MSRMT_RPT_CURR Ad Hoc Build Recipes

Use the Domain or Topic backed by `D1_MSRMT_RPT_CURR` as the starting source.

## Global rules
- Add `Measurement Date/Time` (`msrmt_dttm`) as the first filter in every view.
- Default to a bounded recent window such as the last 7, 30, or 90 days.
- This is one row per processed measurement at `MEASR_COMP_ID + MSRMT_DTTM`.
- Use a table for lineage, exception, and device trace views.
- Use bar charts for status/use/condition summaries.

## View 1: Measurement Status Monitor
### Visual
- Vertical bar chart

### Category
- `Measurement Status` (`msrmt_bo_status_desc`)

### Measure
- `Count of Measurement Rows`

### Series
- Optional: `Measurement Use` (`msrmt_use_desc`)

### Filters
- `Measurement Date/Time` (`msrmt_dttm`)
- `Measurement Status Code` (`msrmt_bo_status_cd`)
- `Measurement Cycle` (`msrmt_cyc_cd`)
- `Route` (`msrmt_cyc_rte_cd`)

### Best use
- Operational monitor of processed measurement volume by status

## View 2: Measurement Condition Profile
### Visual
- Horizontal bar chart

### Category
- `Measurement Condition` (`msrmt_cond_desc`)

### Measure
- `Count of Measurement Rows`

### Filters
- `Measurement Date/Time` (`msrmt_dttm`)
- `Measurement Use` (`msrmt_use_desc`)
- `Service Point ID` (`d1_sp_id`)
- `Measuring Component ID` (`measr_comp_id`)

### Best use
- Monitoring estimated, suspect, or special-condition measurement populations

## View 3: Measurement Use By Route
### Visual
- Stacked bar chart

### Category
- `Route` (`msrmt_cyc_rte_desc`)

### Series
- `Measurement Use` (`msrmt_use_desc`)

### Measure
- `Count of Measurement Rows`

### Filters
- `Measurement Date/Time` (`msrmt_dttm`)
- `Measurement Cycle` (`msrmt_cyc_desc`)
- `Measurement Status Code` (`msrmt_bo_status_cd`)

### Best use
- Route-level work pattern review by measurement use type

## View 4: Read Value Summary By Service Point
### Visual
- Table or bar chart

### Table layout
- Rows: `Service Point ID` (`d1_sp_id`)
- Measures: `Count of Measurement Rows`, `Sum of Measurement Value` (`msrmt_val`), `Sum of Reading Value` (`reading_val`)

### Filters
- `Measurement Date/Time` (`msrmt_dttm`)
- `Service Point ID` (`d1_sp_id`)
- `Measurement Use` (`msrmt_use_desc`)
- `Measurement Condition` (`msrmt_cond_desc`)

### Best use
- Reviewing read totals by service point

## View 5: Measuring Component Health
### Visual
- Table

### Columns
- `Measuring Component ID` (`measr_comp_id`)
- `Measuring Component Type` (`measr_comp_type_desc`)
- `Measuring Component Usage` (`measr_comp_usage_desc`)
- `Latest Measurement Date/Time` (`latest_msrmt_dttm`)
- `Most Recent Measurement Date/Time` (`most_recent_msrmt_dttm`)
- `Most Recent Non-Estimated Measurement Date/Time` (`most_recent_non_est_msrmt_dttm`)
- `Most Recent Reading Value` (`most_recent_msrmt_reading_val`)
- `Most Recent Reading Condition` (`most_recent_msrmt_reading_cond_desc`)
- `Measurement Count`

### Measures
- `Count of Measurement Rows`

### Filters
- `Measurement Date/Time` (`msrmt_dttm`)
- `Measuring Component ID` (`measr_comp_id`)
- `Measuring Component Type Code` (`measr_comp_type_cd`)
- `Measuring Component Usage Code` (`measr_comp_usage_flg`)

### Best use
- Device/component operational review

## View 6: IMD Lineage Review
### Visual
- Table

### Columns
- `Measurement Date/Time` (`msrmt_dttm`)
- `Measuring Component ID` (`measr_comp_id`)
- `Original Initial Measurement Data ID` (`orig_init_msrmt_id`)
- `Initial Measurement Data ID` (`init_msrmt_data_id`)
- `IMD External ID` (`imd_ext_id`)
- `IMD From Date/Time` (`imd_from_dttm`)
- `IMD To Date/Time` (`imd_to_dttm`)
- `Data Source` (`data_src_desc`)
- `IMD Status` (`imd_bo_status_desc`)

### Filters
- `Measurement Date/Time` (`msrmt_dttm`)
- `IMD External ID` (`imd_ext_id`)
- `Data Source` (`data_src_flg`)
- `Measuring Component ID` (`measr_comp_id`)

### Best use
- Tracing processed measurements back to inbound IMD lineage

## View 7: Install Event Context Review
### Visual
- Table

### Columns
- `Measurement Date/Time` (`msrmt_dttm`)
- `Measuring Component ID` (`measr_comp_id`)
- `Install Event ID` (`install_evt_id`)
- `Install Date/Time` (`install_dttm`)
- `Removal Date/Time` (`removal_dttm`)
- `Service Point ID` (`d1_sp_id`)
- `Measurement Cycle` (`msrmt_cyc_desc`)
- `Route` (`msrmt_cyc_rte_desc`)
- `Address` (`address1`)
- `City` (`city`)
- `State` (`state`)

### Filters
- `Measurement Date/Time` (`msrmt_dttm`)
- `Service Point ID` (`d1_sp_id`)
- `Install Event ID` (`install_evt_id`)
- `Measurement Cycle` (`msrmt_cyc_cd`)

### Best use
- Validating install-event context resolved at the time of measurement

## View 8: User Edited Measurement Exceptions
### Visual
- Table

### Columns
- `Measurement Date/Time` (`msrmt_dttm`)
- `Measuring Component ID` (`measr_comp_id`)
- `User Edited Flag` (`user_edited_flg`)
- `User Edited Description` (`user_edited_desc`)
- `Measurement Condition` (`msrmt_cond_desc`)
- `Reading Condition` (`reading_cond_desc`)
- `Measurement Value` (`msrmt_val`)
- `Reading Value` (`reading_val`)
- `Measurement Created Date/Time` (`msrmt_cre_dttm`)
- `Measurement Status Updated Date/Time` (`msrmt_status_upd_dttm`)

### Filters
- `Measurement Date/Time` (`msrmt_dttm`)
- `User Edited Flag` (`user_edited_flg`)
- `Measurement Condition` (`msrmt_cond_flg`)
- `Reading Condition` (`reading_cond_flg`)

### Best use
- Reviewing edited or exception-heavy measurements

## Recommended common prompt set
- `Measurement Date/Time` (`msrmt_dttm`)
- `Measuring Component ID` (`measr_comp_id`)
- `Service Point ID` (`d1_sp_id`)
- `Measurement Cycle` (`msrmt_cyc_cd`)
- `Route` (`msrmt_cyc_rte_cd`)
- `Measurement Status Code` (`msrmt_bo_status_cd`)
- `Measurement Use Code` (`msrmt_use_flg`)
- `Measurement Condition Code` (`msrmt_cond_flg`)

## Measure guidance
- `Count of Measurement Rows`: safest volume KPI
- `Sum of Measurement Value` (`msrmt_val`): default numeric read/value summary
- `Sum of Reading Value` (`reading_val`): supporting read-value measure
- `Combined Multiplier` (`combined_multiplier`) and `Measuring Component Multiplier` (`measr_comp_multiplier`): context fields, not default additive KPIs

## Avoid
- Treating this as a usage-transaction source
- Starting with no `Measurement Date/Time` filter
- Mixing IMD lineage, service point, and component summaries without being explicit about the question

For derived usage process reporting, use `D1_USAGE_RPT_CURR` instead.
