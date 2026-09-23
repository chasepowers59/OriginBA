# Standard Offering Write Offs domain: payment window, account balance, running arrears

Target: `/SmartCity/Report/Standard_Offering/Debt_Management/Write_Off_Process_1/Write_Offs___Domain`
(label "Write Offs - Domain"; one row per write-off process from `CISADM.C1_BI_WOPROC_VW`).
Bound views in every client org: Detailed Write Off Process, Average Process Duration, Debt
Written Off Trend; Origin_DEV adds Active Processes - Initiated Debt and Trend in Effectiveness.

Built offline on 2026-09-23 (VPN down) from the Origin_DEV export taken the same day
(`schema.reference.xml`). Rebuild with:

```bash
python3 scripts/jaspersoft/patch_write_offs_domain.py \
    domains/manual_imports/write_offs_domain/schema.reference.xml \
    domains/manual_imports/write_offs_domain/schema.patched.xml
python3 -m pytest tests/test_write_offs_domain_patch.py -q
```

## What changes (the patch's docstring has the reasoning)

| | Before | After |
| --- | --- | --- |
| `WO_PAY_AGG` window | `cre_dttm >= 2025-09-01` and `pay_dt >= 2025-09-01`, hard-coded | payments dated on or after each process's own create date; "in window" still stops at completion |
| `WO_PAY_AGG` chain | `ci_pay_tndr.pay_tender_id = ci_pay_seg.pay_id` (two id spaces; events never matched) | segment -> `CI_PAY` (pay_id, frozen `PAY_STATUS_FLG='50'`) -> `CI_PAY_EVENT` (pay_event_id) |
| `WO_ACCT_BAL` | | new: account current and payoff balance, the snapshot's CUR_BAL rule (`FREEZE_SW='Y'`, `NOT_IN_ARS_SW='N'`, `ARS_DT` set and not after today): 752 of 752 write-off accounts equal to the cent against the client's CMS_ACCT_SNAPSHOT; 13 of 752 without the arrears-date condition, accounts with a write-off process only |
| `WO_PROC_ARS` | | new: sum of `CI_WO_PROC_SA.ARS_AMT` per process |
| `RUNNING_ARS_ROW` | | new calculated field: process arrears minus frozen payments since start |
| items | 60 | 66: four `(Row)` items in Debt And Recovery, two Sum measures in Measures |

Every pre-existing item id, resourceId, join and table ref is unchanged (test
`test_nothing_a_view_binds_to_moved`), so the bound views keep working.

Deliberately NOT carried from FDL's domain: `REDUNDANT_SW='Y'` (selects transactions already
netted to zero -- the opposite of a balance), `CI_PAY.ILM_DT` as a payment date (it is the
information-lifecycle date), and the payment-arrangement adjustment keyed on `SA_TYPE_CD='PA'`
(a client-configured code).

## Applied and proven, 2026-09-23 (test Origin_DEV and test Fond_Du_Lac)

| Proof | Origin_DEV (Ellensburg DB) | Fond_Du_Lac test |
| --- | --- | --- |
| schema read back == patch output | byte-equal | byte-equal |
| bound views open (topic kinds) and execute | 4 of 4 | 4 of 4 open; 3 rows, 1 empty (empty since the 18 Sep sweep, before this change) |
| six new items in the Ad Hoc metadata | yes | yes |
| running arrears == arrears - payments since start | 822 of 822 | 787 of 787 |
| processes showing payments, before -> after | 0 -> 364 | (not sampled before) 274 |
| Write Off Arrears Amount vs FDL's own report, same process ids | | 787 of 787 equal |
| Account Current Balance vs the client's CMS_ACCT_SNAPSHOT | 633 of 633 to the cent | 752 of 752 to the cent |
| Process Start DTTM vs FDL's Create Date/Time | | 787 of 787 equal (same timestamp) |

For scale: FDL's own report's Current Balance ties to the same snapshot on 23 of 903 accounts.
The rollback for each org is its `*_before.zip` under `backups/jaspersoft/write_offs/`.

**Open, not changed:** the join tree carries its own filter, `C1_BI_WOPROC_VW.CRE_DTTM >=
ts'2025-09-01'`, a third hard-coded floor. It applies to every view on the domain: at FDL it hides
777 of the 1,564 processes (all of 2023 and 2024). Removing it widens what every bound view shows,
so it is a product decision, not part of this patch.

## Apply to another org (one at a time; prod needs --i-mean-prod)

1. Export the live domain fresh and patch THAT (the reference here is a same-day copy, but the
   patch is anchored, so it refuses a schema whose shape moved):
   ```bash
   scripts/jaspersoft/jrs.sh jrs_repository.py --env test --org Origin_DEV export \
       /SmartCity/Report/Standard_Offering/Debt_Management/Write_Off_Process_1/Write_Offs___Domain --out /tmp/wo.zip
   unzip -p /tmp/wo.zip '*Write_Offs___Domain_files/schema.data' > /tmp/wo.reference.xml
   python3 scripts/jaspersoft/patch_write_offs_domain.py /tmp/wo.reference.xml /tmp/wo.patched.xml
   ```
2. Apply in place on Origin_DEV (item ids unchanged, so bound views survive; `/tmp/wo.zip` is the rollback):
   ```bash
   scripts/jaspersoft/jrs.sh jrs_debug.py --env test --org Origin_DEV --confirm Origin_DEV domain-apply \
       /SmartCity/Report/Standard_Offering/Debt_Management/Write_Off_Process_1/Write_Offs___Domain --schema /tmp/wo.patched.xml
   ```
3. Prove, in this order:
   - `jrs_check_topic_kinds.py --env test --org Origin_DEV --folder .../Write_Off_Process_1` and
     `jrs_run_sweep.py` on the folder: the seven bound views still open and execute.
   - `/rest_v2/domains/<uri>/metadata` lists the six new items.
   - A flat query of the new items for a handful of processes, compared with the FDL report's
     "Write Off Arrears Amount", "Current Balance", "Payoff Balance" and "Running Arrears Amount"
     for the same process ids (FDL prod, `/SmartCity/Report/FDL_Active_Write_Off_Process`).
     Arrears amount must match exactly; balances will differ where FDL's `REDUNDANT_SW='Y'`
     filter bites, and that difference is the point; running arrears differs by FDL's
     payment-arrangement term and by the payment-date field.
   - Before/after on `WO_PAY_AGG`: processes older than 2025-09-01 now carry payment figures;
     `payment_event_count` is no longer zero everywhere.
4. Then the client orgs, one at a time, same command with `--org <Org>` (`--i-mean-prod` on prod),
   each preceded by its own export.

Measure `WO_ACCT_BAL` on a large client before prod: it aggregates CI_FT for every account that
ever had a write-off process. If it is slow, the fix is a materialised snapshot, not a smaller
regime.
