<!-- GENERATED from originba_dbt/.claude/skills/c2m-functional-architect/SKILL.md by scripts/local/sync_assistant_knowledge.py; do not edit -->

---
name: c2m-functional-architect
description: The C2M/Origin CIS functional data-model architect. Use when reasoning about how anything in CISADM relates to anything else — designing models or canvases, mapping a client's report SQL to tables, answering "how are X and Y linked", evaluating a join path, judging whether something is configuration or data, or planning what to land next. Carries the verified entity map, join recipes with measured cardinalities, and the config-vs-data rules for Oracle Utilities Customer to Meter 25.4.
---

# C2M functional architect

Every relationship below was **measured on live client data** (Ellensburg, C2M 25.4)
before being written down. When you extend this file, keep that bar: verify on Oracle or
the v2 warehouse first, then record the number next to the claim.

## Sources of truth, in precedence order

1. `scripts/landing/01_create_landing_full.sql` — the verified schema (159 tables,
   column-for-column against `ALL_TAB_COLUMNS`, CHAR_LENGTH semantics). If a column is
   not here, verify it in Oracle before believing it exists.
2. `scripts/landing/extract_slice.py` — EDGES/REFS/POLY_REFS: the machine-readable,
   live-verified join graph. A relationship not recorded there is not yet established.
3. `docs/DOMAIN_JOIN_FINDINGS.md` — what Oracle's own Standard Offering domains say,
   reconciled against data.
4. `docs/BILLING_AMOUNT_SEMANTICS.md` — which amount/quantity column means what.
5. `docs/C2M_BUSINESS_PROCESSES.md`, `docs/CLIENT_CONFIG_FINDINGS.md` — process map and
   per-client configuration variance.
6. Oracle 25.4 docs: Admin User Guide topics are plain HTML at
   `https://docs.oracle.com/en/industries/energy-water/advanced-meter/254/c2m-user-guides/Topics/<topic>.html`
   (start `C2M_Admin_Intro.html`) — WebFetch them directly. The DBA guide is a JS
   viewer and cannot be fetched; schema truth comes from `ALL_TAB_COLUMNS` instead.
7. `.claude/skills/c2m-functional-architect/references/oracle-25-4-notes.md` — distilled
   doc-sourced framework and configuration reference.
8. `.claude/skills/c2m-functional-architect/references/smartcity-suite-platform.md` —
   Origin's own platform: the nine workstreams and their KPIs, the snapshot/Domain/
   promotion architecture, the KPI ownership contract, the report backlog this layer
   serves, and the delivery standards our outputs must satisfy.
9. `.claude/skills/c2m-functional-architect/references/functional-architect-bok.md` —
   the role-level body of knowledge: C-side and D-side functional maps with lifecycle
   states and documented pitfalls (the DEL-BSEG error-segment auto-delete, the meter-
   exchange double-count day, IMD-vs-final-measurement), the one-way CCB→MDM sync seam,
   the technical-analyst toolkit (CMA, batch run tree), and the per-stakeholder daily
   reporting questions each canvas should be able to answer.

## The two worlds and their bridges

CIS/CCB (`CI_`, `C1_`) prices and collects; MDM (`D1_`, `D2_`) measures. They meet at
exactly three verified bridges — never invent a fourth:

| Bridge | Recipe | Measured |
| --- | --- | --- |
| Service point | `D1_SP_IDENTIFIER.ID_VALUE = CI_SP.SP_ID` at `SP_ID_TYPE_FLG='D1EI'` | 100% resolve |
| Device ↔ asset (W1) | device identifier type `D1AS`: its ID_VALUE **is** `W1_ASSET.ASSET_ID` | 55,075/55,082 1:1; value-matching untyped identifiers instead yields 3.5M part-number cross-matches |
| Usage ↔ billing | `D1_USAGE.USG_EXT_ID = C1_USAGE.USAGE_ID`; C1_USAGE carries SA_ID, SP_ID, **BSEG_ID** | 837,439/837,523 bridge; 98.2% of bsegs have exactly one request, retries tail to 10 — always rank-1 (BD-PROC first, latest STATUS_UPD_DTTM) + a match count, never a plain join |

## Load-bearing cardinalities

- **SA ↔ SP is many-to-many** (`CI_SA_SP`, effective-dated, USE_PCT): up to 10 active
  SAs per point; 52 points carry two (water+wastewater), each billing 100% of the same
  measurement. Aggregate or EXISTS through it; a plain join fans out.
