# Production JasperReports Server 10.0 upgrade: review of 2026-09-21

Server: `smartcity-jrs.originsmartops.com`, 10.0.0 PRO build 20260514_1415, Commercial license to
2029-01-09 (from `/rest_v2/serverInfo` at 04:10). Theme "New Theme Name" active on all five orgs,
its 240 files byte-identical to the test root `NewestOriginBATheme`.

## What the upgrade broke, and the fix

Ad Hoc views promoted to the 9.0 server through `strip_jrs8_incompatible_jrxml_uuid.py` carried a
topic JRXML with no namespace, no uuid, no nestedType and `<queryString>`. 10.0's licensed legacy
loader recognises JRXML 6 by its namespace; a namespace-less topic parses as JRXML 7 and fails:
"AdhocDataView state initialization error". Views re-saved on the server after promotion had a
normal topic and worked, which is why Billed Usage worked while Billed Amount did not.

| Org | Stripped views | Repaired | After repair |
| --- | ---: | ---: | --- |
| CityCorp | 103 | 103 | 97 rows, 3 empty, 6 slow, 0 errors |
| Newark1 | 8 | 8 | 6 rows, 2 slow, 0 errors |
| Ellensburg, College Station, Fond du Lac | 0 | | |

Tool: `scripts/jaspersoft/jrs_fix_stripped_topics.py` (scan / repair); the old topics are under
`backups/jaspersoft/topics/prod_<Org>_20260921-*`. Rule: the 9.0 strip is never run for a 10.0 target.

## Every Ad Hoc view on the three untouched orgs, opened and executed (20 s cap)

| Org | Views | Rows | Empty | Slow | Errors |
| --- | ---: | ---: | ---: | ---: | ---: |
| Ellensburg | 176 | 136 | 4 | 25 | 11 |
| College Station | 175 | 70 | 26 | 70 | 9 |
| Fond du Lac | 143 | 107 | 8 | 28 | 0 |

The 20 errors are database- or domain-side and predate the upgrade (each depends on something the
production database or the domain does not have). None is a Standard Offering view.

| Org | Views | Error | Cause |
| --- | --- | --- | --- |
| Ellensburg, College Station | `SC_Origin_Tools/Bill_Compare___Rate_Check/*` (6 + 6) | ORA-00942 `DATAVERGE1.DV_BC_BSEG_CALC` / `BC_CI_BSEG_CALC` does not exist | the Bill Compare tool queries a test-only schema; the prod databases have no `DATAVERGE1` |
| Ellensburg | `My_Reports/ELL_CWU_Billing/*` (3), `My_Reports/ELL_Res_Electric_Billing_Ad_Hoc_View` | query fields `ELL_CHARGE_TYPE.CHAR_VAL_DESC, CI_SA_RS_HIST.RS_CD, ELL_CALC_RULE_1.UNIT_RATE...` do not exist in the data source | user-saved views over a domain that no longer carries those fields |
| Ellensburg | `My_Reports/ELL_Cashier_Balancing_OLD1/ELL_Cashier_Balancing__1_` | `CI_PAY_TNDR_CHAR.ADHOC_CHAR_VAL` does not exist in the data source | same class |
| College Station | `Custom_Reports/CS_Receivebles_Aging/*` (2) | ORA-00904 `CISADM.CIRCVAGAFN` / `CIRCVAGAFN2` invalid identifier | a custom Oracle function the prod database does not have |
| College Station | `SC_Origin_Tools/SC_Trial_Balance_Pre_GO_Live/*` | `SC_TRIAL_BAL_TOTAL.DESCR, .DST_ID` do not exist in the data source | domain lost the fields |

Sweep files: `jaspersoft/sweeps/prod_<Org>_post_upgrade_views_20260921.json`. "Slow" = did not
answer within 20 s and was not waited for; College Station's 70 is that client's volume.
