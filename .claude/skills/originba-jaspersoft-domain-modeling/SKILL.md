---
name: originba-jaspersoft-domain-modeling
description: Design Jaspersoft Domains, join trees, Topics, and Ad Hoc performance patterns for Oracle C2M.
---

# OriginBA Jaspersoft Domain Modeling

## When to use

- Domain or Topic design
- Ad Hoc slowness or row fan-out
- Choosing Domain vs derived table vs snapshot

## Required references

- the *Domain modeling rules* section below
- the *Derived table builder* section below
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`

## Steps

1. Choose artifact: Domain vs Topic vs Report vs Dashboard.
2. Raw Domain joins only if grain is preserved without fan-out.
3. If grain is at risk, establish it in Oracle first (derived table or `*_RPT_CURR` snapshot).
4. Inner joins on optional tables drop population (example: VEE Exception To Do chain).
5. Device Domain: avoid `CMS_DVC_ACCT` unless SA/account fields are required.
6. Use minimum-path joins and join weights on complex Domains.
7. Parity: compare row counts before and after each optional join on a validation slice.
8. For Ad Hoc crosstabs, avoid unnecessary totals (Jaspersoft runs the join graph multiple times).

## Output contract

- Intended grain documented
- Join graph preserves driving population on validation slice
- Performance recommendation states live Domain vs snapshot path

> **Two kinds of domain, both valid in their layer (2026-09-08).** Domains over the dbt reporting canvases are GENERATED in the dbt repo (`~/originba_dbt/scripts/generate_jaspersoft_domains.py`, skill `jaspersoft-domain-generation`): one jdbcTable per canvas, joins live in dbt, item ids from `bi_names.py`, never hand-edited. The hand-built domains this skill describes join CISADM tables or the active-8 snapshot tables and take item ids from `output/domain_field_index.json`. Do not mix the two policies inside one domain.

## Domain modeling rules

*Folded from the *Domain modeling rules* section below on 2026-09-08; the file is archived.*

### Goal
Design production-safe Oracle C2M reporting data models and joins for Jaspersoft domains.

### Core References
- `jaspersoft/docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `knowledge_base/c2m_cisadm/performance_playbook.md`
- `jaspersoft/docs/jaspersoft_domain_report_build_standards.md`

### Modeling Rules
1. Choose the artifact intentionally: Domain for shared semantic reuse, Topic for curated self-service, report for pixel-perfect output, dashboard for multi-panel consumption.
2. Preserve business semantics and driving population before tuning.
3. Use raw Domain tables only when the join graph preserves the intended grain without fan-out; otherwise establish the grain in Oracle first with a derived table or governed SQL layer.
4. Filter high-volume fact tables early (`D1_USAGE`, `C1_USAGE`) and use Topics or pre-filters for self-service over large facts.
5. Pre-aggregate detail tables before dimensional joins when raw detail would multiply rows.
6. Keep optional enrichment joins outer and keep lookup joins language-safe (`LANGUAGE_CD='ENG'`).
7. Avoid non-equality joins in Domains unless composite and validated for row counts.
8. Use minimum-path joins and join weights on complex Domains to reduce ambiguous paths.
9. Use data staging only for bounded, slow-changing Topic datasets where freshness tradeoffs are acceptable.
10. Keep rollback-safe assets (hide risky details, do not hard-delete).
11. All testing and diagnostics must be read-only.

### Validation Rules
- Always run parity SQL before publishing optimized logic.
- Compare counts before and after each optional join on a known slice.
- Require explain-plan evidence for performance claims.
- Keep result deltas zero for equivalent business output.

## Derived table builder

*Folded from the *Derived table builder* section below on 2026-09-08; the file is archived.*

### Goal
Prepare SQL for Jaspersoft Domain or Ad Hoc derived-table ingestion only when a derived table is the safest way to preserve grain, simplify the join graph, or expose a controlled semantic layer.

### Required References
- `jaspersoft/docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`

### Steps
1. Confirm a derived table is actually needed; if raw Domain tables already preserve the grain cleanly, keep the Domain simple.
2. If a derived table is needed, fix one stable row grain in Oracle before exposing it to the Domain.
3. Ensure the SQL begins with `SELECT`, has no trailing semicolon, and avoids parser-fragile constructs unless verified in the target JRS setup.
4. Prefer exposing filterable fields over embedding parser-sensitive parameters.
5. Keep output fields stable, business-readable, and safe for report bindings, Topics, and Ad Hoc use.
6. Validate in Domain Designer; if parser errors occur, simplify the query shape further.
7. Compare derived-table row counts and control totals to the source Oracle SQL on a known validation slice.

### Output Contract
- Query parses in derived table editor.
- Supports report filters via dataset fields.
- No environment-specific hardcoded values unless intentionally scoped.
- Preserves the intended grain and row population on the validation slice.

## Characteristics in a CISADM domain (reviewed 2026-09-17, Service Agreement 360 + CI_PREM_CHAR)

- **`CI_SA.CHAR_PREM_ID` is the right anchor for premise characteristics** — it is C2M's
  designated "characteristic premise" for the SA, the same link five Standard Offering domains
  and `rpt_service_agreement` use. The physical service premise is a different fact
  (`CI_SA_SP` → `CI_SP` → `CI_PREM`, many-to-many); do not swap one for the other. It is
  populated on ~54% of Ellensburg SAs (non-premise SAs — deposits, fees — have none), so
  ~half the SAs carry no premise characteristics by design.
- **Characteristic tables are effective-dated** (PK `entity + CHAR_TYPE_CD + EFFDT`). A plain
  join returns every historical version of every characteristic; Ad Hoc cannot rank. If the
  report needs "the current value", establish it in Oracle first: a `<jdbcQuery>` derived
  table with `EFFDT = (SELECT MAX(EFFDT) ... same entity + type)` (precedent:
  `citycorp_ar_aging_sa_domain/schema.reference.xml`). The dbt canvases do exactly this
  (`rpt_service_agreement` aggregates the latest row per type BEFORE joining).
- **One value column is not enough.** `CI_CHAR_TYPE.CHAR_TYPE_FLG` decides where the value
  lives: `DFV` → `CHAR_VAL` (described by `CI_CHAR_VAL_L`), `ADV` → `ADHOC_CHAR_VAL`,
  `FKV` → `CHAR_VAL_FK1`. A "Value Description" from `CI_CHAR_VAL_L` alone is null for every
  ad hoc and foreign-key characteristic (Ellensburg slice: 19 of 50 premise chars are ADV).
  Expose a calculated field `Coalesce(CI_CHAR_VAL_L_2.DESCR, CI_PREM_CHAR.ADHOC_CHAR_VAL,
  CI_PREM_CHAR.CHAR_VAL_FK1)` or include `CI_CHAR_TYPE` for the flag.
- **A patched schema must keep ONE datasource id, and it must be the wrapper's.** The
  Newark bundle built by `build_service_agreement_360_prem_char_domain.py` had every table on
  `Origin_DEV_DS` while `Service_Agreement___Domain.xml` referenced `/DataSource/Newark1_DS`;
  a domain cannot join across datasource ids, and the schema id must match the referenced DS.
