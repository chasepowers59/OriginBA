---
name: originba-validation-signoff
description: Produce Standard Offering QA documents, manager updates, and structured signoff evidence.
---

# OriginBA Validation Signoff

## When to use

- Standard Offering Report Library QA Word docs
- Manager status updates
- Jira ticket drafting for known defect classes
- Final signoff checklists

## Required references

- `docs/assistant_skills/report_preflight_checklist.md`
- `skills/sql_validation_guard/SKILL.md`
- `output/doc/templates/README.txt`
- `scripts/doc/build_standard_offering_validation_doc.py`

## Steps

1. Standard Offering QA document:
   ```bash
   python3 scripts/doc/build_standard_offering_validation_doc.py \
     --client <Client> \
     --test-version 25.4 \
     --datasource <Client>_DS \
     --author "Chase Powers" \
     --status PASS
   ```
2. JRXML/report signoff: follow `report_preflight_checklist.md`.
3. SQL/snapshot signoff: follow `sql_validation_guard/SKILL.md` (PASS/FAIL, deltas, evidence queries).
4. Jira tickets: one ticket per defect class (JRXML schema, import wrapper, Domain join, perf, scheduler).
5. Do not claim functional CIS testing when only Jaspersoft execution was validated.

## Output contract

- Client-named `.docx` under `output/doc/` when generating QA docs
- Explicit limitation statement (execution vs functional CIS)
- Evidence paths cited
