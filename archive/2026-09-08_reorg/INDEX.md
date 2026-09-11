# Archive 2026-09-08 (repository reorganization)

Nothing here is deleted; every item was superseded, duplicated, or never referenced, and a
pointer stands at its old path (`ARCHIVED.md` in the parent directory, or `README.md` in an
emptied directory). `tests/test_repo_structure.py` (D2, D7) checks that live code never reads
from here and that every row has its pointer. `jaspersoft/README.md` and `README.md` say where
the current equivalent lives.

| original path | why archived | current equivalent |
| --- | --- | --- |
| `exports/` | `source_of_truth_bundle_2026-03-19` -- a frozen fork of docs that already drifted from `docs/` and `knowledge_base/`; zero references | `docs/`, `knowledge_base/` |
| `docs/claude_handoff/` | 2026-07/08 handoff snapshots; its `mcp/originba_oracle_mcp.py` is byte-identical to `scripts/local/originba_oracle_mcp.py` | `scripts/local/originba_oracle_mcp.py`, `.claude/skills/` |
| `docs/mcp-setup.md`, `mcp.json.example` | the SQLcl-in-Cursor MCP setup (Windows era); the MCP actually served is `scripts/local/originba_oracle_mcp.py` with `prod_enabled: false` | `scripts/local/originba_oracle_mcp.py` |
| `Dockerfile`, `railway.toml`, `.railwayignore` | the Railway image; it COPYs `output/snapshot_explorer_catalog.json`, which the catalog retirement (2026-09-04) deleted, so it has not built since. Railway is retired; Fly and Render build `deploy/Dockerfile.api` | `deploy/Dockerfile.api`, `DEPLOYMENT.md` |
| `deploy/{CityCorp,CityCorpPROD,CollegeStation,Ellensburg,Fondulac,Newark,Odessa}DS.zip` | flat backups of the DataSource exports that live, unpacked and documented, under `deploy/jaspersoft_datasources/clients/` | `deploy/jaspersoft_datasources/clients/` |
| `skills/` | eight 2026-03..06 skills nothing could load; folded into `.claude/skills/originba-*/SKILL.md` | `.claude/skills/` |
| `docs/cowork/skills/` | six Co-work paste-in copies (2026-08-11) of skills that now exist in loadable form | `.claude/skills/originba-*/SKILL.md` |
| `sql/performance/snapshots/customer_ops/acct_customer` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/customer_ops/case_prem_contact` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/finance/billable_charge` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/field_ops/crew_ops` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/meter_ops/device_sp` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/new_services/pipeline` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/common/ops_exception` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/payments_cashiering/pay_event` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/debt_mgmt/sa_aged_bal` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/debt_mgmt/wo_proc` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/common/workflow_queue` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client; sql/periodic_reports/ was its only reader and is archived with it | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/field_ops/field_activity` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client; sql/periodic_reports/ was its only reader and is archived with it | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/debt_mgmt/acct_debt` | governed-but-separate snapshot, outside the active-8 stagger since 2026-04; QA and master guide never written | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/debt_mgmt/coll_proc` | governed-but-separate snapshot, outside the active-8 stagger since 2026-04; QA and master guide never written | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/payments_cashiering/pay_tndr_cashier` | Cashiering/Payments snapshot: owner confirmed not in use at any client (2026-09-08) | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/00_consolidation_snapshot_deployment_manifest.md` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/21_create_all_consolidation_snapshot_tables.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/22_deploy_all_consolidation_baseline_procedures.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/23_run_all_consolidation_baseline_refreshes.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/23a_schedule_all_consolidation_baseline_refreshes.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/23b_capture_consolidation_baseline_job_status.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/23d_consolidation_baseline_jobs_ready_gate.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/24_validate_all_consolidation_snapshots.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/24b_consolidation_install_validation_gate.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/25_deploy_all_consolidation_rolling_procedures.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/26_run_all_consolidation_operational_refreshes.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/27_schedule_all_consolidation_snapshots.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/28_capture_latest_consolidation_snapshot_runs.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/apply_6hour_staggered_schedule_consolidation_4am_base.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/apply_daily_staggered_schedule_1am.sql` | superseded 2026-08-21 by apply_6hour_staggered_schedule_1am_base.sql (which includes CMS_SA_SNAPSHOT) | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/deployment_steps/clients/newark_25_4_post_create_grants.sql.bak` | dead backup calling the older originba_ddl_helper | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/unbilled_revenue` | C1_BI_UNBILLED_REV_SNAP: no procedure, no job, no manifest; only consumer was a working-area domain draft | see `README.md` / `jaspersoft/README.md` |
| `sql/periodic_reports` | periodic report pack: owner confirmed not run anywhere; queries two never-deployed consolidation snapshots | see `README.md` / `jaspersoft/README.md` |
| `scripts/local/run_periodic_reports.py` | driver for the archived periodic report pack | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/docs/consolidation_demo_deep_qa.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/docs/consolidation_demo_physical_table_qa.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/docs/consolidation_demo_qa_extended.sql` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/docs/debt_mgmt_acct_debt_snapshot.md` | doc for an archived snapshot | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/docs/debt_mgmt_coll_proc_snapshot.md` | doc for an archived snapshot | see `README.md` / `jaspersoft/README.md` |
| `sql/performance/snapshots/docs/payments_cashiering_pay_tndr_cash_snapshot.md` | doc for an archived snapshot | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/ACCT_CUSTOMER_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/ACCT_DEBT_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/BILLABLE_CHARGE_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/CASE_PREM_CONTACT_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/COLL_PROC_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/CREW_OPS_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/DEVICE_SP_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/FIELD_ACTIVITY_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/NEW_SERVICE_PIPELINE_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/OPS_EXCEPTION_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/PAY_EVENT_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/PAY_TNDR_CASH_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/SA_AGED_BAL_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/WORKFLOW_QUEUE_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/WO_PROC_RPT_CURR_End_User_Friendly.xml` | hand-built domain over a snapshot that is archived (not one of the active-8) | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/current_snapshot_report_packages/Payments___Deposit_Control_Reconciliation_Report.zip` | report package bound to PAY_TNDR_CASH_RPT_CURR, archived with it | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/current_snapshot_report_packages/Payments___Payment_Channel_Summary.zip` | report package bound to PAY_TNDR_CASH_RPT_CURR, archived with it | see `README.md` / `jaspersoft/README.md` |
| `domains/exports/manual_imports/current_snapshot_report_packages/Payments___Tender_Control_Balancing.zip` | report package bound to PAY_TNDR_CASH_RPT_CURR, archived with it | see `README.md` / `jaspersoft/README.md` |
| `domains/working/manual_designs` | hand-authored domain drafts of 2026-04-28 and their backups; the dbt canvases generate domains now | see `README.md` / `jaspersoft/README.md` |
| `domains/working/archive` | hand-authored domain drafts of 2026-04-28 and their backups; the dbt canvases generate domains now | see `README.md` / `jaspersoft/README.md` |
| `domains/working/new_bill_cycle_domain_backups` | hand-authored domain drafts of 2026-04-28 and their backups; the dbt canvases generate domains now | see `README.md` / `jaspersoft/README.md` |
| `scripts/build_consolidation_domain_xml.py` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client (its tooling) | see `README.md` / `jaspersoft/README.md` |
| `scripts/local/audit_consolidation_snapshot_physical_sources.py` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client (its tooling) | see `README.md` / `jaspersoft/README.md` |
| `scripts/local/check_consolidation_field_parity.py` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client (its tooling) | see `README.md` / `jaspersoft/README.md` |
| `scripts/local/run_consolidation_snapshot_demo_qa.sh` | consolidation snapshot: designed 2026-06-11 (cbc1357), never deployed to a client (its tooling) | see `README.md` / `jaspersoft/README.md` |
| `scripts/build_snapshot_explorer_catalog.py` | built output/snapshot_explorer_catalog.json, the legacy portal catalog retired 2026-09-04 | see `README.md` / `jaspersoft/README.md` |
| `scripts/business_process_registry.py` | built output/snapshot_explorer_catalog.json, the legacy portal catalog retired 2026-09-04 | see `README.md` / `jaspersoft/README.md` |
| `scripts/snapshot_explorer_registry.py` | built output/snapshot_explorer_catalog.json, the legacy portal catalog retired 2026-09-04 | see `README.md` / `jaspersoft/README.md` |
| `scripts/build_current_snapshot_report_packages.ps1` | zero references anywhere in the repo or CI | see `README.md` / `jaspersoft/README.md` |
| `scripts/performance/fix_domain_payload_for_import.py` | zero references anywhere in the repo or CI | see `README.md` / `jaspersoft/README.md` |
| `scripts/jaspersoft/build_standard_offering_add_ons_package.py` | zero references anywhere in the repo or CI | see `README.md` / `jaspersoft/README.md` |
| `scripts/jaspersoft/export_standard_offering_domain_inventory.py` | zero references anywhere in the repo or CI | see `README.md` / `jaspersoft/README.md` |
| `scripts/jaspersoft/export_workstream_tables_workbook.py` | zero references anywhere in the repo or CI | see `README.md` / `jaspersoft/README.md` |
| `scripts/jaspersoft/sanitize_standard_offering_export.py` | zero references anywhere in the repo or CI | see `README.md` / `jaspersoft/README.md` |
| `scripts/local/export_admin_config_excel.py` | zero references anywhere in the repo or CI | see `README.md` / `jaspersoft/README.md` |
| `scripts/local/newark_trim_snapshots_2yr_batched.py` | zero references anywhere in the repo or CI | see `README.md` / `jaspersoft/README.md` |
| `tests/test_snapshot_premade_catalog.py` | always skipped: needs output/snapshot_explorer_catalog.json, which no longer exists | see `README.md` / `jaspersoft/README.md` |
| `tests/test_business_process_registry.py` | always skipped: needs output/snapshot_explorer_catalog.json, which no longer exists | see `README.md` / `jaspersoft/README.md` |
| `tests/test_query_builder.py` | always skipped: needs output/snapshot_explorer_catalog.json, which no longer exists | see `README.md` / `jaspersoft/README.md` |
| `docs/workstream_consolidation_snapshot_roadmap.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/smartcity_consolidation_snapshot_rollout_runbook.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/debt_mgmt_acct_debt_adhoc_recipes.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/debt_mgmt_coll_proc_adhoc_recipes.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/payments_cashiering_pay_tndr_cash_adhoc_recipes.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/native_dashboard_inventory_audit.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/snapshot_financial_operations_dashboard_v1.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/jaspersoft_dashboard_build_plan_billing_usage_ft_gl.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/current_snapshot_report_backlog_for_utilities.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/smartcity_demo_snapshot_rollout_runbook.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/smartcity_demo_snapshot_rollout_status.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/smartcity_demo_snapshot_validation_results_2026-05-21.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/smartcity_gap_fill_existing_resources_only.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/analytics_portal_poc.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/refinement-testing-log-2026-02-17.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/repo_cleanup_2026-02-17.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `docs/PR_feature-bi-overhaul.md` | retired-shape or one-off doc (consolidation, app-era catalog, 2026-02/04 exercise records) | see `README.md` / `jaspersoft/README.md` |
| `deploy/standard_offering_add_ons` | add-on packages whose only builder is archived; the shipped package is deploy/jaspersoft_standard_offering/ | see `README.md` / `jaspersoft/README.md` |
| `deploy/jaspersoft_standard_offering_add_ons` | add-on packages whose only builder is archived; the shipped package is deploy/jaspersoft_standard_offering/ | see `README.md` / `jaspersoft/README.md` |
| `scripts/snapshot_portal_config.py` | UX config for the retired CISADM snapshot catalog (date presets per `*_RPT_CURR`); nothing imports it since the catalog retirement on 2026-09-04 | `output/catalog_dbt.json` |
| `sql/performance/snapshots/debt_mgmt/00a_config_discovery_validation.sql` | discovery pack for four snapshots that are all archived | `sql/performance/snapshots/debt_mgmt/cms_sa_snapshot/` |
| `docs/cowork/system_directions.md` | a Co-work paste-in restatement of AGENTS.md (2026-08-11) | `AGENTS.md` |
