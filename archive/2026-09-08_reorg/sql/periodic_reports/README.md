# Utility Periodic Report SQL Packs

Governed, **non-parameterized** SQL reports for municipal utilities on calendar **annual**, **quarterly**, and **semi-annual** cycles.

Periods use rolling `TRUNC` windows — no file edits between runs. See [lib/calendar_windows.sql](lib/calendar_windows.sql).

## Quick start

```bash
# Prerequisite check (snapshot date coverage)
python3 scripts/local/run_client_oracle_sql.py --client odessa_dev \
  --file sql/periodic_reports/validation/00_prerequisite_snapshot_coverage.sql

# All reports
python3 scripts/local/run_periodic_reports.py --client odessa_dev --all

# One frequency
python3 scripts/local/run_periodic_reports.py --client odessa_dev --frequency annual

# Single report
python3 scripts/local/run_periodic_reports.py --client odessa_dev --report A1

# Save full log
python3 scripts/local/run_periodic_reports.py --client odessa_dev --all \
  --report-file /tmp/periodic_reports.txt
```

## Prerequisites

1. **VPN** for SmartCity client databases (e.g. Odessa DEV).
2. **Governed snapshots** deployed and refreshed. Annual reports may need `02a_full_history_refresh_procedure.sql` when the rolling window is shorter than the report period — see validation script output.
3. **Snapshot minimum windows** (operational refresh):
   - `FT_RPT_CURR`, `BSEG_*`, `D1_USAGE_*`: 12 months
   - `FT_GL_DISTRIBUTION_RPT_CURR`: 6 months — annual GL report (A4) queries `CI_FT`/`CI_FT_GL` directly

## Layout

```
periodic_reports/
  MANIFEST.md           # report catalog
  runner_manifest.json  # ordered report list for runner
  lib/                  # calendar windows + governance reference
  annual/ quarterly/ semi_annual/
  validation/           # prerequisite + smoke tests
```

## Related docs

- [MANIFEST.md](MANIFEST.md) — full report catalog
- [workstream_snapshot_catalog.md](../performance/snapshots/docs/workstream_snapshot_catalog.md)
- [conversion_validation FINDINGS.md](../odessa_dev/conversion_validation/FINDINGS.md) — Odessa data gaps
- [VALIDATION_NOTES.md](validation/VALIDATION_NOTES.md) — client run results
