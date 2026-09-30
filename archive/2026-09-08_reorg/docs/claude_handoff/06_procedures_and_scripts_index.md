# 06 — Procedures & scripts index

## Oracle runners

| Script | Role |
|--------|------|
| `scripts/local/run_client_oracle_sql.py` | Primary client SQL runner |
| `scripts/local/oracle_client.py` | Thick init + env load + DSN normalize |
| `scripts/local/originba_oracle_mcp.py` | Read-only stdio MCP wrapper |
| `scripts/local/run_oracle_sql.py` | Generic ORACLE_* runner |
| `scripts/local/newark_after_qa_2yr.py` | Newark AFTER QA pack |
| `scripts/local/newark_trim_snapshots_2yr.py` | Legacy trim helpers |

## Snapshot SQL roots

| Path | Role |
|------|------|
| `sql/performance/snapshots/deployment_steps/` | Central deploy orchestration |
| `sql/performance/snapshots/finance/` | FT / FT_GL |
| `sql/performance/snapshots/billed_usage/` | BSEG billed + SQ |
| `sql/performance/snapshots/meter_ops/` | Usage / measurement |
| `sql/performance/snapshots/debt_mgmt/` | CMS_SA_SNAPSHOT, aging |
| `sql/performance/snapshots/docs/` | Client reporting guides |

## Jaspersoft

| Path | Role |
|------|------|
| `scripts/jaspersoft/` | Build / verify / promote |
| `deploy/jaspersoft_client_promotion/` | Client staging + prepared imports |
| `deploy/jaspersoft_environment_promotion/` | Internal env profiles |
| `deploy/jaspersoft_datasources/clients/` | Canonical client DS exports |
| `server/input_controls/` | Report parameter contracts |
| `reports/` | JRXML sources |

## Validation / docs generators

| Script | Role |
|--------|------|
| `scripts/validate_jrxml_schema.py` | JRXML schema guard |
| `scripts/doc/build_standard_offering_validation_doc.py` | Client QA Word docs |
| `scripts/build_ai_cisadm_context.py` | Regenerate AI CISADM context |

## Source of truth files

- `AGENTS.md`
- `output/ai_cisadm_context.json`
- `output/workstream_reporting_dictionary.json`
- `output/domain_field_index.json`
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/c2m_cisadm/workstream_physical_join_paths.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`

## Co-work skills pack

`docs/cowork/` — system directions + 6 skills + memory manifest
