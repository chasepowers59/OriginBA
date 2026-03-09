# Local Skills Workflow

## Purpose
Reusable execution playbooks for SQL and Jaspersoft work in this repo.

## Skills
- `skills/sql_report_builder/SKILL.md`
- `skills/jaspersoft_derived_table_builder/SKILL.md`
- `skills/sql_validation_guard/SKILL.md`
- `skills/c2m_usage_performance_validation/SKILL.md`
- `skills/cisadm_domain_modeling/SKILL.md`

## Workflow
1. Use `sql_report_builder` to design SQL with correct semantics.
2. Use `jaspersoft_derived_table_builder` to convert into parser-safe derived table SQL.
3. Use `sql_validation_guard` to validate parity and reconciliation.
4. Use `cisadm_domain_modeling` for join-model safety and domain-first patterns.
5. Use `c2m_usage_performance_validation` to execute zero-diff performance validation.
6. All skill workflows are read-only for DB validation unless explicitly approved otherwise.
7. Use `scripts/performance/run_sql_quality_workflow.ps1` for deterministic static gates and optional read-only DB checks.

## Knowledge Base Dependency
All skills reference:
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`
- `knowledge_base/billing_cycle_reporting_semantics.md`
- `knowledge_base/validation_playbook.md`
