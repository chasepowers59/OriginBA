# Repository Structure Standard

## Rule Set
- Keep report SQL under `sql/` categorized by purpose.
- Keep domain packages under `domains/exports/`.
- Keep temporary extracted domain work under `domains/working/`.
- Keep automation scripts under `scripts/performance/` and `scripts/repo/`.
- Keep CISADM knowledge assets under `knowledge_base/c2m_cisadm/`.

## Hygiene
- Do not leave ad-hoc ZIP files in repo root.
- Do not commit temp logs from SQL*Plus validation runs.
- Prefer archiving uncertain legacy assets under `archive/<date>/`.