- **CI_FT.SIBLING_ID is polymorphic** by FT_TYPE_FLG: BS/BX→CI_BSEG, AD/AX→CI_ADJ,
  PS/PX→CI_PAY_SEG (100% populated).
- **CI_FT.PARENT_ID is typed** by FT_TYPE_FLG: BS/BX→bill, AD/AX→**adjustment type
  code**, PS/PX→payment. Verified on every populated row; `assert_ft_parent_typing`
  enforces it.
- **One BS financial transaction per frozen bill segment** (zero duplicates measured);
  Σ calc lines = header = FT CUR_AMT **or** TOT_AMT (budget→TOT, deposit/pay-arrangement
  →CUR with TOT=0). 1,537/1,537.
- **CI_BILL has no amount column** — bill totals always derive from segment FTs,
  attributed by (typed) parent_id.
- **This MDM instance shares one ID value** across device / device config / measuring
  component (generated from the device id) — three distinct columns that happen to be
  equal here; never rely on that at another client.
- **CI_BSEG_READ's reg-read ids are CCB-classic** — null on every row of an MDM-fed
  instance. Not a usage connector.

## Configuration vs data — the rules that never bend

- **Never hardcode a client-configured code.** Client codes: SA types, rate schedules,
  UOM/TOU/SQI, alert types, comm route types (PRIMARYEMAIL), bill route types (EBILL),
  cc types, char types, debt reason codes. Base-product constants that ARE safe:
  lifecycle statuses (bseg 50/60, SA 10/20/30/40/60, FT types, `WEB_ACCESS_FLG` ALWD/
  NALW, `BD-PROC`, `D1EI`, `D1FA`, RUN_STATUS 30=Error).
- **Labels join on their FULL key**: division-qualified masters
  (`cis_division + sa_type_cd`), composite label keys (`calc_grp_cd+calc_rule_cd`,
  `bus_obj_cd+bo_status_cd`, `mr_cyc_cd+mr_rte_cd`), always `LANGUAGE_CD='ENG'`, always
  LEFT join. Lookup families overlap — decode `CI_LOOKUP_VAL_L` per FIELD_NAME, never
  across families.
- **The main-customer chain** is the conformed spine everywhere:
  `CI_ACCT_PER.MAIN_CUST_SW='Y'` → `CI_PER_NAME.NAME_TYPE_FLG='PRIM'`.
- **Alerts are typed rows** (`CI_ACCT_ALERT` + `CI_ALERT_TYPE_L.DESCR80`);
  `CI_ACCT.ALERT_INFO` is a CSR verification-secrets notepad, redacted at staging.
- Per-client spreads are wide (SA types 36–213, rate schedules 12–246, UOMs 2–34,
  CityCorp has 4 divisions and zero TOU): a model correct only on the reference client
  is not correct. See `docs/CLIENT_CONFIG_FINDINGS.md` for the onboarding checklist.
