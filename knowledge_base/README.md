# SQL + Jaspersoft Knowledge Base

## Purpose
Central reference used during Oracle SQL and Jaspersoft report work so implementation is consistent across environments.

## Contents
- `oracle_c2m_query_patterns.md`: Oracle/C2M-safe SQL design patterns.
- `jaspersoft_derived_table_rules.md`: parser-safe derived table rules and known pitfalls.
- `billing_cycle_reporting_semantics.md`: canonical business logic and field semantics for billing cycle reports.
- `validation_playbook.md`: repeatable validation procedure before report signoff.

## How To Use
1. Start with `oracle_c2m_query_patterns.md` and `jaspersoft_derived_table_rules.md`.
2. Apply business semantics from `billing_cycle_reporting_semantics.md`.
3. Execute validation steps from `validation_playbook.md`.
4. Store any newly discovered edge cases back into this knowledge base.
