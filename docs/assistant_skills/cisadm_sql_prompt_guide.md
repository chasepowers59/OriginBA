# CISADM SQL Prompt Guide

Use this template when asking Cursor to generate Oracle C2M SQL. It routes the agent through repo source-of-truth files and population checks.

## Prompt Template

```text
Workstream: <billing|cashiering|customer_ops|debt_mgmt|field_ops|finance|meter_ops|new_services|common>
Client: demo|qa|prod|<client_alias>
Business question: <natural language question>
Expected grain: <account|SA|bill|bseg|charge line|payment|activity|device|...>
Validation slice: <known counts, date range, or cycle to test against>
Constraints:
- read-only SELECT
- preserve driving population
- LEFT JOIN enrichment lookups/BODA views
- no credentials in SQL
References:
- output/ai_cisadm_context.json
- knowledge_base/c2m_cisadm/cisadm_core_model.md
- skills/sql_report_builder/SKILL.md
```

## Example

```text
Workstream: new_services
Client: demo
Business question: List active customers with a pending water SA that has no linked service point.
Expected grain: one row per SA
Validation slice: compare COUNT(*) to CI_SA driving population minus CI_SA_SP matches
Constraints: read-only, LEFT JOIN enrichment, no credentials
References: output/ai_cisadm_context.json
```

Expected join path:
- Drive from `CI_SA`
- LEFT JOIN `CI_SA_SP` to detect missing SP linkage
- LEFT JOIN account/customer enrichment (`CI_ACCT`, `CI_ACCT_PER`, `CI_PER_NAME`)
- Apply status filters in SQL only when the business question requires them; prefer ad hoc filters in JRS for exploratory snapshots

## Before Accepting Generated SQL

1. Check `physical.stats_population_status` and `client_health.population_status` in `output/ai_cisadm_context.json` for every source table used.
2. Confirm driving population and output grain are stated explicitly.
3. Confirm optional joins are LEFT JOINs and do not silently drop rows.
4. Run parity validation with `skills/sql_validation_guard/SKILL.md` when the SQL feeds a snapshot, derived table, or report population.

## Refresh Context

```bash
python3 scripts/build_ai_cisadm_context.py
python3 scripts/local/run_workstream_table_health.sh demo
python3 scripts/performance/build_cisadm_dictionary_coverage.py
python3 scripts/build_ai_cisadm_context.py --client demo
```

## Population Status Meanings

| Status | Meaning |
|--------|---------|
| `populated` | Table exists and `COUNT(*) > 0` on the target client |
| `empty` | Table exists but has zero rows on the target client |
| `missing` | Table not present in `ALL_TABLES` for CISADM on the target client |
| `unknown` | No live health check; rely on optimizer `NUM_ROWS` from dictionary extract |

Treat `empty` and `missing` as high-risk for driving populations. Use alternate tables, snapshots, or document the gap explicitly.
