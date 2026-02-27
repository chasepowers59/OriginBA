# SQL + Jaspersoft Workflow Implementation

## Purpose
Operational workflow for using local skills and knowledge base to deliver Oracle/Jaspersoft report work consistently.

## Workflow Stages
1. Intake
- Capture business question, metric definitions, and expected output grain.

2. Build SQL Logic
- Follow `skills/sql_report_builder/SKILL.md`.
- Use `knowledge_base/oracle_c2m_query_patterns.md`.

3. Convert for Jaspersoft
- Follow `skills/jaspersoft_derived_table_builder/SKILL.md`.
- Use `knowledge_base/jaspersoft_derived_table_rules.md`.

4. Validate
- Follow `skills/sql_validation_guard/SKILL.md`.
- Use `knowledge_base/validation_playbook.md`.

5. Publish and Handoff
- Document known assumptions and date-window semantics.
- Provide client-facing interpretation notes.

## Decision Rules
- If parser errors occur in Jaspersoft, prioritize parser-safe SQL shape over advanced SQL syntax.
- If expected vs actual differs significantly, validate event window and cycle schedule before changing business logic.
- If environment differs, never hardcode cycle lists; derive from data.

## Required Artifacts per Delivery
- SQL file(s) in `sql/`.
- Input control updates in `server/input_controls/` when parameters are used.
- Documentation updates in `docs/` and `knowledge_base/` when behavior changes.
