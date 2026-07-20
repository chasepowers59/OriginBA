# Conversion validation manifest

Gate SQL lives under `gates/<workstream>/`.  
**Plain-language overview:** [WORKSTREAMS.md](WORKSTREAMS.md)

Run:
```bash
python3 scripts/local/run_conversion_validation.py --client odessa_dev
python3 scripts/local/run_conversion_validation.py --client odessa_dev --workstream billing
```

| Severity | Meaning |
|----------|---------|
| **FAIL** | Likely conversion bug or report blocker |
| **WARN** | Investigate — may be client-specific legacy |

---

## Gate index by workstream

### Billing (`gates/billing/`)

| Gate | Severity | C2M rule | Report impact |
|------|----------|----------|---------------|
| `bill_cycle_on_bill_header` | FAIL | `CI_ACCT.BILL_CYC_CD` set → `CI_BILL.BILL_CYC_CD` should be set | Blank cycle on bills-in-error |
| `bseg_sq_days_gal_pattern` | WARN | Water SQ pattern audit (Odessa DAYS/GAL/1) | Billed usage qty semantics |
| `bseg_frozen_without_sq` | FAIL | Frozen water `CI_BSEG` should have `CI_BSEG_SQ` | BSEG SQ usage empty |
| `ft_bill_sa_linkage` | WARN | Complete frozen bseg often has `CI_FT` on bill+SA | FT / AR reports |

### Workflow (`gates/workflow/`)

| Gate | Severity | C2M rule | Report impact |
|------|----------|----------|---------------|
| `todo_assignee_population` | WARN | Open todos should have `ASSIGNED_TO` | Assignee filters drop all rows |
| `todo_open_fk_account_resolution` | WARN | Open todos should FK to `CI_ACCT` via `CI_TD_DRLKEY` | Account context missing |

### Meter ops (`gates/meter_ops/`)

| Gate | Severity | C2M rule | Report impact |
|------|----------|----------|---------------|
| `install_event_off_alignment` | FAIL | Latest `D1OF` + no removal → status `OFF` | "Off" install filter empty |
| `install_event_off_population` | WARN | Converted DB should have some `OFF` rows (ref clients do) | Odessa conversion gap |
| `measurement_without_measr_comp` | WARN | `D1_MSRMT` → `D1_MEASR_COMP` integrity | Measurement reports |

### Devices (`gates/devices/`)

| Gate | Severity | C2M rule | Report impact |
|------|----------|----------|---------------|
| `d1_sp_identifier_coverage` | FAIL | Active ON installs need `D1_SP_IDENTIFIER` D1EI | `CMS_DVC_ACCT` empty |
| `device_domain_premise_bridge` | FAIL | Device → D1EI → `CI_SP` → `CI_PREM` | Premise/address filters |

### Field ops (`gates/field_ops/`)

| Gate | Severity | C2M rule | Report impact |
|------|----------|----------|---------------|
| `field_activity_sp_linkage` | FAIL | D1FA activity → `D1_ACTIVITY_REL_OBJ` D1-SP | Field activity list empty |
| `field_activity_premise_bridge` | FAIL | Activity SP → D1EI → `CI_PREM` | No address on field reports |

### VEE (`gates/vee/`)

| Gate | Severity | C2M rule | Report impact |
|------|----------|----------|---------------|
| `vee_imd_measr_comp_link` | WARN | `D1_VEE_EXCP` → IMD → `D1_MEASR_COMP` | VEE context incomplete |

### Usage (`gates/usage/`)

| Gate | Severity | C2M rule | Report impact |
|------|----------|----------|---------------|
| `usage_c1_bridge_rate` | WARN | `D1_USAGE` should bridge `C1_USAGE` BD-PROC | No billing/account on usage |
| `usage_sa_bseg_mismatch` | FAIL | `C1_USAGE.SA_ID` = `CI_BSEG.SA_ID` | Usage/billing reconciliation |

---

## Discovery profiles (`discovery/`)

| File | Workstreams covered |
|------|---------------------|
| `01_install_event_profile` | meter_ops |
| `02_billing_device_bridge_profile` | billing, devices |
| `03_billing_profile` | billing |
| `04_workflow_profile` | workflow |
| `05_field_ops_usage_vee_profile` | field_ops, vee, usage |

---

## Cross-cutting gap (highest priority)

**D1 SP → CIS SP bridge** (`D1_SP_IDENTIFIER`, `SP_ID_TYPE_FLG = 'D1EI'`) affects devices, field activity, and Jaspersoft device domains.  
12-char `D1_SP_ID` ≠ 10-char `CI_SP.SP_ID` on converted clients.

---

## Adding a gate

1. Add section to `WORKSTREAMS.md` if new process area.
2. Add `discovery/NN_<topic>_profile.sql` (metrics, always returns rows).
3. Add `gates/<workstream>/<name>.sql` (failure rows only).
4. Register WARN stems in `scripts/local/run_conversion_validation.py` if needed.
5. Document in this manifest.
6. For FAIL gates with large populations, use **summary SELECT + sample SELECT** (runner uses `--fail-last-select-only`).
