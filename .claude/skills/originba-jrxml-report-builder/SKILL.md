---
name: originba-jrxml-report-builder
description: Create or fix Domain-first JRXML reports, input controls, and chart blocks for Jaspersoft Studio/Server 9.x.
---

# OriginBA JRXML Report Builder

## When to use

- Creating or editing JRXML under `reports/`
- Fixing compile/render errors in domain reports
- Adding or changing report parameters and input controls

## Required references

- the *JRXML report builder* section below
- `docs/assistant_skills/jrxml_schema_guardrails.md`
- `docs/assistant_skills/jrxml_expression_patterns.md`
- `docs/assistant_skills/domain_report_workflow.md`
- `docs/assistant_skills/troubleshooting_runbook.md`
- `output/domain_field_index.json`

## Steps

1. Map business fields to Domain item IDs from `output/domain_field_index.json`; never invent IDs.
2. Use `language="domain"` with non-empty `<queryFields>`.
3. Enforce element order: `filterExpression` before `group`; `pageFooter` before `summary`.
4. No `seriesColor`, invalid plot attributes, or misplaced `itemLabel` in charts.
5. Update both input control files:
   - `server/input_controls/<report>_input_controls.json`
   - `server/input_controls/<report>_input_controls_rest.json`
6. Keep JRXML parameter IDs aligned with input control IDs.
7. Validate before done:
   ```bash
   python3 scripts/validate_jrxml_schema.py reports/<name>.jrxml
   ```
8. On errors, follow `docs/assistant_skills/troubleshooting_runbook.md` and `past_mistakes_and_prevention.md`.

## Output contract

- XML parse passes
- Non-empty domain query fields with correct IDs
- Input control JSON parses
- No forbidden chart tags for 9.x

> **Style is Origin 2025** (`~/originba_dbt/.claude/skills/origin-doc-style/SKILL.md`: Aptos, Sapphire `#006FAC`); the Blue Theme in `jaspersoft/docs/jaspersoft_domain_report_build_standards.md` applies only when matching an EXISTING Standard Offering report family. `language="domain"` stays the query language (jasperQL is the 9.0 recommendation, not adopted).

## JRXML report builder (Jaspersoft 9.x)

*Folded from the *JRXML report builder* section below on 2026-09-08; the file is archived.*

### Goal
Create or fix domain-first JRXML reports and paired input controls with Studio/Server 9.x-safe structure, null-safe expressions, and deployment compliance.

### Inputs
- Business goal, metrics, and required filters.
- Target Domain URI and exported `schema.data` (or `output/domain_field_index.json`).
- Closest existing report pattern from `reports/`.
- Environment scope (`Origin_DEV` by default).

### Required References
- `AGENTS.md`
- `output/ai_cisadm_context.json` (when SQL/source-table context is needed upstream)
- `output/domain_field_index.json`
- `jaspersoft/docs/c2m_jaspersoft_delivery_playbook.md`
- `jaspersoft/docs/jaspersoft_domain_report_build_standards.md`
- `docs/assistant_skills/jrxml_schema_guardrails.md`
- `docs/assistant_skills/jrxml_expression_patterns.md`
- `docs/assistant_skills/domain_report_workflow.md`
- `docs/assistant_skills/past_mistakes_and_prevention.md`
- `docs/assistant_skills/troubleshooting_runbook.md`
- `knowledge_base/jaspersoft_charts_visuals_jrs9.md`

### Steps
1. Confirm artifact type with the *Domain modeling rules* section below (Report vs Domain vs Ad Hoc vs Dashboard).
2. Map business fields to Domain item IDs using `output/domain_field_index.json`; do not invent IDs.
3. Clone layout/styles from the closest existing report (for example `field_activity_operational_intelligence.jrxml` for filters and severity styling).
4. Build domain query with non-empty `<queryFields>` using exact item IDs from the Domain export.
5. Bind fields with `net.sf.jasperreports.query.field.id` properties matching Domain IDs.
6. Add null-safe `filterExpression`, KPI variables, and conditional styles using patterns from `jrxml_expression_patterns.md`.
7. Create or update both input control files under `server/input_controls/`:
   - `<report>_input_controls.json`
   - `<report>_input_controls_rest.json`
8. Keep parameter IDs in JRXML exactly aligned with input control IDs.
9. Run validation before done:
   - `python3 scripts/validate_jrxml_schema.py reports/<name>.jrxml`
   - JSON parse on both input control files
   - Studio/JRS smoke render when available

