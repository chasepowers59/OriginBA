# Skill: CISADM Reporting Gap Analysis

## Goal
Audit reporting gaps in a client-specific `CISADM` schema and turn them into concrete, governed Oracle/Jaspersoft actions.

## Inputs Required
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `docs/reporting_gap_assessment/README.md`
- `docs/reporting_gap_assessment/03_workstream_coverage_matrix.md`
- `docs/reporting_gap_assessment/04_reporting_gap_findings.md`
- `knowledge_base/c2m_cisadm/reporting_gap_assessment_playbook.md`
- `sql/reporting_assessment/01_candidate_configuration_tables.sql`
- `sql/reporting_assessment/02_transactional_value_inventory.sql`
- existing workstream docs, snapshot packages, and Domain artifacts relevant to the current request

## Steps
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

## Validation
- Run `sql/reporting_assessment/01_candidate_configuration_tables.sql`
- Run `sql/reporting_assessment/02_transactional_value_inventory.sql`
- Confirm the selected source tables and codes are documented in the coverage matrix
- Confirm the chosen grain and artifact type are explicitly justified
- Keep DB discovery read-only unless the user explicitly approves implementation

## Failure Handling
- If the environment-specific configuration cannot be proven from data, stop and mark it as unverified rather than guessing.
- If the join graph multiplies rows, stop and recommend Oracle-side grain control before Domain work.
- If a workstream already has a governed artifact, do not invent a second one without documenting why the first is insufficient.

## Output Contract
- updated workstream coverage matrix
- updated reporting-gap findings file
- clear artifact recommendation per gap
- custom-skill backlog items when repeated schema or logic patterns should be standardized
