# Repository Structure Standard

## Rule Set
- Keep report SQL under `sql/` categorized by purpose.
- Keep domain packages under `domains/exports/`.
- Keep manually retained import-ready packages under `domains/exports/manual_imports/`.
- Keep temporary extracted domain work under `domains/working/`.
- Keep automation scripts under `scripts/performance/` and `scripts/repo/`.
- Keep CISADM knowledge assets under `knowledge_base/c2m_cisadm/`.
- Keep one-off ZIP bundles, patch variants, and uncertain packaging artifacts under `archive/<date>/root_zip_cleanup/`.

## Hygiene
- Do not leave ad-hoc ZIP files in repo root.
- Do not commit temp logs from SQL*Plus validation runs.
- Prefer archiving uncertain legacy assets under `archive/<date>/`.
