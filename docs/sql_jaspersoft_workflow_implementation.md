# SQL + Jaspersoft Workflow Implementation

## Purpose
Operational workflow for using local skills and knowledge base to deliver Oracle/Jaspersoft report work consistently.

## Workflow Stages
1. Intake
- Capture business question, consumer, metric definitions, expected output grain, target deliverable type, prompt contract, and validation slice.
- Apply `docs/c2m_jaspersoft_delivery_playbook.md` as the default operating guide.
- Use `knowledge_base/jaspersoft_artifact_model_and_performance.md` to decide report vs Domain vs Ad Hoc vs dashboard and to choose raw-table vs derived-table modeling.

2. Build SQL Logic
- Follow `skills/sql_report_builder/SKILL.md`.
- Use `knowledge_base/oracle_c2m_query_patterns.md`.

3. Convert for Jaspersoft
- Follow `skills/jaspersoft_derived_table_builder/SKILL.md`.
- Use `knowledge_base/jaspersoft_derived_table_rules.md`.
- Use `knowledge_base/jaspersoft_dynamic_features.md` if the request includes dashboards, Ad Hoc views, Topics, drill paths, or embedding.
- Use `knowledge_base/jaspersoft_charts_visuals_jrs9.md` if the request includes report charts, Ad Hoc charts, dashboard chart behavior, or server/UI theme decisions.

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
- Default to Domain-first JRXML and repository-managed input controls unless a raw SQL report is explicitly requested.
- Use Ad Hoc calculated fields for presentation-layer flexibility, not for source-of-truth financial logic.
- Use dashboard-level controls before duplicating prompts across individual dashlets.
- When row preservation or grain is at risk, prefer establishing the correct Oracle result set before exposing it in a Domain or Ad Hoc layer.

## Required Artifacts per Delivery
- SQL file(s) in `sql/`.
- Input control updates in `server/input_controls/` when parameters are used.
- Documentation updates in `docs/` and `knowledge_base/` when behavior changes.