### Fix Compilation Errors Workflow
1. Paste the full stack trace and the smallest XML snippet that fails.
2. Check `docs/assistant_skills/troubleshooting_runbook.md` and `past_mistakes_and_prevention.md`.
3. Common fixes:
   - Move `filterExpression` before `group`
   - Move `pageFooter` before `summary`
   - Remove forbidden chart tags (`seriesColor`)
   - Repair Domain query field IDs / empty `<queryFields>`
   - Fix parameter/control ID mismatches

### Output Contract
- Domain-based JRXML unless raw SQL was explicitly requested.
- Datasource aliases only: `ORIGIN_DEV_DS`, `C2M_QA_DS`, `C2M_PROD_DS`.
- Matching dual input control JSON for every changed report.
- Validator passes for touched JRXML files.

### Do Not
- Embed credentials in JRXML or input controls.
- Use table-qualified Domain query field IDs (`D1_SP.D1_SP_ID`).
- Skip input control updates when parameters change.
- Ship JRXML without running `scripts/validate_jrxml_schema.py`.

## SQL JRXML: a report from a query, with no Domain and no Ad Hoc view (added 2026-09-17)

The default here is Domain-first (above). A SQL JRXML is the exception for legacy parity,
fixed layouts, staging views, procedure calls, or a grain a join tree cannot hold safely.
Reference implementations, all in this repo and verified importable:

| Shape | File |
| --- | --- |
| Pattern A: main query is the SQL, groups/variables/summary in JRXML | `reports/ar_aging_by_dist_code_asof.jrxml` (CityCorp AR aging, `$P{AS_OF_DT}` bind, Sum variables) |
| Pattern A + subreport | `reports/billing_customer_statement.jrxml` + `reports/subreports/line_items.jrxml` |
| Pattern B: dummy main query + `subDataset` driving a `jr:table` | `domains/manual_imports/newark_rep8_aged_balance_report/REP8_Aged_Balance_staging_publish.jrxml` (Newark REP8) |
| Pattern C: procedure call (legacy) | REP8's `REP8_STORED_PROC` subDataset: `language="plsql"`, `{call REPORT_8()}` |
| How JRS stores it and how it is imported | the report-unit shape below; `scripts/jaspersoft/build_newark_rep8_report_import.py`, `jaspersoft/docs/jaspersoft_client_tenant_report_import.md` |

### The anatomy, in schema order (`scripts/validate_jrxml_schema.py` enforces it)

```
<jasperReport xmlns="http://jasperreports.sourceforge.net/jasperreports" ... name= pageWidth= ...>
  property / style / template
  subDataset            (ALL subdatasets before the first parameter -- Pattern B)
  parameter             typed: java.lang.String, java.sql.Date/Timestamp, java.math.BigDecimal
  queryString language="SQL"   (or "plsql" for {call ...})
  field                 one per SELECT column, name = the column alias the driver returns (Oracle: UPPERCASE)
  sortField / variable  (Sum/Count variables for totals -- or total in SQL and print $F)
  filterExpression, group
  background, title, pageHeader, columnHeader, detail, columnFooter, pageFooter, summary, noData
```

Rules that are not obvious from the schema:

- **Binds are `$P{NAME}`** inside the SQL; JasperReports sends them as JDBC binds, so a
  `java.sql.Date` parameter compares to a DATE column directly (`TRUNC(ft.ars_dt) <= TRUNC($P{AS_OF_DT})`).
  `$P!{NAME}` splices raw text into the SQL -- injection; never with a user-facing control.
- **Qualify every table** (`CISADM.`, or the client's staging schema such as Newark's
  `JRS2C2M.`): the datasource's default schema is not guaranteed. Never credentials in JRXML.
- **The datasource is NOT in the JRXML.** `com.jaspersoft.studio.data.defaultdataadapter` is a
  Studio-only hint. On the server the report unit binds `<dataSource><uri>/DataSource/<Client>_DS</uri>`;
  a subreport or `datasetRun` inherits it through `$P{REPORT_CONNECTION}`.
- **Types:** VARCHAR2 -> `java.lang.String`; NUMBER -> `java.math.BigDecimal` (never Double for money);
  DATE/TIMESTAMP -> `java.sql.Timestamp` (or `java.sql.Date` when the report never needs time);
  Y/N flags stay `java.lang.String`.
