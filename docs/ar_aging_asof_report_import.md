# AR Aging As-Of Reports (SCS-2322)

SQL JRXML reports for fiscal year-end AR aging with a selectable cutoff date.

## Files to import

| Report | JRXML | Purpose |
|---|---|---|
| AR Aging by Dist Code | [`reports/ar_aging_by_dist_code_asof.jrxml`](../reports/ar_aging_by_dist_code_asof.jrxml) | SA Current + FIFO buckets by Distribution Code as of `AS_OF_DT` (`ARS_DT`) |
| AR GL Control Bridge | [`reports/ar_gl_control_bridge_asof.jrxml`](../reports/ar_gl_control_bridge_asof.jrxml) | FT_GL open balances for 142000/050/060 (and optional 235000) as of `ACCOUNTING_DT` |

Input controls:

- `server/input_controls/ar_aging_by_dist_code_asof_input_controls.json`
- `server/input_controls/ar_gl_control_bridge_asof_input_controls.json`

## Import steps (Jaspersoft Studio / Server)

1. Create a Report Unit under your org (e.g. CityCorp / Debt Management).
2. Upload the JRXML as the main report.
3. Set **Data Source** on the Report Unit to **`ORIGIN_DEV_DS`** (JDBC) — not a Domain. Do not use CityCorp_DS until you are ready for that tenant.
4. Add input controls matching parameter IDs exactly:
   - Aging: `AS_OF_DT` (Date/Time), `CLIENT_NAME`, `INCLUDE_ZERO_BAL`
   - Bridge: `AS_OF_DT` (Date/Time), `CLIENT_NAME`, `INCLUDE_DEPOSITS`
5. Default `AS_OF_DT` in JRXML is `2026-06-30`.
6. **Smoke first:** import [`reports/ar_aging_dist_code_smoke.jrxml`](../reports/ar_aging_dist_code_smoke.jrxml) with `ORIGIN_DEV_DS`. If that fails with 6632, the Report Unit datasource is wrong or the JDBC user cannot reach the DB.
7. Full aging report can take several minutes (FIFO over `CI_FT`); 6632 after a long wait is often a **query timeout**, not a bad JRXML.

## Logic notes

**Aging report**

- Population: frozen ARS FTs (`FREEZE_SW=Y`, `NOT_IN_ARS_SW=N`) with `ARS_DT <= AS_OF_DT`
- Includes payments/credits (same as updated `CMS_SA_SNAPSHOT`)
- FIFO aging as of `AS_OF_DT`; excess credit in 0–30
- Dist Code from `CI_SA_TYPE.DST_ID`
- `GL_CONTROL_SECTION` maps DST → TB account family for auditor review

**Bridge report**

- Does **not** produce aging buckets
- Sums `CI_FT_GL.AMOUNT` where `TOT_AMT_SW=Y` and `ACCOUNTING_DT <= AS_OF_DT`
- Use to compare CIS GL open AR to Microsoft BC Trial Balance

## Performance

First run on a large client DB may take several minutes (full `CI_FT` scan + FIFO). Prefer Test/QA for smoke; schedule overnight if needed on Prod.
