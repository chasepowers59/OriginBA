# C2M + Jaspersoft Delivery Playbook

## Purpose
Canonical operating guide for Oracle C2M reporting work in this repository. Use this playbook when producing optimized SQL, Jaspersoft Domains/derived tables, JRXML reports, dashboards, and Ad Hoc views for client delivery.

## Repository Operating Model
- Default to Domain-first JRXML using `language="domain"` unless raw SQL is explicitly requested or the domain cannot support the requirement safely.
- Never embed credentials in JRXML, SQL, scripts, or deployment payloads.
- Use datasource aliases only:
  - `ORIGIN_DEV_DS`
  - `C2M_QA_DS`
  - `C2M_PROD_DS`
- Preserve org isolation with `Origin_DEV` as the default source context.
- Maintain matching input controls under `server/input_controls/` for any report or dashboard parameter change.
- Treat these as source of truth before writing new assets:
  - `output/workstream_reporting_dictionary.json`
  - `Domain Designs.xlsx`
  - exported domain schema files when available

## Official Product Guidance vs Repository Standard
Official Jaspersoft Studio 9.0 documentation says `jasperQL` is the default query language for new domain reports and is recommended for new report authoring. This repository intentionally keeps `language="domain"` as the default contract because existing production-safe assets, validation rules, and server deployment workflows are already built around domain-language JRXML and explicit `<queryFields>`.

Use `jasperQL` only when there is a clear feature gap that cannot be met with the current domain-language standard and the report can still satisfy this repository's validation contract.

Official reference:
- https://community.jaspersoft.com/documentation/jaspersoft%C2%AE-studio/tibco-jaspersoft-studio-user-guide/v900/jss-user-_-jrs-server-_-jss2jrs-domains/

## Request Contract
Every new request should be normalized into this intake shape before implementation:
- `Business Objective`: the client question or operating decision the asset must support.
- `Deliverable Type`: `sql`, `domain`, `jrxml`, `dashboard`, or `adhoc`.
- `Primary Subject Area`: billing, finance, field ops, meter ops, debt management, customer ops, or another governed workstream.
- `Target Grain`: cycle, account, segment, service agreement, service point, device, field task, or transaction.
- `Metric Definitions`: authoritative source table and business meaning for each KPI.
- `Filters / Prompts`: exact parameter names, data types, defaults, and whether each filter is optional.
- `Validation Slice`: known account, bill cycle, date range, or batch slice used for parity testing.
- `Environment Target`: DEV, QA, PROD, or promotion path across all three.
- `Consumer`: internal analyst, operational leader, executive, or client self-service user.

## Delivery Decision Rules
### Optimized SQL
Use when business logic needs to be proven, benchmarked, reconciled, or prepared for a derived table/domain.

Required design rules:
- Read-only SQL only.
- No `SELECT *`.
- Deterministic column list with stable aliases.
- Follow `knowledge_base/oracle_c2m_query_patterns.md`.
- Use authoritative C2M source tables for the target metric.
- Do not hardcode bill cycle lists or tenant-specific values unless intentionally scoped and documented.
- Expose filterable fields when Jaspersoft parser safety matters more than embedded bind logic.

### Domains and Derived Tables
Use when the semantic layer needs to support multiple reports, dashboards, or Ad Hoc views from one governed dataset.

Required design rules:
- Query must be parser-safe and begin with `SELECT`.
- Avoid trailing semicolons and parser-fragile bind syntax.
- Prefer reusable filter fields over embedding parameter logic in the SQL.
- Keep output fields stable for report bindings and Ad Hoc consumption.
- Use Topics when client self-service should start from a narrower curated subset of a larger Domain.
- Do not assume derived tables are automatically faster; use them when they fix grain, control fan-out, or simplify a risky join graph.
- If raw Domain joins could duplicate or drop the driving population, establish the grain in Oracle first and expose that result to the Domain.

### JRXML Reports
Use for client-facing pixel-perfect reports, operational packets, printable statements, and scheduled outputs.

Required design rules:
- Keep 9.x-safe top-level ordering.
- Use domain item IDs only in domain queries.
- Keep non-empty `<queryFields>`.
- Keep styles self-contained unless there is an explicit reusable template already in the repository.
- Match parameter names exactly with input control IDs.

### Dashboards
Use when users need a multi-panel operational view with synchronized filters and drill paths across related reports.

Required design rules:
- Use shared parameter names across dashlets whenever filters should update together.
- Prefer dashboard input controls over duplicating filters inside each dashlet.
- Use a popup input control dashlet when the canvas is crowded.
- Use hyperlinks only when they land on a governed downstream report, dashboard, or URL with a clear workflow reason.

