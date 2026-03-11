# Domain Business Catalog

## Purpose
This catalog explains what each manual domain provides from a business perspective, how it is different, and which files are now standard vs archived.

Quick picker for business users:
- `DOMAIN_DECISION_MATRIX.md`

## Active Standard Domains (Use These)

### `Billed_Usage_Consumption_Billed_Amount_Perf_6M.xml`
- Business view: billed consumption and billed dollars by customer/account/class/rate with billing status context.
- Answers: usage trends, billed amount trends, billed usage by class/cycle/rate schedule.
- Why active: best detailed billed-usage baseline with bounded window.

### `Billed_Usage_Consumption_Billed_Amount_UltraLean.xml`
- Business view: minimum fields for fast usage and billed amount trending.
- Answers: quick high-level usage and billed amount by key dimensions.
- Why active: fastest fallback when broad domains are too heavy.

### `D1_Usage_Device_Account_Outlier_180D.xml`
- Business view: operational usage (D1) with device/meter and account/customer mapping, no financial amounts.
- Answers: top usage customers/accounts/devices, usage-per-day outliers, device and service-point usage concentration, and explicit device-account associations.
- Why active: purpose-built non-financial usage domain with D1 fact tables, meter/device context, and 180-day analysis window.
- Quantity logic: `USAGE_QTY` prefers aggregated `D1_USAGE_PERIOD_SQ.QUANTITY` (cycle/service quantity) with scalar detail fallback.
- Scope guard: usage rows are constrained to `D2-UsageTransaction` business-object records for consistency with enterprise usage-domain behavior.

### `Billed_Revenue_By_Rate_Component_Perf_6M.xml`
- Business view: billed revenue split by rate schedule and rate component.
- Answers: revenue by rate component, RC type mix, component-level billing drivers.
- Why active: includes rate component semantics and tax/revenue component context.

### `Billed_Revenue_Tax_Lean_Perf_6M.xml`
- Business view: tax-focused billed revenue by rate component type with minimal joins.
- Answers: tax component amounts by accounting date, class, cycle, and rate schedule.
- Why active: fastest tax-capable variant with reduced join footprint.

### `Billed_Revenue_Tax_ULTRA_LEAN_30D.xml`
- Business view: ultra-minimal tax amounts sourced directly from financial tax postings.
- Answers: fast tax amount trends by accounting date, bill segment, account, rate schedule, and FT type.
- Why active: minimum-join tax domain using `C1_BI_FT_VW.FT_GL_TAX_AMT` for true tax-based totals.

### `Usage_Billing_Financial_Bridge_PerfFast_6M.xml`
- Business view: bridges billed usage records to financial transaction aggregates.
- Answers: reconciliation between usage billing and financial postings.
- Why active: strongest performance-oriented bridge pattern.

### `Usage_Billing_Financial_Bridge_No_Derived_UltraSafe.xml`
- Business view: minimal bridge with reduced joins for stability.
- Answers: essential usage-to-financial checks with fewer dimensions.
- Why active: import/performance fallback.

### `Fund_Balance_Final_DB_Validated.xml`
- Business view: detailed GL/fund mapping and fund balance outcomes from validated table path.
- Answers: fund-coded revenue/amount balances, FT status/type and fund mapping quality.
- Why active: most DB-validated detailed fund balance design.

### `Fund_Balance_Monthly_PerfSafe.xml`
- Business view: month-level fund balance summary.
- Answers: monthly trend questions and period-over-period fund movement.
- Why active: best performance for trend analytics at monthly grain.

### `Write_Off_Requirements_Final_DB_Validated.xml`
- Business view: write-off process performance, debt movement, and payment recovery context.
- Answers: active/inactive/completed write-off trends, recovery effectiveness, cycle times.
- Why active: best full write-off model with safer aggregation approach.

### `Collections_Process_Effectiveness_Debt_Reduction_180D.xml`
- Business view: collections process effectiveness using process-level arrears and next-process arrears deltas.
- Answers: which templates/statuses/class segments are reducing overdue debt, how much arrears is reduced, and how quickly follow-up processes occur.
- Why active: one-row-per-process model avoids event-level duplication and is purpose-built for debt-reduction effectiveness.

### `To_Do_Entry_Operations_Account_Resolved.xml`
- Business view: To Do operational workload with resolved FK context (including account fallback from SA) and queue timing metrics.
- Answers: open/working/completed workload by type/role/status/assignee, aged backlog, and account/customer/premise context for To Do records.
- Why active: preserves To Do grain with left-join enrichment and fixes common account-loss issues from FK-only mappings.

### `Billing_Requirements_No_Derived_Full_Logic.xml`
- Business view: expected-vs-actual billing reconciliation by active SA/account/cycle.
- Answers: who should have been billed vs who was billed, cycle mismatches, billing gaps.
- Why active: strongest reconciliation logic in current manual set.

