# Snapshot Workspaces

Snapshot build assets live here so each artifact follows the same structure:

- `snapshots/<workstream>/<subset>/`

Examples:
- `snapshots/meter_ops/d1_usage/`
- `snapshots/billed_usage/bseg_sq_usage/`
- `snapshots/debt_mgmt/acct_debt/`
- `snapshots/finance/ft_rpt_curr/`
- `snapshots/docs/`
- `snapshots/impact/`
- `snapshots/payments_cashiering/pay_tndr_cashier/`

This keeps snapshot DDL, refresh procedures, scheduler jobs, validation SQL, subset-level READMEs, and colocated Domain XML copies together without mixing them with broader validation or diagnostic folders.

For the current 6-hour staggered cadence across the active governed snapshot jobs, use:
- `sql/performance/snapshots/apply_6hour_staggered_schedule_1am_base.sql`

For governed snapshot-table indexes that are active or planned, use:
- `sql/performance/snapshots/indexes/`

For centralized deployment sequencing across the active 7 scheduled snapshots, use:
- `sql/performance/snapshots/deployment_steps/`

For active governed snapshots, each snapshot workspace now also carries its matching end-user Domain XML so a developer can review:
- the Oracle snapshot build assets
- the QA and results template
- the exact Jaspersoft Domain artifact

The importable bundle for server deployment still lives under:
- `domains/exports/manual_imports/`

For the end-to-end process of reviewing an older manual Domain, designing a snapshot, validating it, publishing a new Domain XML, and repointing reports, use:
- `sql/performance/snapshots/docs/legacy_domain_to_snapshot_modernization_playbook.md`
- `sql/performance/snapshots/docs/snapshot_modernization_checklist.md`

For the centralized snapshot documentation index, use:
- `sql/performance/snapshots/docs/README.md`
