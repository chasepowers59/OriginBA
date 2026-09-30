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

## Client-configured, effective-dated tables in a domain: the derived-table recipe

C2M's core tables are the same at every client. What differs client to client lives in the
EXTENSION tables: characteristics (`CI_*_CHAR`, `D1_*_CHAR` -- type, code and value are the
client's own configuration, described by `CI_CHAR_TYPE`, `CI_CHAR_TYPE_L`, `CI_CHAR_VAL_L`),
and the other effective-dated detail tables (`CI_SA_RS_HIST`, `CI_SA_RCHG_HIST`,
`CI_SA_CONTERM`, `CI_PREM_CHAR` ...). Joined raw into a domain they misbehave in three ways
that are invisible on a small tenant and wrong on a real one (found on Service Agreement
360, 2026-09-17; verified imported on DEV, both derived tables preview):

1. **A label table is a table of everything.** Drag *Characteristic Type Code* from
   `CI_CHAR_TYPE_L` and Ad Hoc offers every type in the system (account, person, SA,
   premise); select label fields alone and it queries the label table alone. The outer join
   is not the cause and must stay (the 360 domains exist to pull anything, then filter).
2. **Effective dating.** PK is `entity + type + EFFDT`; every version is a row and nothing
   says which is current. Ad Hoc cannot rank.
3. **One value column is not enough.** `CI_CHAR_TYPE.CHAR_TYPE_FLG` decides where the value
   lives: `DFV` -> `CHAR_VAL` (label in `CI_CHAR_VAL_L`), `ADV` -> `ADHOC_CHAR_VAL`,
   `FKV` -> `CHAR_VAL_FK1`. A description from `CI_CHAR_VAL_L` alone is null for every ad hoc
   and FK characteristic (Ellensburg slice: 19 of 50 premise chars are ADV).

**The recipe** (`scripts/jaspersoft/patch_domain_characteristics.py`, tested by
`tests/test_domain_characteristics_patch.py`; `--target TABLE:KEY:TYPE_L_ALIAS:VAL_L_ALIAS`
applies it to any characteristic table in any domain):

- Replace the raw table AND its label joins with ONE `<jdbcQuery>` derived table **under the
  raw table's id**. Joins, join-tree fields and item `resourceId`s that named the table keep
  resolving, so saved Ad Hoc views survive; repoint the label items (same item ids) to the
  folded columns.
- The derived row carries: the raw columns, `CHAR_TYPE_DESCR`, `CHAR_TYPE_FLG`,
  `CHAR_VAL_DESCR`, **`CHAR_VALUE`** (resolved by kind), **`IS_CURRENT_SW`** = 'Y' on the
  latest version whose `EFFDT` is not in the future, per `(entity, type)`. **No row is
  removed** -- history stays; "current" is a filter the user applies.
- SQL rules the JRS domain parser enforces: starts with `SELECT`, one outer wrapper, no CTE,
  no bind, no semicolon; ANSI so the same text runs on Oracle and on the local Postgres
  slice (`COALESCE`, `CASE`, `MAX() OVER`, `TRIM`, `CURRENT_DATE`; XML-escape `<`).
- One datasource id per schema, and it must be the one the domain wrapper references
  (`<uri>/DataSource/X</uri>`); a domain cannot join across datasource ids. The SA 360
  builder reads the id from the export and refuses a mismatch -- the first Newark bundle
  had every table on `Origin_DEV_DS` under a `Newark1_DS` wrapper.
- Prove it before import: derived rows = raw rows, one current row per key with a
  non-future version, zero unresolved values (`sql/validation/service_agreement_prem_char_grain_check.sql`
  gates 5-6); the offline test proves every reference resolves.

Same pattern for a rate-schedule history or a contract-term table: derived table under the
raw id, `IS_CURRENT_SW` over the table's own effective-date key, descriptions folded in.

**Anchors that are right and look wrong:** `CI_SA.CHAR_PREM_ID` is C2M's designated
"characteristic premise" for the SA (populated on ~54% of Ellensburg SAs; deposits and fees
have none) -- the correct link for premise characteristics, used by five Standard Offering
domains and `rpt_service_agreement`. The physical service premise is a different fact
(`CI_SA_SP -> CI_SP -> CI_PREM`, many-to-many). Never swap one for the other.

## JasperReports versions (measured, not assumed)

| Server | Library / JRXML model | Notes |
| --- | --- | --- |
| JRS 8.1.0 PRO (Odessa tenant, `jsVersion` measured from its export) | JasperReports 6.20, JRXML 6 model | reads 6.x JRXML only |
| JRS 9.0.x (Origin DEV; Studio 9.0.x) | 6.x JRXML model | reads 6.x only; JRS 9 Ad Hoc adds date-time calcs, chart options in `knowledge_base/jaspersoft_charts_visuals_jrs9.md` |
| **JRS 10.0.0 PRO -- the SmartCity server today** (`/rest_v2/serverInfo`, 2026-09-17; one instance, every client an org) | JasperReports 7, JRXML 7 model | reads 7 only: 6.x files fail "Unable to load report" and vice versa (measured both ways in originba-letterprint). The 8.1.0 PRO rows above are what the same server was before its 2026-05 upgrade; old exports still say 8.1.0 |

JRXML 7 vs 6: boolean attributes lose the `is` prefix (`isBold` -> `bold`), `reportElement` /
`textElement` / `font` attributes flatten onto the element, `hTextAlign`/`vTextAlign` replace
`textAlignment`/`verticalAlignment`, the XSD lives at `/xsd/jasperreport.xsd`. The converter
that encodes every measured difference is `~/originba-letterprint/jasperserver/tools/jrxml7to6.py`
(author once in 7, generate the 6.20 twin, render both and assert equal text). `jsVersion` in
an import bundle is measured from a real export of the target, never typed.

## Placement history: join from the CURRENT row, never the raw history (2026-09-18, Fond du Lac)

`W1_ASSET_NODE` (asset placement, PK ASSET_ID + EFF_DTTM) carries a "current" pointer
(`CURR_ASSET_ID`/`CURR_NODE_ID`) that C2M fills on one row per asset -- and leaves stale when a
meter is re-installed minutes after an In Store entry (2 of 16,672 at Fond du Lac). Three rules,
each learned the hard way the same day: (1) the current placement is the LATEST EFF_DTTM row,
what Disposition History shows; expose `NVL(CURR_NODE_ID, NODE_ID) AS CURR_NODE_ID` under the same
field id; (2) never select the current row BY the pointer (it showed those meters as In Store);
(3) join service-point/premise tables FROM the derived current-placement table, not from the raw
history table -- the raw join fanned 16,672 installed meters into 20,541 rows, and the legacy views
hid it with a filter on the raw pointer that picked the wrong row. Record and packages:
`domains/manual_imports/fonddulac_asset_domain/` (REST import needs the org's own datasource
export listed first, `rootTenantId`, folder XML with `<parent>`+`<name>`, descriptions under 250
characters -- each of those failed once).

## Version matrix addendum (2026-09-20): JRS 10 PRO loads JRXML 6 through a licensed legacy loader
The JR 7 library alone cannot load JRXML 6 (measured, and vendor-confirmed); JasperReports Server
10.0 PRO adds `LegacyXmlLoader` (JRL-Pro, license-gated), which is why the 10.0 test server serves
JRXML 6 bills. "Mutually unreadable" is true of the LIBRARIES and of Studio; on the PRO server old
units keep running. Details in `jaspersoft-server-operations`.


## Write Offs domain: applied and proven 2026-09-23 (test Origin_DEV, test Fond_Du_Lac)

`scripts/jaspersoft/patch_write_offs_domain.py` + `tests/test_write_offs_domain_patch.py` +
`domains/manual_imports/write_offs_domain/README.md` (apply-and-prove runbook). What it fixes and
adds, found by comparing the Standard Offering Write Offs domain with FDL's custom write-off domain:
- `WO_PAY_AGG` had a HARD-CODED floor (`>= date '2025-09-01'`, twice): every older process showed
  empty payment figures and the cut-off never moved. Now relative to each process's own start.
- `WO_PAY_AGG` joined `ci_pay_tndr.pay_tender_id = ci_pay_seg.pay_id` -- two different id spaces,
  so event counts and first/last dates never matched. Chain is segment -> CI_PAY -> CI_PAY_EVENT
  (the extractor graph's edges). Lesson: a derived query is SQL nobody executes in review; read
  its joins against `extract_slice.py` EDGES before trusting a number that comes out of it.
- New `WO_ACCT_BAL` (account current/payoff balance, balance regime FREEZE_SW='Y' AND
  REDUNDANT_SW='N') and `WO_PROC_ARS` (+ calculated running arrears net of payments since start).
Not carried from FDL, each a defect there: `REDUNDANT_SW='Y'` (the netted-to-zero rows, i.e. the
opposite of a balance), `CI_PAY.ILM_DT` used as a payment date, and an SA-type 'PA' term (client
code). Also learned: "Process Start DTTM" (BI view CRE_DTTM) and FDL's "Create Date/Time"
(CI_WO_PROC.CRE_DTTM) are the SAME timestamp; a list comparison differs only because FDL's
domain fans out per characteristic premise (right-outer joins) and both sides carry different
date floors. Pre-existing item ids/joins are byte-identical after the patch (tested).

Validation record (`domains/manual_imports/write_offs_domain/README.md` has the table). Three
lessons that cost the morning:
- **"Current Balance" is the snapshot's rule, all THREE conditions**: `FREEZE_SW='Y'`,
  `NOT_IN_ARS_SW='N'`, and `ARS_DT` set and not after today. With the first two only, a
  write-off adjustment (no arrears date) nets the debt to zero: 13 of 752 accounts tied. With
  all three, 752 of 752 and 633 of 633 to the cent. The independent oracle is
  `CMS_ACCT_SNAPSHOT.CUR_BAL_1` in the SA Snapshot domain, queried by account.
- **A regime change that does not move the number was never the cause.** Swapping
  `REDUNDANT_SW='N'` for `NOT_IN_ARS_SW='N'` left 13 of 752 unchanged; the missing condition was
  the third one. Compare against the oracle after EVERY change, not once at the end.
- **Look for a hard-coded floor in three places**: the derived query, the join tree's
  `<filterString>`, and the view's own filters. The Write Offs domain had the first two
  (`>= 2025-09-01` in WO_PAY_AGG, fixed; `CRE_DTTM >= ts'2025-09-01'` in the join tree, still
  there -- it hides all of FDL's 2023-2024 processes and is a product decision).
Also measured: the BI view's process count equals the raw table's once the join-tree filter is
accounted for; "Process Start DTTM" and FDL's "Create Date/Time" agree on 787 of 787.
