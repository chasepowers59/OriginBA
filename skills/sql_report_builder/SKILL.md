# Skill: SQL Report Builder (Oracle C2M)

## When to Use
Use when building or modifying Oracle SQL report datasets for C2M billing workflows.

## Inputs
- Business question and expected KPI definitions.
- Target grain (cycle-level, account-level, segment-level).
- Environment scope (DEV/QA/PROD).

## Required References
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/billing_cycle_reporting_semantics.md`

## Steps
1. Define report grain and event scope explicitly.
2. Select authoritative source table for each metric (actual vs expected).
3. Add active SA filter (`SA_STATUS_FLG='20'`) where required.
4. Add cycle/date semantic fields (`EVENT_DATE`, `CYCLE_LAST_EVENT_DATE`).
5. Add lookup enrichment for user-facing descriptions.
6. Include fallback handling for missing descriptions/codes.
7. Save SQL under `sql/` with focused name and comments.

## Output Contract
- Query returns deterministic field list.
- No hardcoded cycle lists.
- Clear semantic column names.