- **Never infer a category from an English description.** The costliest instance
  (2026-08-22): Utility Type derived from `sa_type_descr like '%water%'`, verified on
  Ellensburg where SA types are literally named "Water Residential" — and wrong at every
  other client (Odessa says "Sewer", Newark says "PVSC" and "Fire Line"; 12 of Newark's
  21 non-misc SA types misfiled, silently). The code C2M itself keys on always exists:
  use `CI_SA_TYPE.SVC_TYPE_CD` (+ `CI_SVC_TYPE_L` for the client's label). Same logic
  killed the CASE on RUN_STATUS in rpt_batch long ago; description-matching is that bug
  with extra steps.
- **`SVC_TYPE_CD` is extensible client config, NOT the fixed W/WW/ST/E/G/T/M.** Fleet
  union is 11 codes (College Station adds D Drainage + R Roadway Maintenance, 18 SA
  types; CityCorp adds S Sanitation; SW Solid Waste at two clients). Normalise the
  shared codes, fall through to the client's own label for the rest, never to a bucket.
  Full per-client table: `references/client-mappings.md`.
- **`CI_SA_TYPE.SPECIAL_ROLE_FLG` is the base-product marker for money that is not
  revenue** — fixed 8-value domain (BC/BD/CD/IN/LO/NB/PA/WO), identical at all six
  clients. PA/CD/WO/LO/NB money is rescheduled debt, the customer's own deposit, or
  revenue being removed; `dim_service_agreement.is_revenue_bearing` encodes the
  exclusion so reports don't each carry the list. Found because "Payment Arrangement"
  topped a revenue chart — billed ≠ revenue.
- **BO statuses (`F1_SVC_TASK.BO_STATUS_CD` etc.) are configuration per business
  object** — no product-wide domain exists. Any model enumerating them into flags must
  pair the enumeration with an `accepted_values` WARN at staging, or a new status
  silently reads false on every flag (375 AWAIT RESP tasks were invisible to
  "Is Outstanding" until measured). Fleet union currently 14; per-client deltas in
  `references/client-mappings.md`.

## Recipes banked for newly landed tables

- `D1_ACTIVITY_REL_OBJ`: `ACTIVITY_REL_OBJ_TYPE_FLG='D1RO'` + `MAINT_OBJ_CD='D1-SP'`,
  then `PK_VALUE1 = D1_SP.D1_SP_ID`.
- `D1_US_SP → D1_SP` adds `BO_STATUS_CD='ACTIVE'`.
- `CI_TD_DRLKEY.KEY_VALUE` is the target object's id, typed per to-do context.
- Paperless-billing population: `WEB_ACCESS_FLG='ALWD'` (permission) + `CI_ACCT_ALERT`
  self-service alert + `BILL_RTE_TYPE_CD` EBILL route + `C1_PER_CONTDET` active
  PRIMARYEMAIL — four different facts; expose all, conflate none.

## The reference corpus (mine it before deriving from scratch)

`~/OriginBA-3/docs/` is loaded with production-earned reference; the highest-value files:
- `cisadm_relationship_map.md` — nine reporting chains with driver-table rules and
  fan-out risks per chain.
- `cisadm_schema_agent_reference.md` (1,153 lines) — per-workstream canonical join
  chains, fact/dim/label inventories, child→parent link lists.
- `bseg_calc_ln_cross_client_patterns.txt` — measured calc-line shapes across five
  clients (see below).
- `*_adhoc_recipes.md` per workstream; `asset_vs_device_reporting_guide.md`;
  `assistant_skills/` (Jaspersoft-side guardrails and past-mistakes list).
- `~/SQLc2m/docs/core/VIEW_DOCUMENTATION.md` (an external checkout, in neither repo) — grain, joins and gotchas for the seven
  base-product BI views (C1_BI_BILL_VW, C1_BI_FT_VW, C1_BI_FTGL_VW,
  C1_BI_BILLED_USAGE_VW, D1_* semantic views, X1_BI_* views); the view SQL itself is
  exported under `~/OriginBA-3/output/cisadm_views/`.
- `~/SQLc2m/docs/guides/JASPERSOFT_QUERY_TEMPLATES.sql` (external checkout) — 12 worked report queries
  (T11 is a documented fan-out ANTI-example: bill-level FT joined through CI_BSEG
  double-counts when grouping by SA type).

## Cross-client calc-line shapes (why per-client re-verification is mandatory)

Measured across five clients (frozen segments, 2026-08): lines per segment average
1.0 (Odessa) to 6.4/max 13 (CityCorp); % of lines with NO UOM and NO SQI ranges
**1.0% (Ellensburg) to 71.7% (CityCorp)**. CityCorp's rate design writes
bill-PRESENTATION lines as calc lines — "Total Water Consumption Charge" and "Total
Taxes" ROLLUPS alongside their detail, taxes as print-N/summarize-Y components.
Consequences:
- The charge-basis split's "Flat" bucket is client-shaped: dominant at CityCorp,
  marginal at Ellensburg.
- `PRT_SW` / `APP_IN_SUMM_SW` are the detail-vs-rollup discriminators; summing detail
  AND "Total …" rollup lines double-counts at presentation-line clients.
- **Onboarding check**: re-verify `header CALC_AMT = Σ lines` per client before
  trusting assert_calc_header_ties_to_lines there — the rollup style is the risk case.
- Ellensburg self-service alert code is `ACCTENRL` (client-configured — a per-client
  mapping fact, never a constant in models).

## Landing candidates surfaced by the corpus sweep (verify in ALL_TAB_COLUMNS first)

High value: `C1_COMM_RTE_TYPE` (route-method discriminator EMAIL/SMS — completes the
paperless canvas), `CI_DST_CD_CHAR` + `CI_DST_CODE_EFF` + `F1_EXT_LOOKUP_VAL_CHAR`
(effective-dated GL revenue-vs-tax classification — closes the CI_TXPYBL sample-report
gap), `D1_MC_TYPE_VALUE_IDENTIFIER` (MC type → UOM at `D1MS`), `D1_MSRMT_CYC_BILL_CYC`
(AMI cycle ↔ bill cycle), `CI_MSG_L` (exception message text), `CI_CASE_CHAR`,
GL/division labels (`CI_GL_ACCT_L`, `CI_CIS_DIVISION_L`, `CI_GL_DIVISION_L`).
Verify-before-queueing: `D1_USAGE_PERIOD_SQ` (may duplicate landed scalar detail),
`CI_PAY_PLAN` (existence unconfirmed). The client DB also carries DBA-built
`*_RPT_CURR` snapshot tables with scheduler jobs — a parallel reporting layer whose
logic this project rederives from raw tables; read their procedures, never source them.

## How to answer a new "how does X link to Y" question

1. Check the extractor graph, then `docs/DOMAIN_JOIN_FINDINGS.md`, then the domain
   library (`~/OriginBA-3/output/standard_offering_domain_inventory/domain_joins_master.csv`)
   and the snapshot procedures (`~/OriginBA-3/sql/performance/snapshots/`) — production
   answers live there.
2. **Measure before asserting**: cardinality both directions, null rates, type-qualified
   match rates, on Oracle (full population) when the VPN is up, else v2.
3. Record the verified recipe in this skill or `docs/DOMAIN_JOIN_FINDINGS.md` with its
   numbers, and if models depend on it, pin it with a dbt test.

## Keeping this skill alive

This skill is only as good as its last verified fact. When you measure something new
(a cardinality, a code value, a client difference, a broken assumption): record it the
same day — measured facts and join recipes into `c2m-functional-architect` (client
codes into `references/client-mappings.md`), SQL traps into `cisadm-sql`, pipeline
recipes into `c2m-dbt-mapping`, coverage changes into
`docs/STAKEHOLDER_QUESTION_COVERAGE.md`. Always with the number and where it was
measured. If a documented claim loses to a measurement, the measurement wins and the
correction is the record.

## Meters have FOUR status dimensions (measured, they disagree by design)

| Dimension | Table | Values (ellensburg) | Answers |
| --- | --- | --- | --- |
| Asset lifecycle | `W1_ASSET.BO_STATUS_CD` | INSTALLED 46,553 · INSTORE 8,338 · RETIRED 183 · INRECEIPT 17 · INREPAIR 1 | where the physical unit is |
| Device status | `D1_DVC.BO_STATUS_CD` | ACTIVE 54,898 · RETIRED 184 | is the MDM device live |
| **Install status** | `D1_INSTALL_EVT.BO_STATUS_CD` | **ON 22,462 · OFF 405 · REMOVE 2,718 · PENDING 6** | is SERVICE connected at this point |
| On/off events | `D1_ON_OFF_HIST.ONOFF_HIST_FLG` | D1ON 26,806 · D1OF 4,501 | the log of every connect/disconnect |

Never substitute one for another. Cross-tab of install status vs removal date:
ON+no-removal 22,462 · REMOVE+removal 2,718 · **OFF+no-removal 278** (meter present,
service switched off — the disconnect population) · **OFF+has-removal 127** (cut then
pulled, status never advanced) · PENDING 6. So a removal-date test alone finds 2,845
removals while a status test finds 2,718 — **read both**. `int_sp_device` now carries
install status; "Service Is On" / "Installed But Switched Off" are on rpt_premise_sp
and rpt_device_asset.

## Assets for reporting

The asset IS the meter, seen by Work & Asset instead of MDM: 55,092 assets, 55,075
carrying a `D1AS` device identifier (1:1). Keep them TOGETHER at device grain
(`rpt_device_asset`) — one physical unit, two modules — because the asset contributes
what the device cannot: inventory lifecycle (INSTORE / INREPAIR / INRECEIPT), and
through `W1_ASSET_NODE` (76,063 rows for 55,092 assets) its POSITION history with
effective dates. `W1_ASSET_LOG` (55,716 rows) is the status-transition audit trail.
Location hierarchy stays at its own grain in `rpt_asset_location` (W1_NODE).

## CI_BILL_SA.CUR_AMT is a BALANCE, not this bill's charges (measured + doc-confirmed 2026-08-22)

Dissected one bill 9/9 exact, fleet-sampled 243/300: CUR_AMT = the SA's frozen-FT
balance as of bill COMPLETION (balance forward + segments + adjustments − payments),
i.e. the bill's per-SA "ending balance" from CCB's own formula (Bill Main Information,
2.5.4): Ending Balance = Previous Balance + Payments + Adjustments + Corrections +
Current Billing Charges. There is NO stored bill-total column — C2M computes every
bill amount as a sum of FTs LINKED TO THE BILL BY TYPE (charges=frozen BS,
adjustments=AD, payments=PS, corrections=BX; 417,124 AD FTs carry bill_id at
Ellensburg). Consequences: comparing this-bill charges to CI_BILL_SA is a category
error (it cost 14 phantom "open bills"); a "bill total" canvas column must never be
invented — expose CI_BILL_SA.CUR_AMT as itself if "amount due at billing" is ever
needed; the ~19% of pairs that do NOT tie skew to heavy-payment SAs, standing
hypothesis open-item accounting (docs: different formula, no balance forward).

## Correction: bills DO carry per-SA amounts (CI_BILL_SA)

`CI_BILL` has no amount column, but its child `CI_BILL_SA` (2.76M rows) carries
CUR_AMT and TOT_AMT **per (bill, SA)** — the rung between the segment and the bill:

```
calc lines  ->  calc header  ->  bill segment  ->  FT (BS/BX)  ->  CI_BILL_SA  ->  bill
 (per line)     (= sum lines)    (= sum headers)   (frozen=money)  (per bill+SA)   (sum rows)
```

Measured: `CI_BILL_SA.CUR_AMT` = the sum of that SA's frozen **BS/BX** FTs on that bill,
3,000 of 3,000 sampled pairs to the cent. Two things follow from the grain:
- It is a **roll-up, not a copy**: 350 of 3,462 (bill, SA) pairs on the reference slice
  carry TWO bill segments (cancel/rebill, split periods), so for ~10% the amount is a
  sum of segments; for the other 90% it happens to equal the single segment.
- A **bill** holds several of these rows (avg 2.61 SAs per bill, max 11), so the bill
  total is `sum(CI_BILL_SA.CUR_AMT)` over the bill — not one row.
- Adjustments swept onto the bill are **excluded**: the tie holds against BS/BX only.
  For "everything that hit this bill", stay on the FT stream.

## Service tasks and the OCX domain fan-out

`F1_SVC_TASK` is the OriginCX channel at this client (565,813 tasks). The published
`f1_svc_task_physical_domain` left-outer-joins all eight task tables in one star,
which multiplies: **avg 4.71 chars x 3.96 logs x 1.73 rel-objs ≈ 32x per task**, and
one pathological task carries **97,345 log rows** — that task alone would render
roughly a million rows. Report tasks at task grain (rpt_customer_notification does,
with rel-obj pre-aggregated); put logs in their own drill if ever needed.

## Big-table sweep, 2026-08-19 (>40k rows, not landed)

Landed from it: CI_BILL_SA, D1_USAGE_PERIOD + D1_USAGE_PERIOD_SQ (the determinants MDM
returns — quantity by UOM/TOU/SQI with measuring component, usage rule, and line
description/price), CI_BILL_MSGS (what printed on the bill), D1_SP_MSRMT_CYC_SCHED_RTE
(scheduled reads — the "expected" side of AMI read-success).
Deliberately NOT landed, with reasons: every `*_LOG` / `*_LOG_PARM` family
(D1_USAGE_LOG 14.9M + PARM 21M, C1_USAGE_LOG 4.1M, D1_ACTIVITY_LOG 3M,
F1_SYNC_REQ_LOG 2.3M, CI_MSG_LOG 1.7M, F1_SVC_TASK_LOG 2.2M, CI_TD_LOG 1.1M) —
per-transition logging whose reportable outcome already sits on the parent's status;
`C1_BI_SA_SNAPSHOT` and `*_RPT_CURR` (client-built layers this project rederives);
`D1_MEASR_BK_1027` (a backup); `CI_ZONE_PRM` / `CI_TD_SRTKEY` (UI plumbing);
`CI_BATCH_INST` / `CI_BATCH_THD` (declined earlier — ctrl+run suffice).
