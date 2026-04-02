# Jaspersoft Charts and Visuals for JRS 9

## Purpose
Current reference for chart and visual customization options that are relevant to JasperReports Server 9.x, with an emphasis on which customization layer applies to reports, Ad Hoc views, dashboards, and server UI themes.

Last verified against official Jaspersoft 9.0 documentation: 2026-03-10.

## Customization Layers
### 1. Report Charts in JRXML
Report charts are part of a JRXML report and are rendered by JasperReports Library. These are the right choice when the chart must be pixel-perfect, schedulable, export-safe, and tightly controlled.

Available customization paths:
- JRXML chart properties and element-level styling
- chart themes created in Jaspersoft Studio and packaged as JARs
- chart customizers implemented as Java classes for JFreeChart behavior not directly exposed in the report designer
- HTML5 chart advanced properties in Studio for chart-specific overrides

Best use:
- formal client deliverables
- executive packets
- fixed report bands where layout must not drift

### 2. Ad Hoc Charts
Ad Hoc charts are interactive and are configured in the Ad Hoc Editor. They are designed for exploration and lightweight self-service rather than fixed report design.

Available customization paths:
- Format Visualization panel for labels, legend, axes, and display controls
- Advanced settings for chart properties such as colors, legend alignment, and data labels
- calculated fields and date-grouping functions in the Ad Hoc layer

Best use:
- exploratory dashboards
- analyst self-service
- embedded dashboard content that benefits from user-driven regrouping

### 3. Dashboard Visuals
Dashboards compose reports, Ad Hoc views, and dashboard-native charts/tables/crosstabs into one screen. Some visuals in dashboards are dashlets backed by the embedded Ad Hoc editor.

Available customization paths:
- dashlet layout and parameter mapping
- dashboard input controls as dashlets or pop-up controls
- dashboard chart-type selector behavior
- hyperlink interactions between dashlets

Best use:
- multi-panel operational monitoring
- KPI-to-detail workflows
- shared prompts across several governed views

### 4. Server UI Themes
Server themes change the look of the JRS web application itself through CSS and theme resources. This is branding and UI skinning, not report semantics.

Best use:
- organization branding
- accessibility and contrast adjustments
- embedded/portal-specific UI treatment

### 5. Visualize.js
Visualize.js is the embedding layer for reports, Ad Hoc views, and dashboards in external applications.

Best use:
- custom portals
- application-embedded analytics
- external control of visualization type, filters, sizing, and hyperlinks

## What JRS 9 Adds or Highlights
Official JRS 9.0 release notes call out several features relevant to client-facing visuals:
- drill up and drill down on charts
- hyperlink interactivity for Studio-built reports in dashboards using the `dashlet` hyperlink type
- advanced date-time calculations for Ad Hoc calculated fields
- default visualization type selection for new Ad Hoc views
- new Ad Hoc component behavior that keeps Ad Hoc reports aligned with their parent Ad Hoc view

## Report Chart Customization Best Practices
### Chart Themes
Official Studio docs say chart themes provide full control over JFree chart styling and are the supported way to create reusable visual consistency across reports.

Use chart themes when:
- several JRXML reports should share one visual language
- you want one reusable palette, grid, font, and axis treatment
- client branding should be applied consistently across report charts

Important limit:
- official admin docs state that chart themes do not apply to Ad Hoc chart views

### Chart Customizers
Official Studio docs describe chart customizers as Java classes that change chart appearance and expose JFreeChart functionality not directly available in JasperReports.

Use chart customizers when:
- the required behavior is not available through normal chart properties or themes
- the customization is report-chart specific and justified by delivery value

Avoid by default:
- customizers add code deployment complexity and should be used only when simpler styling paths are not enough

### HTML5 Chart Advanced Properties
Official Studio docs say HTML5 charts expose advanced properties and can accept user-defined properties, often using Highcharts-style property names.

Use when:
- you need chart-level behavior not surfaced in the basic editor
- the chart is in a JRXML report and the property is supported in your target rendering path

Important limit:
- official Studio docs say Ad Hoc chart properties should generally be set on the server, not in Studio

## Ad Hoc Chart Customization Best Practices
### Format Visualization Advanced Settings
Official JRS user guide says the Advanced settings in Format Visualization let you specify custom chart properties for colors, legend placement, data labels, and more.

Key operational facts:
- invalid Ad Hoc chart properties are ignored rather than validated
- property names and values are case-sensitive
- Jaspersoft's advanced chart-formatting knowledge base says 3D options are not supported

Repository default:
- keep Ad Hoc chart formatting limited to properties that improve readability and client usability
- do not push business logic into chart properties
- test no-data, null-heavy, and multi-series cases after every advanced property change

### Calculated Fields in Ad Hoc
JRS 9 adds advanced date-time calculations in Ad Hoc. Use these for presentation-oriented time intelligence when the metric logic is not reconciliation-critical.

