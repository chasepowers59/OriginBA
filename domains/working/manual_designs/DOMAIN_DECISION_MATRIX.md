# Domain Decision Matrix (Business Users)

Use this page to pick the right domain fast.

## Quick Picker

| If your question is about... | Use this domain | Why |
|---|---|---|
| Consumption/quantity and billed dollars by customer class, account, SA, rate | `Billed_Usage_Consumption_Billed_Amount_Perf_6M.xml` | Best detailed billed-usage + billed-amount analytics |
| Same as above, but you need fastest response and fewer fields | `Billed_Usage_Consumption_Billed_Amount_UltraLean.xml` | Leanest design, minimal joins |
| Operational usage only (no financials), with device/meter and customer/account context | `D1_Usage_Device_Account_Outlier_180D.xml` | D1 usage fact model for top-usage, outlier analysis, and device-account association |
| Revenue by rate code / rate component / component type | `Billed_Revenue_By_Rate_Component_Perf_6M.xml` | Built for rate-component revenue analysis |
| Tax-focused rate component revenue with faster runtime | `Billed_Revenue_Tax_Lean_Perf_6M.xml` | Lean join model that keeps RC type tax context |
| Tax-focused analysis with fastest possible load time | `Billed_Revenue_Tax_ULTRA_LEAN_30D.xml` | Ultra-lean 30-day model using FT tax amount (`FT_GL_TAX_AMT`) |
| Reconciliation between billed usage and financial postings | `Usage_Billing_Financial_Bridge_PerfFast_6M.xml` | Bridge model with performance-focused structure |
| Same bridge use case, but safer/fallback version | `Usage_Billing_Financial_Bridge_No_Derived_UltraSafe.xml` | Minimal join fallback |
| Current unbilled revenue estimate (usage + non-usage + tax) | `Unbilled_Revenue_Snapshot_Perf.xml` | Fast single-table daily snapshot model |
| GL/fund mapping and fund balance detail at transaction level | `Fund_Balance_Final_DB_Validated.xml` | DB-validated detailed fund path |
| Fund balance trends by month | `Fund_Balance_Monthly_PerfSafe.xml` | Aggregated monthly model for speed |
| Write-off operations, debt movement, recovery effectiveness | `Write_Off_Requirements_Final_DB_Validated.xml` | Full write-off KPI and recovery context |
| Collections process effectiveness at reducing overdue debt | `Collections_Process_Effectiveness_Debt_Reduction_180D.xml` | Process-level arrears deltas to next process with event summary |
| To Do queue operations with assignee aging and resolved account/customer context | `To_Do_Entry_Operations_Account_Resolved.xml` | Preserves To Do rows and resolves account via direct FK or SA fallback |
| Expected vs actual billing (who should be billed vs who was billed) | `Billing_Requirements_No_Derived_Full_Logic.xml` | Best reconciliation logic for billing requirements |

## Choose by Business Outcome

| Business outcome | Primary domain | Secondary/fallback |
|---|---|---|
| Usage & billing trend dashboards | `Billed_Usage_Consumption_Billed_Amount_Perf_6M.xml` | `Billed_Usage_Consumption_Billed_Amount_UltraLean.xml` |
| Usage outlier detection by account/device without finance fields | `D1_Usage_Device_Account_Outlier_180D.xml` | `Billed_Usage_Consumption_Billed_Amount_UltraLean.xml` |
| Rate design / tariff revenue analysis | `Billed_Revenue_By_Rate_Component_Perf_6M.xml` | `Billed_Usage_Consumption_Billed_Amount_Perf_6M.xml` |
| Tax component monitoring dashboards | `Billed_Revenue_Tax_Lean_Perf_6M.xml` | `Billed_Revenue_By_Rate_Component_Perf_6M.xml` |
| Tax monitoring during ad hoc exploration/performance constraints | `Billed_Revenue_Tax_ULTRA_LEAN_30D.xml` | `Billed_Revenue_Tax_Lean_Perf_6M.xml` |
| Finance-to-billing reconciliation | `Usage_Billing_Financial_Bridge_PerfFast_6M.xml` | `Usage_Billing_Financial_Bridge_No_Derived_UltraSafe.xml` |
| Unbilled revenue accrual monitoring | `Unbilled_Revenue_Snapshot_Perf.xml` | none |
| Fund reporting / GL mapping | `Fund_Balance_Final_DB_Validated.xml` | `Fund_Balance_Monthly_PerfSafe.xml` |
| Write-off governance and recovery KPI | `Write_Off_Requirements_Final_DB_Validated.xml` | none |
| Collections process effectiveness in reducing overdue debt | `Collections_Process_Effectiveness_Debt_Reduction_180D.xml` | `Write_Off_Requirements_Final_DB_Validated.xml` |
| To Do operational queue management and backlog aging | `To_Do_Entry_Operations_Account_Resolved.xml` | `Collections_Process_Effectiveness_Debt_Reduction_180D.xml` |
| Billing gap detection | `Billing_Requirements_No_Derived_Full_Logic.xml` | none |

## Performance Rules (Always)

1. Apply a date filter first in Ad Hoc (Accounting Date, Bill Date, or Create Date).
2. Start with summary measures before adding detailed IDs.
3. Add high-cardinality fields (IDs, timestamps) only when needed for drilldown.
4. Use UltraLean/UltraSafe domains for exploratory ad hoc and switch to detailed domain for final analysis.

## Notes

- Archived/legacy domains are in `domains/working/archive/manual_designs`.
- Full business descriptions and replacement mapping:
  - `DOMAIN_BUSINESS_CATALOG.md`
  - `../archive/manual_designs/REPLACEMENT_MAP.md`
