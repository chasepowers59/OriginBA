# Odessa DEV conversion validation findings

Last run: **2026-07-02** (VPN → `pdevdb_odessa`)

## Summary

| Result | Count |
|--------|------:|
| PASS | 7 |
| WARN | 6 |
| FAIL | 3 |

Re-run:
```bash
python3 scripts/local/run_conversion_validation.py --client odessa_dev --gates-only \
  --report-file /tmp/odessa_validation_$(date +%Y%m%d).txt
```

## FAIL gates (conversion / report blockers)

### `billing/05_bill_cycle_on_bill_header` — **1,782,261** rows

Account has `BILL_CYC_CD` but `CI_BILL.BILL_CYC_CD` is blank on ~99.9% of bills where the account cycle is set.

- **Report impact:** cycle-based billing filters, bills-in-error, cycle distribution reports.
- **Test data:** B01 pack stamps cycle `83` on cloned bills — correct pattern for synthetic rows.
- **CityCorp reference:** 620,897 / 935,184 (~66%) also blank — not Odessa-only, but Odessa is worse.

### `billing/bseg_frozen_without_sq` — **7,681** rows

Frozen/complete water `CI_BSEG` rows with no `CI_BSEG_SQ` child.

- **Report impact:** BSEG SQ usage, billed quantity detail.
- **CityCorp reference:** 55 / 2,846,383 (~0.002%) — Odessa-specific gap at scale.

### `field_ops/field_activity_premise_bridge` — **25** rows (all D1FA activities)

All 60 converted field activities fail the D1EI → `CI_SP` → `CI_PREM` bridge (25 unique activities in gate; some may have multiple SP rel objects).

- **Report impact:** field activity reports filtered by premise/address.
- **Note:** Small population — may be incomplete conversion of field ops, not a systemic bridge failure.

## WARN gates (investigate; may be client-specific)

| Gate | Odessa signal | CityCorp reference |
|------|---------------|-------------------|
| `06_bseg_sq_days_gal_pattern` | 100% water SQ = DAYS/GAL/bill_sq=1 | 0% |
| `02_install_event_off_population` | 0 converted OFF (2 ODEV test rows only) | 551 OFF |
| `07_todo_assignee_population` | ~99.99% open todos unassigned | ~99.9% unassigned |
| `todo_open_fk_account_resolution` | Open IMD/activity todos lack account FK | Similar pattern |
| `measurement_without_measr_comp` | Some `D1_MSRMT` without comp link | TBD |
| `vee_imd_measr_comp_link` | VEE exception → measr comp gaps | TBD |

## PASS gates (healthy on Odessa)

- `devices/03_d1_sp_identifier_coverage` — 44,845/44,848 ON installs have D1EI (3 ODEV test gaps).
- `devices/04_device_domain_premise_bridge` — device domain reaches premise when D1EI present.
- `meter_ops/01_install_event_off_alignment` — no misaligned OFF/Removed rows in converted data.
- `field_ops/field_activity_sp_linkage` — D1FA activities have D1-SP rel objects.
- `billing/ft_bill_sa_linkage`, `usage/usage_c1_bridge_rate`, `usage/usage_sa_bseg_mismatch`.

## Discovery compare (Odessa vs CityCorp)

| Metric | Odessa | CityCorp |
|--------|-------:|---------:|
| Install OFF count | 2 | 551 |
| Bill header blank | 1,782,261 | 620,897 |
| D1EI missing (ON installs) | 3 | 0 |
| Water SQ DAYS/GAL/1 | 1,694,918 | 0 |
| Frozen water bseg w/o SQ | 7,681 | 55 |
| Open todos blank assignee | 64,535 | 24,916 |
| D1FA activities | 60 | 13,679 |
| D1_USAGE w/ C1 BD-PROC | 5 | 596,774 |

## Recommended next steps

1. **Conversion team:** stamp `CI_BILL.BILL_CYC_CD` from `CI_ACCT` during load; investigate 7,681 missing `CI_BSEG_SQ`.
2. **Meter OFF modeling:** populate `OFF` status (not `REMOVE` + removal date) for meters temporarily off SP.
3. **Test data M01:** add `D1_SP_IDENTIFIER` D1EI rows; model OFF without `D1_REMOVAL_DTTM`.
4. **Field ops:** validate whether 60 activities are expected or incomplete conversion slice.

## Script improvements (this session)

- Gates emit **summary count + 25-row sample** (`--fail-last-select-only` on runner).
- Validation runner supports `--gates-only`, `--report-file`, `--quiet`, discovery compare table.
- See [README.md](README.md) for commands.