- **A dummy main query needs a real field**: REP8 uses `SELECT 1 FROM CISADM.CI_ACCT WHERE ROWNUM=1`
  with `<field name="1">` -- Oracle names the column `1`. Alias it (`SELECT 1 AS DUMMY`) in new work.
- **Heavy logic belongs in Oracle.** A JRXML query is a thin `SELECT` over a view or refreshed
  table; REP8 went from a giant inline query to `SELECT ... FROM JRS2C2M.REP8_AGED_BALANCE`
  (refreshed by `REFRESH_NEWARK_REP8_AGED_BALANCE`, `sql/clients/newark/rep8_aged_balance/`).
  Long queries get `<property name="net.sf.jasperreports.query.timeout" value="900"/>`.
- **Prove the SQL before the layout**: run it read-only (`scripts/local/run_client_oracle_sql.py
  --client <alias> --file ...`) with the report's own parameters, and reconcile a total to the
  legacy report or a canvas before a single band is drawn.
- **Author for the tenant's engine.** JRS 8.1/9.0 read the JRXML 6 model only; JRS 10 reads
  JRXML 7 only (measured both ways; the version matrix and the 7->6 converter are in the
  domain-modeling skill). A `uuid` on `jasperReport` and elements is fine for report units
  (REP8 carries them). `strip_jrs8_incompatible_jrxml_uuid.py` is for Ad Hoc TOPIC JRXML
  only (it also rewrites `<query>` -> `<queryString>` and strips `nestedType`).

### Pattern D: a family of reports from one generator (the finance pack, 2026-09-17)

When several SQL reports share a layout (title, window line, header row, detail row,
subreport under each row, totals, confidential footer), write them as SPECS and emit the
JRXML: `scripts/jaspersoft/generate_sql_report_pack.py` -> four main reports + four
subreports + input-control JSON, `tests/test_sql_report_pack.py` proves the committed files
are what the generator emits, pass the validator, keep the SQL conventions (TRIM on CHAR
flags, `COALESCE` not `NVL`, `dt < $P{TO_DT} + INTERVAL '1' DAY`, only lifecycle literals),
wire every subreport parameter, and compile on JasperReports 6.20.6 (the JRS 8.1/9.0
engine; classpath from the letterprint verifier). Every query also runs unchanged on the
local Ellensburg Postgres slice, which is how the totals were reconciled before any server
saw them. Reports and semantics: `jaspersoft/docs/sql_report_pack.md`. Two compile-time
lessons: a `$P{}` used in a subreport's SQL must be DECLARED in that subreport and PASSED
from the main ("Query parameter not found: TOP_N"); `isStretchWithOverflow` is deprecated
on 6.20 -- use `textAdjust="StretchHeight"`.

### Pattern B, the one to copy for wide tabular reports

```xml
<subDataset name="REP8_VW" uuid="...">
  <parameter name="Report_Date" class="java.sql.Date"/>
  <queryString language="SQL"><![CDATA[
SELECT account, ..., current_bal, arrears_total
FROM JRS2C2M.REP8_AGED_BALANCE
WHERE rpt_dt = NVL($P{Report_Date}, TRUNC(SYSDATE))
ORDER BY account]]></queryString>
  <field name="ACCOUNT" class="java.lang.String"/>
</subDataset>
<parameter name="Report_Date" class="java.sql.Date">
  <defaultValueExpression><![CDATA[new java.sql.Date(System.currentTimeMillis())]]></defaultValueExpression>
</parameter>
<queryString language="SQL"><![CDATA[SELECT 1 AS DUMMY FROM DUAL]]></queryString>
<field name="DUMMY" class="java.math.BigDecimal"/>
...
<detail><band height="60"><componentElement><reportElement .../>
  <jr:table xmlns:jr="http://jasperreports.sourceforge.net/jasperreports/components" ...>
    <datasetRun subDataset="REP8_VW">
      <datasetParameter name="Report_Date"><datasetParameterExpression><![CDATA[$P{Report_Date}]]></datasetParameterExpression></datasetParameter>
      <connectionExpression><![CDATA[$P{REPORT_CONNECTION}]]></connectionExpression>
    </datasetRun>
    <jr:column> ... </jr:column>
  </jr:table>
</componentElement></band></detail>
```

### Deploying to the SmartCity server: REST, JRXML 7, org scope (measured 2026-09-17)

