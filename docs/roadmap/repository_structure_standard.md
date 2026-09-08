# Repository Structure Standard

Rewritten 2026-09-08 with the reorganization. The machine-enforced form is
`scripts/repo/repo_structure_audit.ps1` (run by `scripts/performance/run_sql_quality_workflow.ps1`);
`tests/test_repo_structure.py` checks the same contract from pytest. Where the two disagree
with this page, fix this page.

## What lives where

| Area | Home | Rule |
| --- | --- | --- |
| Portal app | `api/`, `apps/analytics-portal/`, `config/`, `data/`, `output/catalog_dbt.json` | Runtime paths; never moved. The catalog is generated in `originba_dbt` (`scripts/build_portal_catalog.py`). |
| Jaspersoft delivery | `jaspersoft/README.md` is the index; assets stay at their pinned paths: `reports/`, `server/input_controls/`, `deploy/jaspersoft_*`, `deploy/snapshot_rollout_logs/`, `domains/` | Domains over the dbt canvases are GENERATED in `originba_dbt/jaspersoft/domains/`; hand-built domains live under `domains/exports/manual_imports/`. |
| Active snapshots (the active-8) | `sql/performance/snapshots/` -- `deployment_steps/` 01-13, `clients/`, `qa/`, `impact/`, `indexes/`, the per-table dirs, `docs/` (its doc home, incl. `docs/recipes/`) | Only the active-8 tables (`FT`, `BSEG_BILLED_USAGE`, `BSEG_SQ_USAGE`, `D1_MSRMT`, `FT_GL_DISTRIBUTION`, `D1_USAGE`, `D1_USAGE_SCALAR_DTL` `_RPT_CURR`, and `CMS_SA_SNAPSHOT`) may be named outside `archive/`. |
| Per-client SQL | `sql/clients/<client>/` | Handwritten; a client deliverable, not a snapshot. |
| Governed SQL packs | `sql/performance/{bill_cycle,billed_usage/validation}`, `sql/reconciliation/billing`, `sql/diagnostics/cisadm_dictionary` | Pinned by `.github/workflows/sql-quality.yml`; read-only SQL only (`scripts/repo/sql_read_only_guard.py`). |
| Automation | `scripts/jaspersoft/`, `scripts/local/`, `scripts/performance/`, `scripts/repo/` | `scripts/` is an import root for tests. |
| Knowledge | `knowledge_base/c2m_cisadm/`, `docs/cisadm_schema_agent_reference.md`, `docs/assistant_skills/` | Reference corpus; the loadable skills are `.claude/skills/*/SKILL.md`, the only skill home. |
| Client registry | `originba_dbt/clients.yml` (canonical), exported to `config/clients.export.yml` | No script carries its own client list. |
| Archive | `archive/<date>/` mirroring original paths, `INDEX.md` at its root | Archive, never delete; leave `ARCHIVED.md` (or `README.md` in an emptied directory) at the old path naming each item. Live code, CI and docs never reference `archive/`. |

## Hygiene
- No ad-hoc ZIPs in the repo root (the audit warns).
- No SQL*Plus temp logs, no `.env*` backups (gitignored), no credential values anywhere.
- A generated artifact is regenerated, not hand-edited: `config/clients.export.yml`, `client_org_mapping.csv`, `output/catalog_dbt.json`.
