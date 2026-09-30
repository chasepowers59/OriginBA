# Skill: CISADM Domain Modeling

## Goal
Design production-safe Oracle C2M reporting data models and joins for Jaspersoft domains.

## Core References
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `knowledge_base/c2m_cisadm/performance_playbook.md`
- `docs/jaspersoft_domain_report_build_standards.md`

## Modeling Rules
1. Choose the artifact intentionally: Domain for shared semantic reuse, Topic for curated self-service, report for pixel-perfect output, dashboard for multi-panel consumption.
2. Preserve business semantics and driving population before tuning.
3. Use raw Domain tables only when the join graph preserves the intended grain without fan-out; otherwise establish the grain in Oracle first with a derived table or governed SQL layer.
4. Filter high-volume fact tables early (`D1_USAGE`, `C1_USAGE`) and use Topics or pre-filters for self-service over large facts.
5. Pre-aggregate detail tables before dimensional joins when raw detail would multiply rows.
6. Keep optional enrichment joins outer and keep lookup joins language-safe (`LANGUAGE_CD='ENG'`).
7. Avoid non-equality joins in Domains unless composite and validated for row counts.
8. Use minimum-path joins and join weights on complex Domains to reduce ambiguous paths.
9. Use data staging only for bounded, slow-changing Topic datasets where freshness tradeoffs are acceptable.
10. Keep rollback-safe assets (hide risky details, do not hard-delete).
11. All testing and diagnostics must be read-only.

## Validation Rules
- Always run parity SQL before publishing optimized logic.
- Compare counts before and after each optional join on a known slice.
- Require explain-plan evidence for performance claims.
- Keep result deltas zero for equivalent business output.
