# CMS_SA_SNAPSHOT (legacy SA arrears snapshot)

## Why this exists

Standard Offering Debt Management domain `SA Snapshot - Aged Balance` expects:

- physical table: `CISADM.CMS_SA_SNAPSHOT`
- domain derived query: `CMS_ACCT_SNAPSHOT` (SQL over `cms_sa_snapshot`, not a physical table)

CityCorp had `CMS_SA_SNAPSHOT` only under `CISADM290`, and `CISREAD.CMS_SA_SNAPSHOT` synonym was invalid because it pointed at missing `CISADM.CMS_SA_SNAPSHOT`.

## Domain warning context

Domain Designer deletes / breaks when it cannot resolve:

- table `CMS_SA_SNAPSHOT`
- derived table `CMS_ACCT_SNAPSHOT`
- calculated fields depending on them (`ACCT_ID_DISTINCT`, `PER_ID_DISTINCT`)
- join trees `JoinTree_1` / `JoinTree_2`

## Scripts

1. `01_create_cms_sa_snapshot_table.sql` — create `CISADM.CMS_SA_SNAPSHOT`, indexes, grants, synonym
2. `02_refresh_cms_sa_snapshot_procedure.sql` — create `CISADM.REFRESH_CMS_SA_SNAPSHOT`
3. `03_run_and_validate.sql` — run refresh + basic validation queries
4. `04_validate_cms_sa_snapshot.sql` — bucket identity, FT parity, CISREAD smoke (no refresh)
5. `05_schedule_cms_sa_snapshot_job.sql` — recurring 6-hour scheduler job

Centralized rollout wrappers: [deployment_steps/00_domain_support_deployment_manifest.md](../../deployment_steps/00_domain_support_deployment_manifest.md)

## CityCorp deploy

```bash
python3 scripts/local/run_client_oracle_sql.py --client citycorp \
  --file sql/performance/snapshots/debt_mgmt/cms_sa_snapshot/01_create_cms_sa_snapshot_table.sql

python3 scripts/local/run_client_oracle_sql.py --client citycorp \
  --file sql/performance/snapshots/debt_mgmt/cms_sa_snapshot/02_refresh_cms_sa_snapshot_procedure.sql

python3 scripts/local/run_client_oracle_sql.py --client citycorp \
  --file sql/performance/snapshots/debt_mgmt/cms_sa_snapshot/03_run_and_validate.sql
```

## Notes

- Snapshot type used for current-state load: `LDAY`
- Balance rule: frozen ARS FTs **including payments/credits**, with **`ARS_DT <= today` only** so `CUR_BAL` / `TOT_BAL` match CIS SA **Current** (excludes CIS "Future" / not-yet-due)
- Aging rule: **FIFO** on that due/past population — positive amounts aged by bill `ARS_DT`; negatives reduce oldest open debt first; excess credit sits in `ARS_AMT1`
- `ARS_AMT1 + … + ARS_AMT5 = CUR_BAL` for every SA
- Aging buckets align to the domain labels:
  - `ARS_AMT1` 0–30 days past due (not Future)
  - `ARS_AMT2` 31–60
  - `ARS_AMT3` 61–90
  - `ARS_AMT4` 91–120
  - `ARS_AMT5` 121+
- CIS "Future" (ARS_DT after today) is intentionally excluded from this snapshot; report it separately if needed
- Longer-term replacement object is `SA_AGED_BAL_RPT_CURR`; this CMS table keeps existing SO domains working.
- Recurring schedule: `JOB_REFRESH_CMS_SA_SNAPSHOT`, every 6 hours at 04:30, 10:30, 16:30, and 22:30 GMT.
