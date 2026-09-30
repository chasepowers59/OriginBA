---
name: originba-cisadm-sql-builder
description: Write read-only Oracle CISADM SQL for validation, KPIs, snapshot QA, and derived-table preparation.
---

# OriginBA CISADM SQL Builder

## When to use

- Validation SQL, parity checks, KPI definitions
- Snapshot BEFORE/AFTER QA
- Derived-table SQL before Domain ingestion

## Required references

- `skills/sql_report_builder/SKILL.md`
- `output/ai_cisadm_context.json`
- `knowledge_base/c2m_cisadm/workstream_physical_join_paths.md`
- `knowledge_base/oracle_c2m_query_patterns.md`
- `docs/assistant_skills/cisadm_sql_prompt_guide.md`

## Steps

1. Load `output/ai_cisadm_context.json` for table semantics and join hints.
2. State driving population, output grain, and validation slice before writing joins.
3. Do not use `CMS_*` or `*_VW` as driving tables unless explicitly governed.
4. Preserve driving population; use LEFT JOIN for optional enrichment.
5. Read-only SQL only; no `SELECT *`; deterministic column aliases.
6. Active SA filter: `NULLIF(TRIM(SA.SA_STATUS_FLG),'') = '20'`.
7. ARS / debt (balance-forward clients): `FREEZE_SW='Y' AND NOT_IN_ARS_SW='N' AND ARS_DT IS NOT NULL`. Do not use `MATCH_EVT_ID` for paid/balanced logic.
8. Compare counts before and after optional joins on a known slice.
9. Client execution:
   ```bash
   python3 scripts/local/run_client_oracle_sql.py --client <client> --sql "..."
   ```

## Output contract

- Explicit grain and driving population documented
- No hardcoded tenant-specific cycle lists unless scoped
- Validation slice and evidence queries included
