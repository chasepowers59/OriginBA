# Skill: SQL Report Builder (Oracle C2M)

## Goal
Build Oracle SQL datasets for C2M reporting without losing required rows, changing the intended grain, or introducing environment-specific fragility.

## Inputs
- Business question and expected KPI definitions.
- Target grain (cycle-level, account-level, segment-level).
- Environment scope (DEV/QA/PROD).
- Deliverable type (direct SQL report, derived table, Domain feed, dashboard feed, or validation SQL).
- Known validation slice for parity testing.

## Required References
- `output/ai_cisadm_context.json`
- `docs/assistant_skills/cisadm_sql_prompt_guide.md`
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `knowledge_base/billing_cycle_reporting_semantics.md`

## Pre-Steps (mandatory)
1. Identify the workstream from the business question.
2. Load `output/ai_cisadm_context.json` for candidate tables, join hints, and population status.
3. If client-specific accuracy matters, confirm live table health:
   - `python3 scripts/local/run_workstream_table_health.sh <client>`
   - or inspect `deploy/snapshot_rollout_logs/<client>/table_health.json`
4. Do not use tables marked `population_status: empty` or `missing` as the driving population without documenting the gap or choosing a snapshot/alternate source.
5. State driving population, output grain, and validation slice before writing joins.

## Steps
1. Define the driving population, output grain, event scope, and validation slice before writing joins.
2. Select the authoritative source table for each metric and label actual vs expected populations explicitly.
3. Decide whether the SQL should feed a direct report or a Domain/derived table. If a raw Domain join graph would multiply or drop rows, establish the grain in Oracle first.
4. Apply active/frozen/date-window rules and C2M blank-string normalization where required.
5. Join optional enrichment tables outward from the driving population so descriptive lookups do not drop required rows.
6. Add cycle/date semantic fields such as `EVENT_DATE` and `CYCLE_LAST_EVENT_DATE` when the business logic depends on event recency.
7. Expose stable aliases and filterable fields; avoid parser-fragile bind syntax if the SQL may be reused in a derived table.
8. Save SQL under `sql/` with focused naming and short comments that document grain or assumptions when not obvious.

## Output Contract
- Query returns deterministic field list.
- No hardcoded cycle lists.
- Clear semantic column names.
- Driving population and output grain are explicit.
- Optional joins do not silently drop required rows.
