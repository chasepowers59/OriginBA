<!-- GENERATED from originba_dbt/.claude/skills/cisadm-sql/SKILL.md by scripts/local/sync_assistant_knowledge.py; do not edit -->

---
name: cisadm-sql
description: SQL generation against the C2M CISADM schema — live Oracle (via the read-only MCP) and the local Postgres warehouses (originba_v2 on 5432, the fixture container on 5433). Use whenever writing validation queries, mapping ad hoc report SQL, profiling tables, or measuring cardinalities. Encodes the dialect traps, join discipline, and safety rules this project has learned the hard way.
---

# CISADM SQL generation

## Where to run what

| Target | How | Use for |
| --- | --- | --- |
| Live Oracle (full population) | `mcp__originba-oracle__originba_run_readonly_sql` (client alias, e.g. `ellensburg`); VPN required | cardinality truth, `ALL_TAB_COLUMNS` verification, full-scale measurements |
| Real slice warehouse | psql `PGPORT=5432 PGDATABASE=originba_v2`, schema `cisadm` + dbt schemas | offline checks, canvas verification; remember it is a SLICE — per-entity complete, population partial |
| Fabricated container | creds from `.env` (`DBT_*`), port 5433 | logic checks with zero PII |

Read-only always. Never write to Oracle; `prod_enabled` stays false. One statement per
MCP call (SELECT/WITH only). Never paste real customer values (names, emails, MICR,
ALERT_INFO contents) into committed files or chat output — counts and codes only.

## Schema truth

- Column names/types: `scripts/landing/01_create_landing_full.sql` (159 tables,
  Oracle-verified). For anything else: `SELECT ... FROM all_tab_columns WHERE
  owner='CISADM' AND table_name=... ORDER BY column_id` — use **CHAR_LENGTH, never
  DATA_LENGTH** (AL32UTF8 makes DATA_LENGTH 4x wrong). Batch multi-table pulls with
  `LISTAGG(column||'~'||type||'~'||char_length...) WITHIN GROUP (ORDER BY column_id)`.
- Table-name traps seen so far: `CI_B_CHG_LINE` (not BILL_CHG_LN), `CI_BILL_RT_TYPE_L`
  (table RT, column BILL_RTE_TYPE_CD).

## Dialect traps

- **Never trim() a JOIN column at scale** — `on trim(f.sa_id) = s.sa_id` blocks the
  index on CI_FT.SA_ID and full-scans; fine at Ellensburg's 5M FTs, a hard timeout at
  Newark's volume (measured 2026-08-22, the arrears-proof query). CHAR-to-CHAR of the
  same width joins RAW (`f.sa_id = s.sa_id` — both padded identically); reserve trim()
  for SELECT output and for comparisons against varchar/literals per the next rule.
- **Oracle CHAR columns are space-padded**: every equality against a CHAR key from
  another table or a literal needs `TRIM()` on the CHAR side (`BILL_RTE_TYPE_CD =
  'EBILL   '` in client SQL is the symptom). In the Postgres landing the padding
  survives — same rule.
- Oracle: `ROWNUM`/`FETCH FIRST n ROWS ONLY`, `NVL`, `LISTAGG`, `ADD_MONTHS`,
  `TRUNC(date)`; Postgres: `LIMIT`, `coalesce`, `string_agg`, date arithmetic.
  `DATE` in Oracle carries time — landed as `timestamp`.
- Empty string vs NULL: Oracle treats '' as NULL; Postgres does not — after TRIM,
  compare with `nullif(trim(x),'')`.

## Join discipline (each rule exists because the naive join was measured wrong)

1. **Identifier tables join TYPE-PINNED, never by value alone** — untyped device/asset
   identifier matching produced 3.5M false pairs. `D1EI` for SP bridge, `D1AS` for
   asset, `D1BN` badge, `D1SN` serial.
2. **Rank-1 winners for request/retry objects** — `C1_USAGE` per bseg: BD-PROC first,
   latest STATUS_UPD_DTTM, plus a match count column.
3. **EXISTS or aggregate through CI_SA_SP** (≤10 active SAs share a point).
4. **Polymorphic FKs gate on the discriminator**: `CI_FT.SIBLING_ID`/`PARENT_ID` only
   with `FT_TYPE_FLG` pinned.
5. **Labels**: full key + `LANGUAGE_CD='ENG'` + LEFT. Lookups per FIELD_NAME.
6. **Population preservation**: start FROM the entity being counted; LEFT-join context;
   an INNER label join silently deletes rows for codes the client didn't configure. A
   GROUP BY that "fixes" duplicates is hiding a fan-out — fix the join instead
   (dedupe as columns on one line, not rows).
7. **Never sum across grains**: line `BILL_SQ` double-counts usage; GL lines net to
   zero; SP-attributed usage counts repeat per SA. See
   `docs/BILLING_AMOUNT_SEMANTICS.md` before summing any amount.

## Recipes banked from production SQL (sources in ~/SQLc2m and ~/EburgForReals~2.sql)

- **Blank means missing**: CISADM CHAR columns hold `' '` (spaces), not NULL — every
  presence test is `nullif(trim(x),'') is not null`, and a literal `SP_ID=' '` in old
  SQL means "the blank segment-level row".
- **Effective-dated config lookup**: `CI_DST_CODE_EFF` at
  `MAX(EFFDT) <= FT.ACCOUNTING_DT` — the pattern for GL account / revenue-vs-tax
  labeling (pairs with CI_DST_CD_CHAR + F1_EXT_LOOKUP_VAL_CHAR classification chars).
- **Finalized-financials gate**: `FREEZE_SW='Y'` + FT type pinned + (for GL work) an
  `EXISTS (CI_FT_GL)` guard, per the base C1_BI_FT_VW.
