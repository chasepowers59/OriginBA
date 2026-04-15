# Legacy Domain To Snapshot Modernization Playbook

## Purpose
This is the end-to-end operating guide for taking an older manual Domain, turning it into a governed Oracle snapshot, validating it, publishing a new importable Domain XML, and moving existing reports onto the new snapshot-backed Domain.

Use this when the current state is:
- an older XML Domain under `domains/working/manual_designs/`
- runtime joins are too heavy, inconsistent, or mixed-grain
- business questions are stable enough to justify a governed snapshot table
- reports or Ad Hoc views need to move to a faster and safer semantic layer

Use the per-snapshot docs for artifact-specific details. Use this document for the repeatable process.

## End State
When this process is complete, the repository should contain:
- a governed snapshot workspace under `sql/performance/snapshots/<workstream>/<subset>/`
- a business-facing snapshot doc under `docs/`
- an importable Domain XML under `domains/exports/manual_imports/`
- updated catalog entries and runbook references
- report and input-control updates pointing to the new Domain-backed artifact

## Starting Point

### Review the old Domain first
Start with:
- `domains/working/manual_designs/DOMAIN_BUSINESS_CATALOG.md`
- the candidate XML under `domains/working/manual_designs/`
- `output/workstream_reporting_dictionary.json`
- `Domain Designs.xlsx`

You are trying to answer six questions before writing SQL:
- What business questions does the old Domain answer today?
- What is the real grain of the old Domain?
- What additive measures are trusted at that grain?
- Which joins or calculated fields are making it heavy or risky?
- Which reports, dashboards, or Ad Hoc views currently depend on it?
- Which fields are essential versus just legacy convenience fields?

### Decide whether a snapshot is justified
Build a snapshot when one or more of these are true:
- the old Domain rebuilds the same joins every time
- the Domain mixes grains and risks fan-out
- the business needs repeated self-service access from one governed table
- the old design depends on fragile derived-table logic or wide runtime joins
- existing reports need better performance and a stable field contract

Do not create a snapshot just to mirror every old field. The snapshot should exist to lock grain, preserve trusted measures, and remove unnecessary runtime complexity.

## Phase 1: Define the Snapshot Contract

### Write the contract before the table
Document these items first:
- workstream
- snapshot name
- target grain
- natural key
- trusted additive measures
- source-of-truth driving table
- optional child overlays
- row-preservation rules
- business filters that define the population

Example:
- `FT_RPT_CURR`
- grain: one row per `FT_ID`
- trusted measure: `CUR_AMT`
- row-preservation rule: keep `CI_FT` population and only populate child overlays when FT type makes sense

### Trim the fat up front
Before creating columns, sort old-domain fields into:
- required for business questions
- useful but optional
- not needed in the new governed snapshot

Keep these rules:
- keep IDs, dates, statuses, codes, and trusted measures that support real questions
- keep business-friendly descriptions only when they remove repeated lookup pain
- avoid columns that are always null, duplicate another field, or belong to a different grain
- do not pull in deep child detail that changes row count

Use `sql/performance/snapshots/docs/snapshot_impact_assessment.md` and `sql/performance/snapshots/impact/05_snapshot_column_relevance.sql` later to confirm whether low-value columns should be removed from existing snapshots.

## Phase 2: Build the Snapshot Workspace

### Create the workspace
Use this folder pattern:

`sql/performance/snapshots/<workstream>/<subset>/`

Expected files:
- `README.md`
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`

Optional files when needed:
- `00a_preflight_validation.sql`
- `00b_string_width_audit.sql`
- `01a_alter_existing_snapshot_table.sql`
- additional trace or parity helpers

### Table design rules
The snapshot table should:
- preserve one agreed grain
- include `LOAD_DTTM`
- use stable business-readable column names
- avoid carrying unused legacy columns just because they existed before
- size identifier columns based on validated source widths, not guesswork

### Procedure design rules
The refresh procedure should:
- load only the intended reporting population
- keep optional joins `LEFT JOIN` unless row loss is intentional and justified
- decode statuses and descriptions in a consistent way
- be simple enough that another analyst can read it in SQL Developer

If the first version uses `TRUNCATE` plus full reload, document that explicitly in the snapshot README and business doc.

### Scheduler design rules
The scheduler job file should define:
- job name
- procedure action
- enabled state
- repeat interval
- any rollout note about refresh windows or table-empty periods

## Phase 3: Validate In SQL Developer

### Build order
Run in this order:
1. `01_create_snapshot_table.sql`
2. `02_refresh_snapshot_procedure.sql`
3. execute the procedure manually at least once
4. `04_validation_queries.sql`
5. `03_schedule_snapshot_job.sql` only after manual validation is acceptable

### What to validate
Validation should prove:
- row count is reasonable
- natural key is unique
- required IDs are populated
- statuses and descriptions are populated where expected
- optional child fields only populate for the right subset
- dates are sane
- additive measures reconcile to the intended source slice
- recent sample rows are readable for business users

Use:
- the snapshot-specific `04_validation_queries.sql`
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md`
- `sql/performance/snapshots/docs/snapshot_impact_assessment.md`
- `sql/performance/snapshots/impact/`

