# Periodic Reports — Validation Notes

Last updated: **2026-07-05**

## Running validation (VPN required)

```bash
# Prerequisites + smoke
python3 scripts/local/run_periodic_reports.py --client odessa_dev --validate \
  --report-file /tmp/periodic_validate_odessa.txt

# Full pack
python3 scripts/local/run_periodic_reports.py --client odessa_dev --all \
  --report-file /tmp/periodic_all_odessa.txt

# Reference client
python3 scripts/local/run_periodic_reports.py --client citycorp --all \
  --report-file /tmp/periodic_all_citycorp.txt
```

**2026-07-05:** Live runs blocked without VPN (`ORA-12170` TCP timeout to SmartCity hosts). Re-run when VPN is connected.

## Required snapshots

| Snapshot | Reports using it |
|----------|------------------|
| `BSEG_SQ_USAGE_RPT_CURR` | A1, Q1, S1 |
| `BSEG_BILLED_USAGE_RPT_CURR` | A2, S2 |
| `FT_RPT_CURR` | A3, A5, A8, Q3, Q5, S3–S5 |
| `FT_GL_DISTRIBUTION_RPT_CURR` | Q4 |
| `PAY_TNDR_CASH_RPT_CURR` | A6 |
| `WORKFLOW_QUEUE_RPT_CURR` | A7, Q6 |
| `D1_USAGE_RPT_CURR` | Q7 |
| `FIELD_ACTIVITY_RPT_CURR` | S6 (optional — fails if not deployed) |

**Annual GL (A4)** queries `CI_FT` + `CI_FT_GL` directly because the GL snapshot rolling window is 6 months.

## Prerequisite warnings

`validation/00_prerequisite_snapshot_coverage.sql` emits `WARN` when `MAX(date)` on a snapshot is earlier than the annual window start. Mitigation:

1. Run `02a_full_history_refresh_procedure.sql` for affected snapshots before annual packs, or
2. Accept partial annual results from the rolling window only.

## Odessa DEV caveats

From [conversion_validation FINDINGS.md](../odessa_dev/conversion_validation/FINDINGS.md):

| Report area | Expected Odessa behavior |
|-------------|------------------------|
| A1/Q1/S1 consumption | Runs; water SQ may show DAYS/GAL/1 pattern |
| A2/S2 revenue | Runs; some bsegs lack SQ child rows |
| Q8 bseg without SQ | **High failure count** (~7,681 frozen water bsegs) |
| Q7 usage volume | Very low row count (5 C1-bridged usages vs 596K on CityCorp) |
| A7/Q6 workflow | High open-todo volume; assignee mostly blank |
| S6 field activity | Only ~60 activities converted |

## CityCorp reference expectations

| Metric | Typical signal |
|--------|----------------|
| Consumption by UOM | Non-zero water/electric rows |
| Payments by tender | Multiple tender types |
| Usage Q7 | Large `D1_USAGE` counts |
| Q8 bseg without SQ | ~55 exceptions (vs thousands on Odessa) |

## Report-specific notes

- **A8 executive scorecard:** Union of scalar KPIs; useful as a one-page leadership export.
- **S5 arrears movement:** Uses frozen FT on active SAs with positive `CUR_AMT` sum; not a full collections aging report.
- **Q6 open aging:** Filters todos **created** in the prior quarter that are still open — not all open backlog.

## Next steps when VPN is available

1. Run `--validate` on Odessa and CityCorp; paste snapshot min/max dates into this file.
2. Run `--all` on both clients; note any ORA errors (missing snapshot tables).
3. If `FIELD_ACTIVITY_RPT_CURR` missing, skip S6 or deploy consolidation snapshot first.
