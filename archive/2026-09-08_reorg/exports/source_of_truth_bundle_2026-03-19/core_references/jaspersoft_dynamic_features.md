# Jaspersoft Dynamic Features

## Purpose
Quick reference for the dynamic Jaspersoft capabilities that matter most for client-facing reporting in this repository: dashboards, Ad Hoc views, Domains/Topics, prompt behavior, drill paths, and optional embedding.

## Use Order
Prefer these in order when you need more interactivity:
1. Standard report parameters plus matching input controls.
2. Dashboard-level input controls shared across multiple dashlets.
3. Domain pre-filters and Topics for safe Ad Hoc self-service.
4. Ad Hoc calculated fields for lightweight client-facing formulas.
5. Hyperlinks and drill paths for KPI-to-detail navigation.
6. Visualize.js only when the client needs embedded delivery outside JasperReports Server.

## Feature Guidance
### Dashboard Input Controls
Best for synchronized filters across multiple dashlets. Use one shared parameter contract instead of creating slightly different controls per report.

Use when:
- several dashlets answer one operational question
- a single date or client filter should update the full dashboard
- the same controls should be reused in HTML and PDF dashboard views

Avoid when:
- only one report needs the filter
- the filter logic is highly dependent and would be better handled as cascading controls or a pre-filtered Topic

Official references:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-adding-controls/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-input-control-tips/

### Query-Based and Cascading Input Controls
Use when the value list must come from repository data or when a downstream prompt depends on a parent choice.

Use when:
- bill cycle, premise, or account lists must be data-driven
- the child selector must narrow after a parent selection

Avoid when:
- a plain text, number, date, or boolean prompt is sufficient
- the dynamic lookup would add complexity without improving usability

Official references:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-administration-guide/v900/jasperreports-server-admin-guide-_-resources-_-query-based_input_controls/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-reports-_-reports-cascading-input-controls/

### Domain Topics and Ad Hoc Pre-Filters
Use Topics to expose a governed subset of a larger Domain. Use pre-filters to restrict rows before the user starts building the Ad Hoc view.

Use when:
- client self-service must start from a curated slice
- users should not see every field from a wide Domain
- row restriction should be applied before interactive filtering

Avoid when:
- the use case is a fixed-layout operational report
- the domain has not been validated for row-level scope and metric correctness

Official references:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-data-chooser/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-create-topic-from-domain/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-create-view-from-domain/

### Ad Hoc Calculated Fields and Measures
Use for lightweight formulas that improve analyst self-service, such as ratios, buckets, labels, and simplified score logic.

Use when:
- the formula is presentation-oriented
- analysts need to regroup or recalculate inside the Ad Hoc layer

Avoid when:
- the formula changes source-of-truth totals
- the logic belongs in governed Oracle SQL for parity and auditability

Official reference:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-calc-fields-reference/

### Drill Paths and Hyperlinks
Use to move users from summary KPIs to governed detail reports or dashboards. This is the preferred navigation model for executive-to-operational workflows.

Use when:
- a KPI needs an accountable drill target
- an exception tile should open a detail report filtered to the same slice

Avoid when:
- the destination asset is not governed or not yet validated
- the hyperlink would cross into an unrelated workflow with different semantics

Official references:
- https://community.jaspersoft.com/applications/cms/interface/file/file.php?database=8&file=js-jrs_9.0.0_relnotes.pdf&module=view&record=160
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-working/

### Visualize.js
Use when reports or dashboards must be embedded into a client portal, custom web app, or another controlled UI. It is optional and should not replace standard repository delivery without a clear integration need.

Use when:
- the client wants embedded reports or dashboards in an external application
- the consuming application must set or read parameters programmatically

Avoid when:
- a normal JasperReports Server repository workflow is sufficient
- the project does not need custom application integration

Official references:
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-get-embed-code/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-reports-_-reports-get-embed-code/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-visualizejs-guide/vv900/jasperreports-server-visualizejs-guide-_-displaying_dashboards/
- https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-visualizejs-guide/vv900/jasperreports-server-visualizejs-guide-_-input_controls/

## Repository Defaults
- Default to repository-managed reports, dashboards, and Ad Hoc views before considering Visualize.js.
- Default to simple input controls before query-based or cascading controls.
- Default to Domain Topics and pre-filters before exposing broad Domains to self-service users.
- Default to governed SQL for source-of-truth business logic; use Ad Hoc calculations for presentation-layer flexibility.
