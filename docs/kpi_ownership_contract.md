# KPI Ownership Contract (SQL vs JRXML)

## Purpose

Prevent KPI drift between standalone SQL artifacts and embedded JRXML query logic by defining one canonical ownership model and mandatory synchronization controls.

This contract applies to KPI packs such as:

- `sql/smartcity_9_workstream_kpis.sql`
- `reports/ops_hub_dashboard.jrxml`

## Canonical ownership model

1. **Canonical logic owner:** SQL file under `sql/` owns KPI computation semantics.
2. **Report owner:** JRXML owns presentation, parameter wiring, and render behavior.
3. **Allowed JRXML SQL:** Copy of canonical SQL is allowed only when Jaspersoft runtime requires embedded SQL; it must be treated as a synchronized mirror, not an independent implementation.

## KPI change policy

Any KPI logic change must be delivered in one atomic change set that includes:

1. Canonical SQL update (source of truth)
2. JRXML embedded query update (if that report embeds SQL)
3. Input control compatibility check (parameter names/types/defaults)
4. Short change note in PR or release notes identifying KPI IDs changed

## Required controls before merge

1. **Name-and-count parity:** KPI identifiers (`WORKSTREAM_NAME`, `KPI_NAME`) in JRXML output must exactly match canonical SQL output for the same parameter window.
2. **Parameter contract parity:** `CLIENT_ID`, `START_TS`, `END_TS` (or report-specific equivalents) must be consistent across:
   - SQL bind expectations
   - JRXML parameters
   - `server/input_controls/*` payloads
3. **No silent semantic rewrites:** threshold/window/filter changes require explicit mention in changelog text.
4. **Environment neutrality:** no embedded credentials and no environment-hardcoded secrets in SQL/JRXML.

## Drift detection checklist

Use this checklist whenever touching KPI logic:

- Compare canonical SQL and JRXML query block text for all KPI branches.
- Validate KPI set cardinality (expected row count and key names).
- Validate one sample window in DEV and compare row-level KPI output.
- Confirm no business-rule-only edits were made in JRXML without SQL changes.

## Escalation rules

1. If SQL and JRXML disagree, **SQL wins** until reconciled.
2. If an urgent report hotfix is done in JRXML first, canonical SQL must be updated in the same release cycle before promotion.
3. If KPI semantics differ by audience, split into distinct named KPI packs instead of overloading one KPI identifier.

## Versioning guidance

- Treat KPI packs as versioned contracts.
- Keep stable KPI identifiers when only implementation is optimized.
- Introduce new KPI identifiers when business definition changes.
- Deprecate old KPI IDs explicitly rather than repurposing them.

## Ownership and sign-off

Minimum sign-off for KPI logic changes:

1. Business Analytics owner (metric definition)
2. Data/Snapshot owner (source and grain correctness)
3. Reporting owner (JRXML and input-control compatibility)

This three-way sign-off ensures metric semantics, data correctness, and rendering contracts stay aligned.
