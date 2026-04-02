# Jaspersoft Artifact Model and Performance

## Purpose
Working reference for choosing the right Jaspersoft artifact and the right data-shaping strategy in JasperReports Server 9.x without dropping needed rows or creating avoidable performance problems.

Last verified against official Jaspersoft 9.0 documentation: 2026-03-10.

## What Each Artifact Is
### Domain
A Domain is a semantic layer over a data source. Jaspersoft describes it as a virtual view that presents data in business terms and supports localization and data-level security.

Use a Domain when:
- multiple reports, dashboards, or Ad Hoc views should share one governed model
- business users need readable field names instead of raw table/column names
- row-level or column-level security must be enforced in the semantic layer

### Topic
A Topic is a prepared Ad Hoc source. It can be created from JRXML or from a Domain. It is narrower than a Domain and is useful when self-service users should start from a curated subset of fields and filters.

Use a Topic when:
- you want self-service to begin from a safe subset
- users do not need the full Domain structure
- data staging or pre-filtered Ad Hoc performance matters

### Ad Hoc View
An Ad Hoc view is an interactive table, chart, or crosstab created from a Domain, Topic, or OLAP connection. It is the analysis layer for slicing, grouping, pivoting, filtering, and visualization changes.

Use an Ad Hoc view when:
- the user needs exploration and self-service
- layout does not have to be pixel-perfect
- the main value is interactive analysis, not print-grade formatting

### Report
A report in JasperReports Server is a JasperReport/report unit built from JRXML plus its linked resources. It is the production rendering layer for pixel-perfect output, scheduling, exports, and governed presentation.

Use a report when:
- layout must be stable every run
- the output will be scheduled, printed, exported, or embedded in a formal workflow
- you need subreports, fixed headers/footers, precise pagination, or controlled expressions

### Dashboard
A dashboard is a single-page composition of dashlets. Dashlets can be reports, Ad Hoc views, charts, tables, crosstabs, images, text, web content, and filters.

Use a dashboard when:
- several governed visualizations must be consumed together
- one set of prompts should drive multiple views
- users need KPI-to-detail navigation in one screen

## How JRS Runs Data
### Report Units
In JRS, a JasperReport/report unit aggregates the main JRXML, data source, input controls, query resource, subreports, and other file resources. The server can override the main root-level query of the JRXML during upload, but that override does not change subdataset queries.

Repository implication:
- if a table component or chart uses a subdataset, changing the report-unit query alone will not change that subdataset

### Domains and Ad Hoc
Domains expose joined tables and derived tables as a semantic model. Ad Hoc views sit on top of that model. Official docs note that, depending on configuration, JRS may load an entire Topic, Domain, or OLAP result set into memory while editing or running the view.

Repository implication:
- large unfiltered Ad Hoc sources are risky even when the underlying SQL is correct
- pre-filters, Topics, and bounded date windows are not optional on large CISADM facts

### Ad Hoc Query Optimization and Cache
JRS has Ad Hoc data policies that can rewrite JDBC- and Domain-based queries so filtering, grouping, sorting, and aggregation happen in the database instead of in memory. If the optimization settings are disabled, those steps can happen in memory instead.

JRS also caches Ad Hoc datasets. This can improve performance, but cached data can become stale until refreshed or cleared. Domain Topics can also use data staging, which stores the entire staged dataset in Ad Hoc cache and stops using Domain-based query optimizations for that staged topic.

Repository implication:
- performance testing has to distinguish live-query behavior from cached behavior
- for reconciliation or same-day operational monitoring, validate whether cache or data staging could hide fresh rows

## Choosing Raw Tables vs Derived Tables
### Raw Tables in the Domain Designer
Prefer raw tables and explicit Domain joins when:
- the business grain is already stable in the source tables
- joins are straightforward and do not create fan-out
- the same base model will power multiple self-service use cases
- you need Domain security, localization, or item curation more than SQL reshaping

Advantages:
- clearer lineage to source tables
- easier reuse across reports and Ad Hoc views
- easier to expose optional dimensions without rewriting SQL

Risks:
- circular joins and ambiguous join paths
- row multiplication from one-to-many or many-to-many joins
- accidental row loss from inner joins on optional tables

### Derived Tables
Prefer a derived table when:
- the business grain must be fixed before it reaches the Domain
- the logic needs pre-aggregation, de-duplication, windowing, or a controlled driving set
- the Domain join graph would otherwise be ambiguous or lossy
- complex filters should run in SQL before data reaches the semantic layer

Advantages:
- one stable row shape for downstream reports and Ad Hoc
- simpler join tree in the Domain
- easier parity testing against Oracle SQL

Risks:
- derived tables are not automatically faster
- official Jaspersoft guidance confirms that large or complex derived tables can slow Domain loading because the server validates the queries
- parser limitations still apply in Domain Designer

## Repository Default for C2M
Repository standard, derived from official Jaspersoft behavior plus CISADM row-preservation risk:
- use raw tables in Domains only when the join graph preserves the intended grain without fan-out
- use a derived table when the Domain would otherwise duplicate rows, lose rows, or depend on ambiguous paths
- for reconciliation-critical outputs, fix the grain in Oracle first, then expose the result set to Jaspersoft