Repository default:
- use Ad Hoc calculations for exploration and presentation
- keep source-of-truth financial and operational logic in Oracle SQL or the Domain model

## Dashboard Visual Customization Best Practices
### Shared Controls
Official dashboard docs say a dashboard input control affects only dashlets that reference it.

Repository default:
- use one shared parameter contract across dashlets that should update together
- do not assume every dashlet reacts to every dashboard control

### Embedded Ad Hoc Content
Official dashboard docs say charts, crosstabs, and tables created inside Dashboard Designer are saved as Ad Hoc views and placed into dashlets.

Repository default:
- use dashboard-native Ad Hoc content for lightweight exploratory visuals
- use JRXML reports when the visual must be tightly governed, export-stable, or reusable outside the dashboard

### Chart-Type Selector
Official admin docs say dashboard charts are interactive by default and users can change chart type using the selector unless disabled.

Repository default:
- leave chart-type switching enabled only for exploratory dashboards
- disable it for executive and client-certified dashboards where semantics must stay fixed

### Dashlet Hyperlinks
JRS 9 release notes add a `dashlet` hyperlink type for Studio reports in dashboards so one dashlet can pass values to another.

Repository default:
- use this only when the downstream dashlet is governed and the parameter mapping is explicit
- avoid surprise cross-filtering behavior

## Server Theme Best Practices
Official admin docs describe themes as the server-level mechanism for changing JRS UI appearance, including organization-level variations.

Repository default:
- use themes for application chrome, logos, contrast, and embedded experience
- do not use themes as a substitute for report styling or chart semantics

## Visualize.js Best Practices
Official Visualize.js docs show that:
- `dashboard()` renders dashboards and exposes dashlet structure
- `adhocView()` renders interactive Ad Hoc tables, crosstabs, and charts
- Ad Hoc views can be initialized with visualization type, parameters, hyperlink handlers, and autoresize behavior

Repository default:
- use Visualize.js only when embedding is a real product requirement
- keep repository resources governed first; embed them second

## Best-Practice Decision Guide
### Use a JRXML Report Chart
Best when:
- visual semantics must be fixed
- export fidelity matters
- layout is part of the deliverable

### Use an Ad Hoc Chart
Best when:
- the user needs to change visualization type, grouping, or fields
- speed of iteration matters more than pixel-perfect layout

### Use a Dashboard
Best when:
- multiple governed visuals need one shared operating surface
- controls, drill paths, and comparison views matter more than page-perfect rendering

### Use a Server Theme
Best when:
- the goal is branding or UI look-and-feel across the application, not report content customization

## Repository Rules
- Keep chart calculations in Oracle SQL or Domain logic unless they are strictly presentational.
- For report charts, prefer chart themes before customizers.
- For Ad Hoc charts, prefer built-in formatting before advanced properties.
- Do not assume a customization path applies across artifact types; report chart themes do not carry over to Ad Hoc views.
- Validate every chart in HTML view, export output, and no-data scenarios before signoff.

## Official Sources
- JRS 9.0 release notes:
  - https://community.jaspersoft.com/index.php?app=jasper&controller=pdf&database=8&file=js-jrs_9.0.0_relnotes.pdf&module=view&record=160
- Ad Hoc chart formatting:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-charts-formatting/
  - https://community.jaspersoft.com/knowledgebase/best-practices/advanced-chart-formatting/
- JRS dashboard behavior:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboard-designer-overview/
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-dashboards-_-dashboards-adding-controls/
- Studio chart themes and customizers:
  - https://community.jaspersoft.com/documentation/jaspersoft%C2%AE-studio/tibco-jaspersoft-studio-user-guide/v900/jss-user-_-charts-jfree-_-charts-themes-using/
  - https://community.jaspersoft.com/documentation/jaspersoft%C2%AE-studio/tibco-jaspersoft-studio-user-guide/v900/jss-user-_-charts-jfree-_-charts-customizers/
  - https://community.jaspersoft.com/documentation/jaspersoft%C2%AE-studio/tibco-jaspersoft-studio-user-guide/v900/jss-user-_-charts-html5-_-html5-charts-advanced-formatting/
  - https://community.jaspersoft.com/documentation/jaspersoft%C2%AE-studio/tibco-jaspersoft-studio-user-guide/v900/jss-user-_-jrs-server-_-jss2jrs-uploading-chart-themes/
- Server-level chart/theme configuration:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-administration-guide/v900/jasperreports-server-admin-guide-_-configuration-_-configuring_jasperreports_library/
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-administration-guide/v900/jasperreports-server-admin-guide-_-themes-_-how_themes_work/
- Visualize.js embedding:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-visualizejs-guide/vv900/jasperreports-server-visualizejs-guide-_-ad_hoc_views/
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-visualizejs-guide/vv900/jasperreports-server-visualizejs-guide-_-displaying_dashboards/