### Ad Hoc Views
Use for analyst or client self-service when users need slicing, grouping, sorting, and visualization changes without JRXML edits.

Required design rules:
- Put row-scoping logic into Domain security or pre-filters first.
- Use Topics for curated starting points.
- Use calculated fields/measures for presentation and lightweight formulas, not for source-of-truth reconciliation logic.
- Keep field names business-readable and consistent with the repository dictionary.
- Treat Ad Hoc cache and data staging as performance features with freshness tradeoffs, not invisible implementation details.

## Jaspersoft Dynamic Features To Use Deliberately
### Dashboard Input Controls
Use dashboard-level input controls when several dashlets share the same prompt contract. This is the default dynamic-filter pattern for operational dashboards in this repository.

Official references:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-adding-controls/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-input-control-tips/

### Cascading and Query-Based Input Controls
Use only when a child value list genuinely depends on the parent selection and static text/date/number controls are not sufficient. Prefer simple controls first because they are easier to validate and deploy.

Official references:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-administration-guide/v900/jasperreports-server-admin-guide-_-resources-_-query-based_input_controls/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-reports-_-reports-cascading-input-controls/

### Domain Topics and Ad Hoc Pre-Filters
Use Domain Topics when client self-service should start from a safe subset of fields and filters. Use pre-filters to restrict rows before the user begins designing the Ad Hoc view.

Official references:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-data-chooser/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-create-topic-from-domain/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-create-view-from-domain/

### Calculated Fields and Measures
Use for business-readable labels, bucketing, ratios, and lightweight formulas that improve client self-service. Do not move core accounting logic or reconciliation-critical calculations out of governed SQL just to make an Ad Hoc view more flexible.

Official reference:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-calc-fields-reference/

### Drill Paths and Hyperlink Navigation
Use chart drill and dashlet/report hyperlinks to move from KPI summary to governed detail. Use them only when the landing asset already exists or is part of the same delivery scope.

Official references:
- https://community.jaspersoft.com/applications/cms/interface/file/file.php?database=8&file=js-jrs_9.0.0_relnotes.pdf&module=view&record=160
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-working/

### Visualize.js Embedding
Use only when the client needs the report, dashboard, or Ad Hoc view embedded in a custom application or portal. This is an advanced integration path, not the default delivery model for repository-managed assets.

Official references:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-get-embed-code/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-reports-_-reports-get-embed-code/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-visualizejs-guide/vv900/jasperreports-server-visualizejs-guide-_-input_controls/

## Required Output Contract
For any delivery that changes logic, presentation, or prompts, produce the applicable set below:
- SQL under `sql/` when logic is introduced or changed.
- JRXML under `reports/` when a report is introduced or changed.
- Matching JSON under `server/input_controls/` for any parameterized report or dashboard.
- Documentation updates under `docs/` or `knowledge_base/` when behavior, structure, or semantics change.
- Validation notes that state what was tested, what passed, and any residual caveats.

## Required Validation Before Done
### JRXML
- XML parse succeeds.
- No forbidden chart-tag or schema-ordering issues.
- Domain query includes non-empty `<queryFields>`.
- Input control JSON parses and matches parameter names.

### SQL and Derived Tables
- Query is read-only and parser-safe for the intended path.
- Source-of-truth validation passes where the repository has a governed validator.
- Parity or reconciliation slice is documented when totals matter.

### Dashboards and Ad Hoc Views
- Filters update the intended dashlets or view state.
- Pre-filters and Topics restrict data as intended.
- Calculated fields behave as expected for the agreed validation slice.
- Any hyperlink or drill path lands on the correct governed asset.

## Default Build Sequence
1. Confirm source-of-truth tables and field availability from the dictionary, workbook, and domain export.
2. Write or refine the Oracle SQL logic and validate it against a known slice.
3. Convert the logic into a derived table or domain-safe query shape when the semantic layer needs it.
4. Build the JRXML, dashboard, or Ad Hoc artifact with the same parameter contract.
5. Add or update input controls.
6. Validate XML, JSON, parser safety, and parity.
7. Update docs when semantics, structure, or workflow changed.

## Supporting Repository Guides
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/jaspersoft_charts_visuals_jrs9.md`
- `docs/jaspersoft_domain_report_build_standards.md`
- `docs/template_authoring_playbook.md`
- `docs/sql_jaspersoft_workflow_implementation.md`
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`
- `knowledge_base/jaspersoft_dynamic_features.md`
- `knowledge_base/validation_playbook.md`
