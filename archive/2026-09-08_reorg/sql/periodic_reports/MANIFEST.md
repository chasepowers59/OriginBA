# Periodic Report Manifest

| ID | Frequency | Workstream | File | Grain | Measures | Source |
|----|-----------|------------|------|-------|----------|--------|
| A1 | annual | billing | `annual/billing/annual_billing_consumption_by_uom.sql` | SA_TYPE + UOM + SQI | `TOTAL_BILL_SQ`, segment count | `BSEG_SQ_USAGE_RPT_CURR` |
| A2 | annual | billing | `annual/billing/annual_billing_revenue_by_customer_class.sql` | CUST_CL + SA_TYPE | `TOTAL_CALC_AMT`, segment count | `BSEG_BILLED_USAGE_RPT_CURR` |
| A3 | annual | finance | `annual/finance/annual_finance_ft_by_type.sql` | FT_TYPE + SA_TYPE | `CUR_AMT`, FT count | `FT_RPT_CURR` |
| A4 | annual | finance | `annual/finance/annual_finance_ft_gl_by_account.sql` | GL_ACCT + DST_ID | debit/credit/net GL | `CI_FT` + `CI_FT_GL` |
| A5 | annual | finance | `annual/finance/annual_finance_adjustments_summary.sql` | ADJ_TYPE | `CUR_AMT`, count | `FT_RPT_CURR` |
| A6 | annual | payments | `annual/payments/annual_payments_by_tender.sql` | TENDER_TYPE + source | `TENDER_AMT`, count | `PAY_TNDR_CASH_RPT_CURR` |
| A7 | annual | workflow | `annual/workflow/annual_workflow_volume_by_type.sql` | TD_TYPE + status | queue count | `WORKFLOW_QUEUE_RPT_CURR` |
| A8 | annual | executive | `annual/executive/annual_executive_scorecard.sql` | KPI name | scalar KPIs | union of A1–A7 |
| Q1 | quarterly | billing | `quarterly/billing/quarterly_billing_consumption_by_uom.sql` | SA_TYPE + UOM + SQI | `TOTAL_BILL_SQ` | `BSEG_SQ_USAGE_RPT_CURR` |
| Q2 | quarterly | billing | `quarterly/billing/quarterly_bills_issued_completion.sql` | bill status | bill/bseg counts | `CI_BILL` + `CI_BSEG` |
| Q3 | quarterly | finance | `quarterly/finance/quarterly_finance_charges_vs_payments.sql` | FT category | `CUR_AMT` | `FT_RPT_CURR` |
| Q4 | quarterly | finance | `quarterly/finance/quarterly_finance_ft_gl_by_fund.sql` | GL_DIVISION + GL_ACCT | net GL | `FT_GL_DISTRIBUTION_RPT_CURR` |
| Q5 | quarterly | finance | `quarterly/finance/quarterly_finance_adjustments_summary.sql` | ADJ_TYPE | `CUR_AMT`, count | `FT_RPT_CURR` |
| Q6 | quarterly | workflow | `quarterly/workflow/quarterly_workflow_open_aging.sql` | aging bucket | open count | `WORKFLOW_QUEUE_RPT_CURR` |
| Q7 | quarterly | usage | `quarterly/usage/quarterly_usage_processing_volume.sql` | BO_STATUS | usage count | `D1_USAGE_RPT_CURR` |
| Q8 | quarterly | billing | `quarterly/billing/quarterly_billing_bseg_without_sq.sql` | SA_TYPE | bseg count | `CI_BSEG` + `CI_SA` |
| S1 | semi_annual | billing | `semi_annual/billing/semi_annual_billing_consumption_by_sa_type.sql` | SA_TYPE + UOM | `TOTAL_BILL_SQ` | `BSEG_SQ_USAGE_RPT_CURR` |
| S2 | semi_annual | billing | `semi_annual/billing/semi_annual_billing_revenue_trend.sql` | bill month | `TOTAL_CALC_AMT` | `BSEG_BILLED_USAGE_RPT_CURR` |
| S3 | semi_annual | payments | `semi_annual/payments/semi_annual_payments_vs_bills.sql` | category | amount totals | `FT_RPT_CURR` |
| S4 | semi_annual | finance | `semi_annual/finance/semi_annual_finance_adjustment_trend.sql` | month + ADJ_TYPE | `CUR_AMT` | `FT_RPT_CURR` |
| S5 | semi_annual | finance | `semi_annual/finance/semi_annual_finance_arrears_movement.sql` | SA_TYPE | arrears `CUR_AMT` | `FT_RPT_CURR` |
| S6 | semi_annual | field_ops | `semi_annual/field_ops/semi_annual_field_activity_summary.sql` | activity type + status | activity count | `FIELD_ACTIVITY_RPT_CURR` |

## Calendar windows

| Frequency | Expression |
|-----------|------------|
| Annual | previous full calendar year |
| Quarterly | previous full calendar quarter |
| Semi-annual | previous six full calendar months |

Details: [lib/calendar_windows.sql](lib/calendar_windows.sql)
