---
name: originba-jaspersoft-domain-modeling
description: Design Jaspersoft Domains, join trees, Topics, and Ad Hoc performance patterns for Oracle C2M.
---

# OriginBA Jaspersoft Domain Modeling

## When to use

- Domain or Topic design
- Ad Hoc slowness or row fan-out
- Choosing Domain vs derived table vs snapshot

## Required references

- `skills/cisadm_domain_modeling/SKILL.md`
- `skills/jaspersoft_derived_table_builder/SKILL.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`

## Steps

1. Choose artifact: Domain vs Topic vs Report vs Dashboard.
2. Raw Domain joins only if grain is preserved without fan-out.
3. If grain is at risk, establish it in Oracle first (derived table or `*_RPT_CURR` snapshot).
4. Inner joins on optional tables drop population (example: VEE Exception To Do chain).
5. Device Domain: avoid `CMS_DVC_ACCT` unless SA/account fields are required.
6. Use minimum-path joins and join weights on complex Domains.
7. Parity: compare row counts before and after each optional join on a validation slice.
8. For Ad Hoc crosstabs, avoid unnecessary totals (Jaspersoft runs the join graph multiple times).

## Output contract

- Intended grain documented
- Join graph preserves driving population on validation slice
- Performance recommendation states live Domain vs snapshot path