- **The server is JasperReports Server 10.0.0 PRO** (`GET /rest_v2/serverInfo`), one instance
  hosting every client as a sub-organization of `organization_1` (Ellensburg, Fond_Du_Lac,
  CityCorp, College_Station, Odessa, Newark1, Origin_DEV, Origin_TEST). It runs JasperReports 7:
  **author JRXML 7** -- `<jasperReport name=...>` with no namespace, `<query language="SQL">`,
  `<element kind="textField" ...><expression>`, `bold=`/`blankWhenNull=`/`forPrompting=`,
  `<title height=...>` bands with elements directly inside (only `<detail>` keeps `<band>`),
  subreport = `<element kind="subreport"><parameter name><expression/></parameter>
  <connectionExpression/><expression>"repo:name"</expression></element>`. A 6.x file fails
  "Unable to load report"; JR 6.20 fails on a 7 file. Compile-check with JR 7.0.7 (classpath
  from `~/originba-letterprint/service`, JDK 21): `tests/test_sql_report_pack.py` does.
- **Login scope decides where things land.** `user|Org` scopes to the organization; a bare
  login is root (superuser) or organization_1. Superuser REST paths are
  `/organizations/organization_1/organizations/<Org>/SmartCity/...`.
- **Deploy with REST, not import zips.** `scripts/jaspersoft/jrs_deploy_report_units.py`:
  `PUT /rest_v2/resources/<uri>?overwrite=true&createFolders=true`,
  `Content-Type: application/repository.reportUnit+json`, body = `label`, `dataSource:
  {dataSourceReference: {uri}}`, `jrxml: {jrxmlFile: {type: jrxml, content: base64}}`,
  `resources: {resource: [{name, file: {fileResource: {type: jrxml, content}}}]}` (the
  wrapper object, not a bare array -- "Cannot deserialize ClientReportUnitResourceListWrapper"),
  `inputControls: [{inputControl: {label, mandatory, visible, type: 2, dataType: {dataType:
  {type: text|number|date}}, uri: "<unit>_files/<NAME>"}}]` (the `uri` names the control =
  the parameter it binds). Then `GET /rest_v2/reports/<uri>.pdf?PARAM=...` proves execution.
  Two import-zip shapes (manifest; export-shaped without/with keyalias and datasource)
  returned "Import succeeded" and created nothing.
- **Pick-list input controls** (single-select query, `type: 4`): embed
  `query: {query: {language: sql, value: "SELECT code AS CODE, code || ' - ' || descr AS DESCR
  FROM CISADM.<X>_L WHERE language_cd = 'ENG' ORDER BY 1", dataSource: {dataSourceReference:
  {uri}}}}, valueColumn: "CODE", visibleColumns: ["DESCR"], mandatory: false` -- the user picks
  a description, the parameter receives the code, blank binds NULL (the SQL's
  `$P{X} IS NULL OR ...` selects all). Every client-configured code (cycle, tender type,
  adjustment type, distribution code, division, service type) is a pick-list; ids and
  amounts stay typed. `GET /rest_v2/reports/<uri>/inputControls/<NAME>/values` proves the
  list populates. Multi-select is `type: 7`, the parameter `java.util.Collection`, the SQL
  `$X{IN, TRIM(col), PARAM}` (true when the collection is null/empty, so blank = all); pass
  repeated `PARAM=v` query args to run it. A pick-list shows codes WITH ACTIVITY IN THE LAST
  3 YEARS (`CURRENT_DATE - INTERVAL '3' YEAR`, ANSI, runs on Oracle and the slice): the label
  table with an `EXISTS` against the dated fact table (Chase's rule, 2026-09-17, after the configured
  list showed Auto Pay tender types no tender ever used -- Ellensburg: 18 configured, 10 used).
  Compare CHAR = CHAR untrimmed in the EXISTS so Oracle keeps its indexes.
- **Layout rules that survived the first DEV review**: main row = light band under a sapphire
  rule; subreport on the SAME column grid (blank placeholder cells), no caption, plain rows,
  hairline + subtotal; `fontName="SansSerif"` -- the server has no Aptos and falls back to a
  serif, which reads as a different report.
- **Only Origin_DEV** on the SmartCity server unless Chase names another org: the rest are live
  client tenants (2026-09-17).
- `jrs_repository.py search <name>` / `list <folder>` answer "where is it" before any theory.

### Choosing

| Approach | Use when |
| --- | --- |
| Domain + domain JRXML | Standard Offering, governed self-service, shared semantics (preferred) |
| Ad Hoc view / topic | exploration, crosstabs on a Domain |
| SQL JRXML | legacy parity, fixed layout, staging view/table, procedure call, or a grain a join tree cannot hold |
