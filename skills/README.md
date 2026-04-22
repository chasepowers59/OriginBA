# Local Skills Workflow

## Purpose
Reusable execution playbooks for SQL and Jaspersoft work in this repo.

## Skills
- `skills/sql_report_builder/SKILL.md`
- `skills/jaspersoft_derived_table_builder/SKILL.md`
- `skills/sql_validation_guard/SKILL.md`
- `skills/c2m_usage_performance_validation/SKILL.md`
- `skills/cisadm_domain_modeling/SKILL.md`
- `skills/cisadm_reporting_gap_analysis/SKILL.md`

## Workflow
1. Use `cisadm_domain_modeling` first to choose report vs Domain vs Topic vs Ad Hoc vs dashboard and to decide whether raw tables or a derived table are row-safe.
2. Use `sql_report_builder` to design Oracle SQL with the correct grain, driving population, and business semantics.
3. Use `jaspersoft_derived_table_builder` only when the semantic layer needs a parser-safe derived table or controlled SQL-backed shape.
4. Use `sql_validation_guard` to validate parity, preserved rows, cache-sensitive behavior, and reconciliation.
5. Use `c2m_usage_performance_validation` to execute zero-diff performance validation for billed-usage optimization work.
6. Use `cisadm_reporting_gap_analysis` when the goal is to inventory client-specific configuration, identify missing governed layers, and document workstream reporting gaps before building artifacts.
7. All skill workflows are read-only for DB validation unless explicitly approved otherwise.
8. Use `scripts/performance/run_sql_quality_workflow.ps1` for deterministic static gates and optional read-only DB checks.

## Knowledge Base Dependency
All skills reference:
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/jaspersoft_charts_visuals_jrs9.md`
- `knowledge_base/jaspersoft_dynamic_features.md`
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`
- `knowledge_base/billing_cycle_reporting_semantics.md`
- `knowledge_base/validation_playbook.md`