### Minimum SQL Developer checks
Every handoff should be able to answer these in SQL Developer:
- What is the current row count and latest `LOAD_DTTM`?
- What procedure text is running right now?
- What job is scheduled right now?
- Did the last scheduler runs succeed?

Those exact read-only checks already live in:
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md`

## Phase 4: Publish The New Domain

### Create the importable XML
After the snapshot is stable, create the new importable Domain XML in:

`domains/exports/manual_imports/`

The standard naming pattern is:

`<SNAPSHOT_NAME>_End_User_Friendly.xml`

### Domain design rules
The new Domain should:
- point to the snapshot table, not the old heavy join graph
- preserve business-friendly labels and folders where they help adoption
- expose the trusted measures and key dimensions clearly
- avoid carrying forward confusing duplicate fields from the old Domain
- preserve field IDs and naming carefully when you want a smoother report migration

### XML documentation updates
When the new Domain XML exists, update:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`
- the snapshot-specific business doc under `docs/`
- `sql/performance/snapshots/docs/workstream_snapshot_catalog.md` if the snapshot is net-new

If the old XML remains important for lineage, mention it in the new snapshot doc under a migration or legacy-source section instead of pretending it never existed.
If an older import bundle or design variant is being retired, archive it intentionally instead of hard-deleting it.

## Phase 5: Convert Existing Reports And Ad Hoc Assets

### Find impacted assets
Search the repo for the old subject or Domain names before editing:

```powershell
rg -n "Old_Domain_Name|Old Subject|legacy field id" reports docs server
```

Also search for snapshot and Domain references:

```powershell
rg -n "FT_RPT_CURR|BSEG_BILLED_USAGE_RPT_CURR|PAY_TNDR_CASH_RPT_CURR" reports docs server
```

### Report conversion approach
For each report:
1. identify the current Domain or SQL dependency
2. confirm the new snapshot-backed Domain can answer the same question at the correct grain
3. update the JRXML dataset and fields to the new Domain contract
4. update matching input controls under `server/input_controls/`
5. validate XML parse, parameter alignment, and query field completeness

Repository rules still apply:
- prefer Domain-based JRXML
- maintain matching input controls
- keep Jaspersoft 9.x-safe ordering
- do not silently widen scope or change KPI definitions during migration
- preserve rollback path by archiving or clearly documenting replaced legacy report assets when the migration is significant

### Ad Hoc and Topic conversion approach
When the consumer is self-service:
- create or refresh the Topic from the new snapshot-backed Domain
- keep the starting field set smaller than the raw Domain where possible
- preserve trusted measures and obvious dimensions first
- move optional or niche fields behind folders instead of putting everything on the surface

## Phase 6: Document The Snapshot So Someone Else Can Operate It

Each snapshot needs a business-facing doc under `docs/` that covers:
- purpose
- grain
- driving tables
- source scale
- included fields
- excluded fields
- join rules
- trusted measures
- best use cases
- do-not-use cases
- validation checklist
- implementation caveats
- XML artifact path
- SQL Developer runbook reference

Also update:
- `sql/performance/snapshots/docs/workstream_snapshot_catalog.md`
- `sql/performance/snapshots/docs/business_question_snapshot_coverage.md` when coverage changes
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`
- `sql/performance/README.md` or `sql/performance/snapshots/README.md` when a new workspace is added

## Phase 7: Record DB Impact And Relevance

After the snapshot exists in the database, capture:
- storage footprint
- live row count
- freshness
- scheduler health
- evidence of actual SQL usage if available
- sparse or low-value columns that should be candidates for removal

Use the read-only pack in:
- `sql/performance/snapshots/impact/`

This is where the database-health results belong once they are available.

## Definition Of Done
The modernization is done only when all of the following are true:
- the old Domain has been reviewed and its grain is understood
- the new snapshot table, procedure, job, and validation SQL exist in a governed workspace
- the snapshot was manually validated before scheduler rollout
- the importable XML exists under `domains/exports/manual_imports/`
- the snapshot business doc exists
- the XML inventory and workstream catalog are updated
- impacted reports and input controls are migrated or explicitly deferred
- report validation and parameter validation pass
- handoff instructions exist for SQL Developer inspection and job validation

## Handoff Package
If another analyst needs to pick up the work, they should be able to find everything from this minimum package:
- the snapshot workspace under `sql/performance/snapshots/`
- the business doc under `docs/`
- the importable XML under `domains/exports/manual_imports/`
- the SQL Developer operating steps in `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md`
- the current coverage position in `sql/performance/snapshots/docs/business_question_snapshot_coverage.md`

## Related Guides
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `sql/performance/snapshots/docs/workstream_snapshot_catalog.md`
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md`
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`
- `sql/performance/snapshots/docs/snapshot_impact_assessment.md`
- `sql/performance/snapshots/docs/snapshot_modernization_checklist.md`
