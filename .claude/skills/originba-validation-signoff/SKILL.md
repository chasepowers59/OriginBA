---
name: originba-validation-signoff
description: Produce Standard Offering QA documents, manager updates, and structured signoff evidence.
---

# OriginBA Validation Signoff

## When to use

- Standard Offering Report Library QA Word docs
- Manager status updates
- Jira ticket drafting for known defect classes
- Final signoff checklists

## Required references

- `docs/assistant_skills/report_preflight_checklist.md`
- the *SQL validation guard* section below
- `output/doc/templates/README.txt`
- `scripts/doc/build_standard_offering_validation_doc.py`

## Steps

1. Standard Offering QA document:
   ```bash
   python3 scripts/doc/build_standard_offering_validation_doc.py \
     --client <Client> \
     --test-version 25.4 \
     --datasource <Client>_DS \
     --author "Chase Powers" \
     --status PASS
   ```
2. JRXML/report signoff: follow `report_preflight_checklist.md`.
3. SQL/snapshot signoff: follow the *SQL validation guard* section below (PASS/FAIL, deltas, evidence queries).
4. Jira tickets: one ticket per defect class (JRXML schema, import wrapper, Domain join, perf, scheduler).
5. Do not claim functional CIS testing when only Jaspersoft execution was validated.

## Output contract

- Client-named `.docx` under `output/doc/` when generating QA docs
- Explicit limitation statement (execution vs functional CIS)
- Evidence paths cited

## SQL validation guard

*Folded from the *SQL validation guard* section below on 2026-09-08; the file is archived.*

### Goal
Validate SQL and Jaspersoft changes before signoff so parity, preserved population, and freshness assumptions are explicit.

### Required References
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/validation_playbook.md`
- `knowledge_base/billing_cycle_reporting_semantics.md`

### Steps
1. Run freshness and parity checks in Oracle.
2. Run reconciliation checks for expected vs actual reasonableness.
3. Compare row counts before and after optional joins or derived-table shaping on a known slice.
4. Export Jasper output for the same filter slice and compare control totals/fingerprint.
5. Note whether the Jaspersoft result came from fresh query execution, Ad Hoc cache, or staged Topic data when that distinction matters.
6. Document mismatches and root cause (logic vs data window vs environment issue).
7. Update docs/KB if a new edge case is discovered.

### Output Contract
- Explicit PASS/FAIL status.
- Delta metrics documented when failed.
- Evidence query outputs captured for audit trail.
- Row-grain or preserved-population risks documented when present.

## C2M usage performance validation

*Folded from `skills/c2m_usage_performance_validation/SKILL.md` on 2026-09-08; the file is archived.*

### Goal
Validate optimized vs original C2M usage-reporting logic with deterministic, read-only SQL parity checks.

### Inputs
- Date ranges (`start_ts`, `end_ts`)
- CISADM access for:
  - `CI_ACCT`
  - `CI_SA`
  - `C1_USAGE`
  - `D1_USAGE`
  - `D1_USAGE_SCALAR_DTL`
- Read-only DB credentials only.

### Required References
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/validation_playbook.md`

### Runbook
1. Run read-only preflight: `sql/performance/billed_usage/validation/00_read_only_preflight.sql`
2. Run original aggregation: `sql/performance/billed_usage/validation/01_original_agg.sql`
3. Run optimized aggregation: `sql/performance/billed_usage/validation/02_optimized_agg.sql`
4. Compare results: `sql/performance/billed_usage/validation/03_compare_original_vs_optimized.sql`
5. Validate sample IDs: `sql/performance/billed_usage/validation/04_sample_usg_ext_id_check.sql`
6. Execute complete cycle: `07_run_all_ranges.sql`
7. If the optimized logic will feed a Domain or derived table, confirm the validated row grain matches the intended semantic layer grain.

### Pass Criteria
- All per-class differences = 0
- Sample-level differences = 0
- Queries run successfully in read-only mode.

### Automation
- Runner: `scripts/performance/run_billed_usage_validation.ps1`

## CISADM reporting gap analysis

*Folded from `skills/cisadm_reporting_gap_analysis/SKILL.md` on 2026-09-08; the file is archived.*

### Goal
Audit reporting gaps in a client-specific `CISADM` schema and turn them into concrete, governed Oracle/Jaspersoft actions.

### Inputs Required
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `docs/reporting_gap_assessment/README.md`
- `docs/reporting_gap_assessment/03_workstream_coverage_matrix.md`
- `docs/reporting_gap_assessment/04_reporting_gap_findings.md`
- `knowledge_base/c2m_cisadm/reporting_gap_assessment_playbook.md`
- `sql/reporting_assessment/01_candidate_configuration_tables.sql`
- `sql/reporting_assessment/02_transactional_value_inventory.sql`
- existing workstream docs, snapshot packages, and Domain artifacts relevant to the current request

### Steps
1. Start with the workstream and business question, not the table list.
2. Check whether a governed snapshot, Domain, Topic, or report SQL already exists in the repo for that workstream.
3. Use `sql/reporting_assessment/01_candidate_configuration_tables.sql` to inventory configuration and lookup tables actually present in the target `CISADM` schema.
4. Use `sql/reporting_assessment/02_transactional_value_inventory.sql` and targeted follow-up SQL to identify which business codes are actually active in client data.
5. Record the results in `docs/reporting_gap_assessment/03_workstream_coverage_matrix.md`.
6. Decide the smallest safe Oracle grain for the business question.
7. Choose the right artifact:
   - raw Domain only when row-safe
   - Topic for curated self-service
   - governed snapshot when grain, performance, or row preservation need Oracle control
   - report SQL only when the use case is narrow and not reusable
8. Document confirmed findings and backlog in `docs/reporting_gap_assessment/04_reporting_gap_findings.md`.
9. When repeated patterns emerge, update or add a repo skill so future work can reuse the discovered schema logic and validation rules.

### Validation
- Run `sql/reporting_assessment/01_candidate_configuration_tables.sql`
- Run `sql/reporting_assessment/02_transactional_value_inventory.sql`
- Confirm the selected source tables and codes are documented in the coverage matrix
- Confirm the chosen grain and artifact type are explicitly justified
- Keep DB discovery read-only unless the user explicitly approves implementation

### Failure Handling
- If the environment-specific configuration cannot be proven from data, stop and mark it as unverified rather than guessing.
- If the join graph multiplies rows, stop and recommend Oracle-side grain control before Domain work.
- If a workstream already has a governed artifact, do not invent a second one without documenting why the first is insufficient.

### Output Contract
- updated workstream coverage matrix
- updated reporting-gap findings file
- clear artifact recommendation per gap
- custom-skill backlog items when repeated schema or logic patterns should be standardized