- **Alert predicates**: open-ended alerts are `END_DT IS NULL OR END_DT > SYSDATE`;
  the alert TYPE code is client config (Ellensburg self-service = `ACCTENRL`).
- **Paperless stack** (four independent facts, expose all): WEB_ACCESS_FLG permission,
  ACCT_ALERT enrollment, BILL_RTE_TYPE_CD route, C1_PER_CONTDET active
  (`CND_ACTINACT_FLG='C1AC'`) contact whose route type's `COMM_RTE_METH_FLG='EMAIL'`.
- **Anti-recipe (documented fan-out)**: joining bill-level FTs through CI_BSEG while
  grouping by SA type double-counts each bill FT per segment; DISTINCT/GROUP BY that
  "fixes" counts is the smell. Pre-aggregate each side to a shared grain first (the
  billed-vs-GL reconciliation CTE pattern).

## The College Station aging method (the FIFO allocation, banked 2026-08-19)

Naive ARS_DT bucketing of CUR_AMT is wrong: payments are separate FT rows, so you must
decide WHICH charges they retired. The client-blessed method (their Master Report):
1. Debit-side FTs only: `FT_TYPE_FLG NOT IN ('PS','PX')` and exclude credit
   adjustments (`CUR_AMT < 0 AND FT_TYPE_FLG IN ('AD','AX')`).
2. True net total per SA from ALL FTs at `FREEZE_SW='Y' AND NOT_IN_ARS_SW='N'`.
3. Order charges youngest->oldest, preceding-rows running sum;
   unpaid portion = `LEAST(charge, net_total - preceding_sum)` floored at 0.
Payments retire the OLDEST charges first; residual debt sits on the newest. Matches
what int_sa_arrears implements; measure ours against theirs per client.

Two FT exclusion regimes COEXIST -- never mix: balances use `REDUNDANT_SW='N' +
FREEZE_SW='Y'`; aging uses `FREEZE_SW='Y' + NOT_IN_ARS_SW='N'` and KEEPS null-ARS_DT
rows as a NEW/UNBILLED band. `CI_FT.BILL_ID` is the bill the FT is PRINTED on (swept),
never attribution -- use typed PARENT_ID. Payment dates for drafts/trustee reports use
`ARS_DT` on PS rows (the effective date), not CRE/FREEZE_DTTM. "Active" must include
Reactivated ('50') wherever activity matters, not just '20'. There is NO payment->bill
link in C2M; any "bill paid" indicator comes from the FIFO allocation.

GL debit/credit sourcing (verbatim from their GL rules): BS debit = SA type DST_ID
(A/R), credit = calc-rule revenue/tax; PS debit = tender-source bank account, credit =
SA type DST_ID (PX reverses); AD positive debit SA type / credit adj type DST_ID,
negative (refund) reversed. Charity bills have NO GL effect; company usage posts zero.
"Posted to GL" = CI_FT_PROC.BATCH_NBR not null; distributed = GL_DISTRIB_STATUS='D'.

## Method

- **Profile before filtering**: check a code column's actual values
  (`GROUP BY code ORDER BY count`) before writing a WHERE on it — client codes differ
  and padded CHARs lie.
- **Measure both directions** of any new relationship (children per parent AND parents
  per child) plus null rates before trusting it in a join.
- Validation queries return counts and identities, not row dumps; a query whose result
  you cannot state as "N of M satisfy X" is not yet a validation query.
- Existing worked examples: `scripts/validate_joins.sh`, `tests/*.sql`, and the
  production snapshot SQL in `~/OriginBA-3/sql/performance/snapshots/`.

## Keeping this skill alive

This skill is only as good as its last verified fact. When you measure something new
(a cardinality, a code value, a client difference, a broken assumption): record it the
same day — measured facts and join recipes into `c2m-functional-architect` (client
codes into `references/client-mappings.md`), SQL traps into `cisadm-sql`, pipeline
recipes into `c2m-dbt-mapping`, coverage changes into
`docs/STAKEHOLDER_QUESTION_COVERAGE.md`. Always with the number and where it was
measured. If a documented claim loses to a measurement, the measurement wins and the
correction is the record.

## Rules banked from the OriginBA-3 SQL builder skills (merged 2026-09-08)

The portal repo carried its own CISADM SQL skills (`skills/sql_report_builder`,
`docs/cowork/skills/originba-cisadm-sql-builder.md`, since archived). These are the rules
that existed only there; this file is now the one place.

- **Never drive from `CMS_*` or `*_VW` objects** unless the object is explicitly governed:
  they are report-support views over snapshots, and a query driven from one inherits the
  snapshot's window and staleness without saying so.
- **Active SA** is `NULLIF(TRIM(SA_STATUS_FLG), '') = '20'` -- never a bare `= '20'` on a
  CHAR column (the blank-string trap above).
- **Optional enrichment is LEFT JOIN, outward from the driving population**, and the
  count is compared before and after each optional join on a known slice; an inner join
  on an optional table (the VEE-exception To Do chain is the recorded example) silently
  drops the population.
- **Paid / balanced logic never reads `MATCH_EVT_ID`.** Match events are cashiering
  bookkeeping, not settlement.
- **ARS / debt on a balance-forward client**: `FREEZE_SW = 'Y' AND NOT_IN_ARS_SW = 'N'` is
  the arrears population. The portal-era rule added `AND ARS_DT IS NOT NULL`; the College
  Station FIFO method above (measured 2026-08-19) KEEPS null-ARS_DT rows in the net total
  and dates PS rows on `ARS_DT`. Use the measured method; the older rule is recorded here
  so nobody re-derives it.
- **No hardcoded cycle lists**; a tenant-specific cycle set is a parameter, never a literal.
