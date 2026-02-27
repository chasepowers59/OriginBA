# Local Skills Workflow

## Purpose
Reusable execution playbooks for SQL and Jaspersoft work in this repo.

## Skills
- `skills/sql_report_builder/SKILL.md`
- `skills/jaspersoft_derived_table_builder/SKILL.md`
- `skills/sql_validation_guard/SKILL.md`

## Workflow
1. Use `sql_report_builder` to design SQL with correct semantics.
2. Use `jaspersoft_derived_table_builder` to convert into parser-safe derived table SQL.
3. Use `sql_validation_guard` to validate parity and reconciliation.

## Knowledge Base Dependency
All skills reference:
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`
- `knowledge_base/billing_cycle_reporting_semantics.md`
- `knowledge_base/validation_playbook.md`
