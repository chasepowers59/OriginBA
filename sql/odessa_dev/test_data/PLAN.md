# Odessa DEV test data — execution plan (no loads yet)

Validated against pdevdb on VPN (read-only). **Nothing has been inserted.**

## Approach

1. **Discover** — `00_discover_valid_codes.sql` (re-run after C2M config changes).
2. **Preflight** — `01_pack_manifest.sql` (ODEV collisions = 0, golden template exists).
3. **Load by clone** — `INSERT … SELECT` from golden template; swap only `ODEV-*` keys + shifted dates.
4. **Validate** — row counts + snapshot refresh for affected workstreams.
5. **Rollback** — `99_rollback_odev.sql` (delete children → parents, `ODEV-%` only).

Hand-built `INSERT` lists (original draft) will fail: `CI_PER` alone has **29 NOT NULL columns**; `CI_PREM` has **33**.

## Why the original draft would fail

| Issue | Fix |
|-------|-----|
| `MONTHLY` bill cycle | Use `83` (or other `CI_BILL_CYC` code) |
| `COMPLETE` statuses | `BILL_STAT_FLG = 'C '`, `BSEG_STAT_FLG = '50'`, `SA_STATUS_FLG = '20'` |
| `RES` SA type | `W-RES` |
| `OD` division | `DIV1` |
| `PRI` name type | Use template value (`PRIM` or as stored) |
| Missing `ACCT_REL_TYPE_CD` | `MAIN` |
| No `CI_PREM` / `CI_SP` | Required for billing chain |
| No calc / SQ | Required for billed-usage snapshots |
| Blank `CI_BILL.BILL_CYC_CD` | Copy from `CI_ACCT` (Odessa conversion gap — don’t repeat) |

## Pack B01 — Billing water (first pack)

**Goal:** One completed water bill visible in `BSEG_SQ_USAGE_RPT_CURR` / `BSEG_BILLED_USAGE_RPT_CURR` after snapshot refresh.

### Tables to clone (in load order)

| Step | Table | Template source | New key |
|------|-------|-----------------|---------|
| 1 | `CI_PER` | `9184027141` | `ODEV-B01-PER-0001` |
| 2 | `CI_PER_NAME` | same person | name → `ODEV TEST B01 CUSTOMER 0001` |
| 3 | `CI_PREM` | `4237790275` | `ODEV-B01-PREM-0001` |
| 4 | `CI_ACCT` | `1110100087` | `ODEV-B01-ACCT-0001` |
| 5 | `CI_ACCT_PER` | same account | remap `ACCT_ID`, `PER_ID` |
| 6 | `CI_SA` | `7790352119` | `ODEV-B01-SA-0001` |
| 7 | `CI_SA_CHAR` | if present on template | remap `SA_ID` |
| 8 | `CI_SP` | `8740115078` | `ODEV-B01-SP-0001` |
| 9 | `CI_SA_SP` | same SA/SP link | remap keys |
| 10 | `CI_BILL` | `856601546942` | `ODEV-B01-BILL-00000001` |
| 11 | `CI_BSEG` | `776805100203` only (W-RES) | `ODEV-B01-BSEG-00000001` |
| 12 | `CI_BSEG_CALC` | same bseg | remap `BSEG_ID` |
| 13 | `CI_BSEG_SQ` | same bseg | remap `BSEG_ID` |
| 14 | `CI_FT` (optional) | 4 rows on template bill | `ODEV-B01-FT-00000001`… |

**Skip on v1:** STORM / SW-RES segments on same bill (no SQ); sewer/storm separate packs if needed.

### Date shifting

Use `TRUNC(SYSDATE)` offsets from template:

- Bill window: ~30 days ending yesterday.
- `CI_BILL.BILL_DT` = yesterday, `DUE_DT` = +21 days.
- Set `CRE_DTTM` / `COMPLETE_DTTM` on bill to match.

### Post-load

```sql
-- After insert + commit
EXEC cisadm.refresh_bseg_sq_usage_rpt_curr;
EXEC cisadm.refresh_bseg_billed_usage_rpt_curr;
```

## Pack B02 — Billing errors (second)

Clone B01 chain or add second bill on same account:

- `CI_BILL.BILL_STAT_FLG = 'P'`
- `CI_BSEG.BSEG_STAT_FLG = '20'`
- `CI_BSEG_EXCP` with `BSEG_EXCP_FLG = '10'` (matches current Odessa error pattern)

IDs: `ODEV-B02-*` or second bill `ODEV-B01-BILL-00000002`.

## Pack W01 — Workflow / to-do (third)

- `CI_TD_ENTRY` with real `TD_TYPE_CD` (e.g. `D1-ATVTD` or `W1-SYRQO`).
- Set `ASSIGNED_TO` to valid `SC_USER.USER_ID` so assignee reports work.
- Use `ENTRY_STATUS_FLG` in `O`, `W`, `C` mix for aging reports.

## Pack V01 — VEE (fourth, hardest)

