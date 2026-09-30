# test / Fond_Du_Lac: calibrated

10.0.0 PRO · /SmartCity/Report/Standard_Offering · swept 2026-09-19T07:07:42 in 289 s · cap 60 s per resource
Backup: `backups/jaspersoft/test/20260919-0656/Fond_Du_Lac.zip`

## Verdict

**BROKEN: errors below.** 160 resources: 120 ok, 26 empty, 13 slow (over 60 s), 1 error. Median ok time 3.5 s.

## Against the baseline (10.0.0 PRO, 2026-09-18T11:37:28)

- **Broke (ran before, errors now): 0**
- **Went empty: 0**
- **Now slow (ran within the cap before): 2**
  - `/SmartCity/Report/Standard_Offering/Finance/Financial_Transaction/Financial_Transaction___Current___Payoff_by_SA` — TimeoutError('The read operation timed out')
  - `/SmartCity/Report/Standard_Offering/Meter_Operations/Measurements/Measurements___No_Reads` — TimeoutError('The read operation timed out')
- **Healed: 0**
- **Missing now: 14**
  - `/SmartCity/Report/Standard_Offering/Billing_and_Rates/Billed_Amount/Billed_Amount___Dashboard`
  - `/SmartCity/Report/Standard_Offering/Billing_and_Rates/Billed_Amount/Executive_Multi_Utility_KPI_Dashboard`
  - `/SmartCity/Report/Standard_Offering/Billing_and_Rates/Billed_Usage/Billed_Usage___Dashboard`
  - `/SmartCity/Report/Standard_Offering/Cashiering/Payment_Header/Cashiering_Dashboard`
  - `/SmartCity/Report/Standard_Offering/Common/Batch/Batch_Process_Dashboard`
  - `/SmartCity/Report/Standard_Offering/Common/To_Do/Exception_and_To_Do_Dashboard`
  - `/SmartCity/Report/Standard_Offering/Customer_Operations/Customer_Contact/Customer_Operations_Dashboard`
  - `/SmartCity/Report/Standard_Offering/Debt_Management/SA_Snapshot___Aged_Balance/Collections_Performance_Dashboard`
  - `/SmartCity/Report/Standard_Offering/Field_Operations/Field_Activity/Field_Operations_Dashboard`
  - `/SmartCity/Report/Standard_Offering/Finance/Financial_Transaction/Finance_Dashboard`
  - `/SmartCity/Report/Standard_Offering/Finance/General_Ledger/General_Ledger___Dashboard`
  - `/SmartCity/Report/Standard_Offering/Meter_Operations/Measurements/Measurements___Dashboard`
  - `/SmartCity/Report/Standard_Offering/Meter_Operations/Usage/Usage_Dashboard`
  - `/SmartCity/Report/Standard_Offering/New_Services___Planning/New_Services/New_Services_Dashboard`
- **New: 0**

## Inventory: what changed since the last committed snapshot

- added 0, removed 0, changed 0 — sample: inventory diff not run

## Errors

- `/SmartCity/Report/Standard_Offering/Customer_Operations/Customer/Customer___SA_s_start_stop_last_6_months` — 500: Cannot invoke \"String.equals(Object)\" because \"s\" is null (Error UID: 4560f9ed-c935-4cde-9ec0-9c9eff5bc444)

## Slow (over 60 s, not waited for)

- `/SmartCity/Report/Standard_Offering/Billing_and_Rates/Billed_Amount/Billed_Amount___Billing_Activity`
- `/SmartCity/Report/Standard_Offering/Billing_and_Rates/Billed_Usage/Billed_Usage___Account_Level_View`
- `/SmartCity/Report/Standard_Offering/Cashiering/Payment_Tender/Tender___Account_Detail`
- `/SmartCity/Report/Standard_Offering/Common/Exception/VEE_Exceptions___Detailed_View`
- `/SmartCity/Report/Standard_Offering/Customer_Operations/Customer/Customer___Customers_Accounts_with_Active_Services`
- `/SmartCity/Report/Standard_Offering/Customer_Operations/Premise/Premise___Service_Points_at_Each_Premise_With_Linked_SA`
- `/SmartCity/Report/Standard_Offering/Debt_Management/SA_Snapshot___Aged_Balance/Aged_Debt___Accounts_with_Highest_Debt`
- `/SmartCity/Report/Standard_Offering/Debt_Management/SA_Snapshot___Aged_Balance/Aged_Debt___SA_View__Highest_Debt`
- `/SmartCity/Report/Standard_Offering/Finance/Financial_Transaction/Financial_Transaction___Current___Payoff_by_SA`
- `/SmartCity/Report/Standard_Offering/Meter_Operations/Measurements/Measurements___No_Reads`
- `/SmartCity/Report/Standard_Offering/Meter_Operations/Usage/Usage___Account_View`
- `/SmartCity/Report/Standard_Offering/Meter_Operations/Usage/Usage___by_Measuring_Component`
- `/SmartCity/Report/Standard_Offering/Meter_Operations/Usage_Transactions/Usage_Transaction___Not_Used_on_Bill`
