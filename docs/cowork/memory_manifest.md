# Co-work Memory Manifest

Attach these repo paths to Claude Co-work project memory. Prefer pinning files over entire log or archive trees.

## Tier A — always pin

| Path | Why |
|------|-----|
| `AGENTS.md` | Master contract |
| `docs/cowork/system_directions.md` | Co-work instructions (this bundle) |
| `docs/c2m_jaspersoft_delivery_playbook.md` | End-to-end delivery rules |
| `docs/assistant_skills/README.md` | Assistant workflow index |
| `docs/assistant_skills/report_preflight_checklist.md` | Done criteria |
| `docs/assistant_skills/past_mistakes_and_prevention.md` | Known failure patterns |
| `output/ai_cisadm_context.json` | Table semantics, joins, populations |
| `output/workstream_reporting_dictionary.json` | Workstream / report dictionary |
| `output/domain_field_index.json` | Valid Domain item IDs for JRXML |

## Tier B — add by task

### JRXML / reports

- `skills/jrxml_report_builder/SKILL.md`
- `docs/assistant_skills/jrxml_schema_guardrails.md`
- `docs/assistant_skills/jrxml_expression_patterns.md`
- `docs/assistant_skills/domain_report_workflow.md`
- `docs/assistant_skills/troubleshooting_runbook.md`
- `knowledge_base/jaspersoft_charts_visuals_jrs9.md`

### SQL / snapshots / debt

- `skills/sql_report_builder/SKILL.md`
- `skills/sql_validation_guard/SKILL.md`
- `skills/cisadm_domain_modeling/SKILL.md`
- `docs/assistant_skills/cisadm_sql_prompt_guide.md`
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `knowledge_base/c2m_cisadm/workstream_physical_join_paths.md`
- `sql/governance_snippets.sql`

### Domains / derived tables / Ad Hoc performance

- `skills/jaspersoft_derived_table_builder/SKILL.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`
- `knowledge_base/jaspersoft_dynamic_features.md`

### Client promotion / import

- `docs/jaspersoft_client_promotion_pipeline.md`
- `docs/jaspersoft_environment_promotion_troubleshooting.md`
- `docs/jaspersoft_repository_import_debugging_runbook.md`
- `deploy/jaspersoft_client_promotion/README.md`
- `deploy/jaspersoft_client_promotion/client_org_mapping.csv`
- `deploy/jaspersoft_datasources/clients/README.md`

### Snapshot rollout

- `sql/performance/snapshots/deployment_steps/clients/newark/README.md` (or target client)
- `sql/performance/snapshots/docs/snapshot_client_reporting_guide.md`
- `docs/smartcity_client_snapshot_rollout_status_2026-04-30.md`

## Tier C — do not pin

- `.env` (credentials)
- `deploy/**/*.zip`, `archive/**` (large binaries)
- `deploy/snapshot_rollout_logs/**` (reference specific files only when needed)
- Full `output/cisadm_views/**` DDL dumps

## Co-work skills folder

Pin the whole folder:

- `docs/cowork/skills/`