This means derived tables are the safer default for:
- latest-event logic
- expected-vs-actual comparisons
- one-row-per-account or one-row-per-bill-cycle KPI layers
- situations where status or lookup joins can multiply fact rows

## Join Design Rules That Protect Rows
### Join Type
Official Domain documentation defines join behavior this way:
- inner join keeps only matching rows
- left outer join keeps all rows from the left table
- right outer join keeps all rows from the right table
- full outer join keeps all rows from both sides

Repository default:
- choose the driving population first
- join optional descriptive or enrichment tables outward from that driving population
- if every base row must survive, make that base table the preserved side of the outer join

### Comparison Operators
Official Domain documentation warns that comparison operators other than `=` can generate very large row counts similar to a Cartesian product unless used carefully in a composite join.

Repository default:
- avoid non-equality joins in Domains unless they are paired with an equality join and validated for row counts

### Join Path Selection
Official Domain documentation recommends enabling minimum path joins for most situations and leaving use-all-joins disabled unless needed for backward compatibility. Join weights and always-include-table controls influence path selection.

Repository default:
- enable minimum path joins on new complex Domains
- assign higher weights to less-desirable joins
- use always-include-table only when the semantic rules require a table in every generated path

## Performance Rules That Matter for C2M
### Push Work to Oracle
Official Jaspersoft guidance for virtual data sources says performance improves when joins, filters, and aggregations are pushed down to the database instead of handled in server memory.

Repository default:
- do reductions in Oracle first whenever possible
- avoid wide, raw Domains over very large fact tables unless pre-filters keep them bounded

### Keep Ad Hoc Sources Manageable
Official docs state that Ad Hoc may load full result sets into memory and recommend sample data for design-time work.

Repository default:
- use sample data while designing
- require date windows, bill cycle windows, or other scoping filters on large CISADM facts
- use Topics to narrow broad Domains before self-service rollout

### Use Data Staging Selectively
Official docs say data staging can speed Domain Topic usage by storing the full staged dataset in cache, but staged topics stop using Domain query optimizations.

Repository default:
- use data staging only for curated, bounded, slow-changing Topic datasets
- do not use data staging for real-time or reconciliation-sensitive datasets unless the refresh interval and operational expectations are explicitly aligned

### Avoid Slow Metadata Paths
Official JRS configuration docs note that Oracle metadata access is significantly slower when synonyms are included.

Repository default:
- prefer explicit source tables, views, and materialized views over synonym-heavy discovery paths when building C2M Domains

## Best-Practice Decision Matrix
### Use a Domain on Raw Tables
Best when the join graph is clean, row-safe, and reusable.

Typical examples:
- reference and lookup browsing
- one-to-one and controlled one-to-many dimensions
- self-service exploration where field curation matters more than SQL reshaping

### Use a Domain with a Derived Table
Best when SQL must establish a stable grain or business definition before the semantic layer.

Typical examples:
- latest-batch summaries
- bill-cycle completion summaries
- exception sets
- cross-fact reconciliations

### Use a Direct SQL JRXML Report
Best when the output is fixed-layout, parameterized, and not intended to power self-service or multiple downstream assets.

Typical examples:
- client statements
- operational letters
- narrow one-off packets

## Validation Required Before Publish
- Confirm intended row grain in Oracle before building the Jaspersoft layer.
- Compare counts before and after each optional join on a known slice.
- Validate that outer joins preserve the intended driving population.
- Validate Domain/Ad Hoc output against the source SQL for at least one known slice.
- Test with cache awareness: note whether results came from fresh query execution, Ad Hoc cache, or staged topic data.

## Official Sources
- JRS core workflow definitions:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-introduction-_-intro_getting_started/
- JasperReport structure and report unit behavior:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-administration-guide/v900/jasperreports-server-admin-guide-_-repository-_-jasperreport_structure/
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-repo-upload-reports-_-repo-defining-query/
- Ad Hoc sources and editor behavior:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-topics-domains-olap/
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-user-guide/vv900/jasperreports-server-user-guide-_-adhoc-_-adhoc-data-source-selection/
- Domain joins and derived tables:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-data-management-using-domains/vv900/jrs-domain-_-advanced_domains-_-advanced_joins/
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-data-management-using-domains/vv900/jrs-domain-_-advanced_domains-_-derived_tables/
- Ad Hoc optimization, cache, and data staging:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-administration-guide/v900/jasperreports-server-admin-guide-_-configuration-_-configuring_ad_hoc/
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-administration-guide/v900/jasperreports-server-admin-guide-_-configuration-_-enabling_data_staging/
- Domain configuration and security:
  - https://community.jaspersoft.com/documentation/jasperreports-server/tibco-jasperreports-server-administration-guide/v900/jasperreports-server-admin-guide-_-configuration-_-configuring_domains/
  - https://community.jaspersoft.com/applications/cms/interface/file/file.php?database=8&file=jasperreports-server-security-guide.pdf&record=85
