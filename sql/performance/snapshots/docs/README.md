# Snapshot Documentation

This folder is the central documentation package for the governed snapshot program.

Keep snapshot-facing resources here so the SQL workspaces and the documentation stay together.

The matching Domain XML files are now also copied into each active snapshot workspace. Use the snapshot folder when you want the full local implementation package in one place, and use `domains/exports/manual_imports/` when you need the importable server bundle.

## Core operating docs
- `legacy_domain_to_snapshot_modernization_playbook.md`
- `snapshot_modernization_checklist.md`
- `snapshot_sqldeveloper_runbook.md`
- `snapshot_impact_assessment.md`
- `snapshot_measured_resource_impact_summary_2026-04-17.md`
- `snapshot_xml_inventory.md`
- `workstream_snapshot_catalog.md`
- `business_question_snapshot_coverage.md`

## Snapshot business docs
- `billing_bseg_billed_usage_snapshot.md`
- `billing_bseg_sq_usage_snapshot.md`
- `finance_ft_rpt_curr_snapshot.md`
- `finance_ft_gl_distribution_snapshot.md`
- `debt_mgmt_acct_debt_snapshot.md`
- `debt_mgmt_coll_proc_snapshot.md`
- `meter_ops_d1_usage_snapshot.md`
- `meter_ops_d1_usage_scalar_snapshot.md`
- `meter_ops_final_measurement_snapshot.md`
- `payments_cashiering_pay_tndr_cash_snapshot.md`

## Usage
- Start with `workstream_snapshot_catalog.md` to choose the right snapshot.
- Use `legacy_domain_to_snapshot_modernization_playbook.md` when building the next snapshot from an older Domain.
- Use `snapshot_sqldeveloper_runbook.md` when validating the live table, procedure, and scheduler job.
- Use `snapshot_impact_assessment.md` and `../impact/` for read-only database impact and trim-fat review.
