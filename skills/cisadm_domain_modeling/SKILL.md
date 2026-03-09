# Skill: CISADM Domain Modeling

## Goal
Design production-safe Oracle C2M reporting data models and joins for Jaspersoft domains.

## Core References
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `knowledge_base/c2m_cisadm/performance_playbook.md`
- `docs/jaspersoft_domain_report_build_standards.md`

## Modeling Rules
1. Preserve business semantics before tuning.
2. Filter high-volume fact tables early (`D1_USAGE`, `C1_USAGE`).
3. Pre-aggregate detail tables before dimensional joins.
4. Keep lookup joins language-safe (`LANGUAGE_CD='ENG'`).
5. Keep rollback-safe assets (hide risky details, do not hard-delete).
6. All testing and diagnostics must be read-only.

## Validation Rules
- Always run parity SQL before publishing optimized logic.
- Require explain-plan evidence for performance claims.
- Keep result deltas zero for equivalent business output.
