# SQL + Jaspersoft Knowledge Base

## Purpose
Central reference used during Oracle SQL and Jaspersoft report work so implementation is consistent across environments.

## Contents
- `jaspersoft_artifact_model_and_performance.md`: report vs Ad Hoc vs dashboard vs Domain guidance, plus raw-table vs derived-table performance and row-preservation rules.
- `jaspersoft_charts_visuals_jrs9.md`: current JRS 9 chart, dashboard, theme, and embedding customization guidance.
- `oracle_c2m_query_patterns.md`: Oracle/C2M-safe SQL design patterns.
- `jaspersoft_derived_table_rules.md`: parser-safe derived table rules and known pitfalls.
- `jaspersoft_dynamic_features.md`: recommended use of dashboard controls, Topics, Ad Hoc calculations, drill paths, and Visualize.js.
- `billing_cycle_reporting_semantics.md`: canonical business logic and field semantics for billing cycle reports.
- `validation_playbook.md`: repeatable validation procedure before report signoff.

## How To Use
1. Start with `jaspersoft_artifact_model_and_performance.md` to choose the right Jaspersoft artifact and data-shaping strategy.
2. Use `oracle_c2m_query_patterns.md` and `jaspersoft_derived_table_rules.md` for Oracle and parser-safe SQL work.
3. Use `jaspersoft_charts_visuals_jrs9.md` and `jaspersoft_dynamic_features.md` when the request involves charts, dashboards, Ad Hoc views, self-service, drill paths, or embedding.
4. Apply business semantics from `billing_cycle_reporting_semantics.md`.
5. Execute validation steps from `validation_playbook.md`.
6. Store any newly discovered edge cases back into this knowledge base.