`D1_VEE_EXCP` has 15 NOT NULL columns and ties to measurement usage — clone from existing exception row rather than hand-build.

## Pack M01 — Meter install event “Off” (meter ops)

Odessa uses **D1** (not `CI_MTR` — that table is empty). A meter at a service point is:

```
CI_SP  →  D1_SP  →  D1_DVC  →  D1_DVC_CFG  →  D1_INSTALL_EVT
```

### What “Off” means in reporting

On the **Device** domain, install event status is:

- **Column:** `D1_INSTALL_EVT.BO_STATUS_CD`
- **Label:** `F1_BUS_OBJ_STATUS_L.DESCR` where `BUS_OBJ_CD = 'D1-InstallEvent'`

That is the field that shows as **Status (Install Event)** in Meter Operations reports — “Off” is a **status description**, not a free-text value.

Separately, **currently installed** logic (device snapshot) uses **dates**, not only status:

```sql
(d1_install_dttm IS NULL OR d1_install_dttm <= SYSTIMESTAMP)
AND (d1_removal_dttm IS NULL OR d1_removal_dttm > SYSTIMESTAMP)
```

So for a row to behave as **not installed** in snapshots you may need **both**:

1. `BO_STATUS_CD` = the code whose label is **Off** (discover on pdevdb)
2. `D1_REMOVAL_DTTM` set (e.g. `SYSDATE`) if you want it out of “current install” joins

`ARM_STAT_FLG` is **arming status** (different lookup) — usually not what “Off” means on install event.

### How to set it in the test script (when we load)

After cloning a golden `D1_INSTALL_EVT` row:

```sql
-- Use real code from discovery (example placeholder only):
UPDATE cisadm.d1_install_evt
SET    bo_status_cd     = :install_off_bo_status_cd,  -- from F1_BUS_OBJ_STATUS_L where descr = 'Off'
       d1_removal_dttm  = SYSDATE,                    -- if simulating removal / not current
       status_upd_dttm  = SYSDATE,
       version          = version + 1
WHERE  install_evt_id   = 'ODEV-M01-INST-00000001';
```

Better: set those columns in the `INSERT … SELECT` clone step so no separate UPDATE is needed:

```sql
INSERT INTO cisadm.d1_install_evt (...)
SELECT 'ODEV-M01-INST-00000001',
       d1_sp_id,
       device_config_id,
       d1_install_dttm,
       SYSDATE,              -- removal_dttm → Off / not current
       installation_const,
       bus_obj_cd,
       :install_off_bo_status_cd,
       ...
FROM   cisadm.d1_install_evt
WHERE  install_evt_id = :template_install_evt_id;
```

### Discovery before load (VPN on)

```sql
SELECT bo_status_cd, descr
FROM   cisadm.f1_bus_obj_status_l
WHERE  bus_obj_cd = 'D1-InstallEvent' AND language_cd = 'ENG';

SELECT ie.bo_status_cd, st.descr, COUNT(*)
FROM   cisadm.d1_install_evt ie
LEFT JOIN cisadm.f1_bus_obj_status_l st
       ON st.bus_obj_cd = 'D1-InstallEvent'
      AND st.bo_status_cd = ie.bo_status_cd
      AND st.language_cd = 'ENG'
GROUP  BY ie.bo_status_cd, st.descr
ORDER  BY COUNT(*) DESC;
```

Also in `00_discover_valid_codes.sql` sections 11–12.

### M01 tables (load order, all `ODEV-M01-*` keys)

1. `D1_DVC` (device)
2. `D1_DVC_CFG` (effective config)
3. `D1_MEASR_COMP` (optional, for measurement reads)
4. `D1_INSTALL_EVT` (install event — **set Off status here**)
5. Link `D1_SP_ID` to `ODEV-M01-SP-0001` (bridge from `CI_SP` / billing pack if shared)

Rollback: extend `99_rollback_odev.sql` with `D1_INSTALL_EVT`, `D1_DVC_CFG`, `D1_DVC` deletes where `install_evt_id` / device ids like `ODEV-M01-%`.

## Insert + validate pattern (all packs)

Each pack load script should follow the same three-phase shape as `10_pack_b01_billing_clone.sql`:

| Phase | What | How it fails |
|-------|------|----------------|
| **Preflight** | ODEV collisions, template exists | SELECT returns failure rows → use `--fail-if-any-rows` |
| **Load** | `INSERT … SELECT` clone via `lib/clone_declare_helpers.sql` | `RAISE_APPLICATION_ERROR(-20001, …)` rolls back |
| **Post-load** | Chain integrity + business rules | SELECT returns failure rows → `--fail-if-any-rows` |

Shared helpers live under `lib/`:

- `clone_declare_helpers.sql` — `insert_clone`, `assert_count_eq`, `assert_count_ge`
- `validate_b01_post_load.sql` — B01-specific SELECT gate (included via `@@`)

## Next file to author

`20_pack_m01_meter_install_off.sql` — same three-phase pattern for D1 install event Off status.

**Run B01 only after manifest preflight passes and VPN is up.**