### `Unbilled_Revenue_Snapshot_Perf.xml`
- Business view: daily unbilled revenue estimate by SA/account/class/cycle/rate schedule.
- Answers: current unbilled usage quantity, estimated usage amount, estimated non-usage amount, estimated tax, and total estimated unbilled revenue.
- Why active: single-table snapshot domain for maximum Jasper performance.

## Archived Domains (Do Not Use for New Builds)

### Replaced by newer equivalent (mostly duplicate scope)

#### `Billed_Revenue_By_Rate_Component_Perf.xml`
- Business view: same as active rate-component domain.
- Archived reason: duplicate of active 6M variant except date window.
- Replacement: `Billed_Revenue_By_Rate_Component_Perf_6M.xml`.

#### `Billed_Usage_Consumption_Billed_Amount_Perf.xml`
- Business view: same as active billed-usage detailed domain.
- Archived reason: duplicate of active 6M variant except date window.
- Replacement: `Billed_Usage_Consumption_Billed_Amount_Perf_6M.xml`.

#### `Usage_Billing_Financial_Bridge_No_Derived_Core.xml`
- Business view: usage-to-financial bridge.
- Archived reason: functionally same as PerfFast 6M standard.
- Replacement: `Usage_Billing_Financial_Bridge_PerfFast_6M.xml`.

### Fund balance legacy variants (superseded)

#### `Fund_Balance_Current_Patched_PerfSafe.xml`
- Business view: detailed VW-based fund mapping with lookups.
- Archived reason: superseded by DB-validated detailed domain.
- Replacement: `Fund_Balance_Final_DB_Validated.xml`.

#### `Fund_Balance_Import_Safe_Lookup_Fund.xml`
- Business view: import-safe reduced fund mapping.
- Archived reason: reduced coverage; superseded by validated model.
- Replacement: `Fund_Balance_Final_DB_Validated.xml`.

#### `Fund_Balance_No_Derived_With_Fund_Lookups.xml`
- Business view: detailed VW-based fund mapping baseline.
- Archived reason: superseded by validated model.
- Replacement: `Fund_Balance_Final_DB_Validated.xml`.

#### `Fund_Balance_No_Derived_With_Fund_Lookups_Folderized.xml`
- Business view: same as above with presentation folders.
- Archived reason: uses parser-risk date functions and legacy pattern.
- Replacement: `Fund_Balance_Final_DB_Validated.xml`.

#### `Fund_Balance_OldStructure_BoundedWindow.xml`
- Business view: older detailed VW structure with fixed date range.
- Archived reason: legacy pattern superseded by validated model.
- Replacement: `Fund_Balance_Final_DB_Validated.xml`.

#### `Fund_Balance_OldGL_NoFilter.xml`
- Business view: legacy GL pattern at transaction grain.
- Archived reason: unbounded/no prefilter performance risk.
- Replacement: `Fund_Balance_Final_DB_Validated.xml`.

#### `Fund_Balance_OldGL_ParserSafe.xml`
- Business view: legacy GL pattern with parser-safe filter.
- Archived reason: superseded by validated model.
- Replacement: `Fund_Balance_Final_DB_Validated.xml`.

### Write-off legacy variants (superseded)

#### `Write_Off_Requirements_No_Derived_Core.xml`
- Business view: core write-off KPIs/statuses without full enrichment.
- Archived reason: narrower than final validated model.
- Replacement: `Write_Off_Requirements_Final_DB_Validated.xml`.

#### `Write_Off_Requirements_No_Derived_UltraSafe.xml`
- Business view: minimal write-off fields for very safe imports.
- Archived reason: too limited for most business questions.
- Replacement: `Write_Off_Requirements_Final_DB_Validated.xml`.

#### `Write_Off_Requirements_No_Derived_With_Payments.xml`
- Business view: write-off plus payment chain detail.
- Archived reason: older payment approach; replaced by safer aggregated model.
- Replacement: `Write_Off_Requirements_Final_DB_Validated.xml`.

### Billing requirements legacy variants (superseded)

#### `Billing_Requirements_Adjusted_From_Current.xml`
- Business view: earlier billing reconciliation draft.
- Archived reason: older logic and weaker structure.
- Replacement: `Billing_Requirements_No_Derived_Full_Logic.xml`.

#### `Billing_Requirements_No_Derived_Design.xml`
- Business view: no-derived billing baseline.
- Archived reason: replaced by full expected-vs-actual logic version.
- Replacement: `Billing_Requirements_No_Derived_Full_Logic.xml`.

#### `Billing_Requirements_No_Derived_Full_Logic_UltraSafe.xml`
- Business view: safer fallback form of full-logic billing domain.
- Archived reason: less optimized/less accurate defaults than full logic standard.
- Replacement: `Billing_Requirements_No_Derived_Full_Logic.xml`.
