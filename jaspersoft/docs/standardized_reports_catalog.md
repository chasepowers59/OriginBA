# Standardized Reports: the catalog and the build rules (2026-09-25)

**Moved 2026-10-05:** the folder is now `/SmartCity/Report/Origin_BA_2_0/Standardized_Reports` on Origin_DEV, part of the
Origin BA 2.0 release beside the generated domains (`Origin_BA_2_0/Domains`). All seven units ran from there.

Chase's brief: one `Standard_Offering/Standardized_Reports` folder a client schedules from (now `Origin_BA_2_0/Standardized_Reports`); every
report easy to read, with an as-of date or window and the input controls that let a client SAVE a
filtered copy as their own report (JasperServer's "save as" on a report with controls); summary
totals with detail rows underneath; built from what clients already use (the legacy `SC_*` list
reports), Oracle's own C2M reporting, and utility reporting norms across the nine workstreams;
portable across clients (no client code in SQL; pick-lists from the client's own configuration).

## Rules every report follows (they are the tests in `tests/test_sql_report_pack.py`)

1. **Two dates or one.** A WINDOW report takes `FROM_DT` / `TO_DT` (inclusive); a POSITION report
   takes `AS_OF_DT` (the pack's `as_of=True` mode). Never both.
2. **Every code the client configures is a pick-list** built from the client's own label table,
   limited to codes with activity in the last three years; every pick-list is optional (empty =
   all) and multi-select where a user would naturally pick several (cycles, tender types,
   statuses, SA types, divisions).
3. **Lifecycle switches are parameters with defaults**, not hard-coded: status sets, "include
   canceled", "age by", "as known today". Only base-product lifecycle codes are literal, each with
   its reason in `constants`.
4. **Summary first, detail under it**: the main query is the grouped summary with totals; the
   subreport lists the rows behind each summary line (top N or all, a parameter). Both take
   every filter.
5. **Portable SQL**: COALESCE not NVL, no SYSDATE (CURRENT_DATE), no ROWNUM (FETCH FIRST), TRIM on
   every CHAR flag, label joins at ENG on their full key, division-qualified SA types.
6. **Proof per client before it ships**: the summary's totals tie a direct Oracle query on that
   client's database; the detail count ties the summary count; a saved filtered copy still runs.
7. **Interactive layout** (next template step, see below): the summary and the detail are Table
   components so the viewer can sort, filter and hide columns; PDF/XLS exports keep the layout.

## Wave 1: the reports (grouped by workstream; * = exists today in the folder)

| Workstream | Report | Cadence | Summary rows (totals) | Detail rows | Dates | Pick-lists and switches |
| --- | --- | --- | --- | --- | --- | --- |
| Billing | Billing by Cycle* | weekly | cycle x window: bills, segments, billed amount, estimated | service type under each cycle | window on bill date | cycles (multi), service type, division |
| Billing | Bill Cycle Calendar | weekly | cycle window: scheduled vs completed, bills, pending, estimated, exceptions, late freeze | the windows of one cycle | window on window start | cycles (multi), only-incomplete switch |
| Billing | Bills In Error And Unbilled | daily | cycle x exception type: segments in error, accounts unbilled past window | segment, account, customer, message | as of | cycles, exception type, division |
| Billing | Billed Usage And Revenue by Service Type | monthly | service type x rate: bills, usage by UOM, billed amount | rate schedules under each service type | window on bill date | service type, rate, division, cust class |
| Cashiering | Payments by Tender Type* | daily/monthly | tender type x day: count, amount, canceled | payments under each type | window on payment date | tender types (multi), source, payor account |
| Cashiering | Cashier Drawer Balancing | daily | tender control x source x cashier: tenders, amount, deposit control, variance | tenders in each control | window on tender date | tender source (multi), cashier, deposit control |
| Cashiering | Unapplied And Overpaid | daily | account: credit balance, unapplied payments, last payment | payments behind each | as of | cust class, division, minimum amount |
| Finance | Adjustments by Type* | monthly | type: count, net, debits, credits | largest adjustments | window on created date | type (multi), status set, division |
| Finance | GL by Distribution Code* | monthly | distribution code x accounting period: debits, credits, net | FTs behind each | window on accounting date | distribution codes (multi), GL division, FT type |
| Finance | Adjustment A/P Requests Control* | daily | request status x adjustment status with the action needed | requests | window on created date | request status, adjustment status, action-only, account |
| Finance | Deposits Held | monthly | SA type x cust class: deposit SAs, held, interest, refunds due | deposit SAs | as of | SA type, cust class, division |
| Debt | Aged Debt As Of Date* | monthly | division x SA type: SAs, balance, five buckets | largest balances | as of | cust class, division, account; age-by, as-known-today |
| Debt | Collections Pipeline | weekly | process template x status: processes, arrears, average age | processes with account and customer | as of | template, status set, cust class |
| Debt | Disconnects And Reconnects | daily | dispatch group x day: severance events due, FAs created, completed, pending | events with FA status | window on trigger date | event type, dispatch group, status set |
| Debt | Write-Off Activity | monthly | reason x SA type: processes, amount written off, recovered | processes | window on completion date | reason, SA type, division |
| Customer Ops | Customer Contacts | weekly | contact class x type: contacts, open, by channel | contacts with account | window on contact date | class, type (multi), user |
| Customer Ops | Cases Open And Aging | daily | case type x status condition: open, average age, over N days | cases with account, premise | as of | case type (multi), status, division, N days |
| Customer Ops | Service Agreement Starts And Stops | weekly | SA type x reason: starts, stops, net | SAs with account, premise | window on start/stop date | SA type, start/stop reason, division |
| Customer Ops | Active Customers And Service Agreements | monthly | division x cust class x SA type: active accounts, active SAs, premises served | none (a position count) | as of | division, cust class, service type |
| Meter Ops | Installs And Removals | weekly | device type x SP type: installs, removals, switched off | install events with premise | window on install/removal date | device type, SP type, division |
| Meter Ops | Meters Not Reading | daily | measuring component type: devices silent N days, estimated last bill | devices with premise and last measurement | as of | MC type, N days, route |
| Meter Ops | Unbilled Usage | weekly | SA type: SPs with usage after last bill, unbilled quantity | SPs | as of | SA type, cycle, division |
| Field Ops | Field Activity Backlog | weekly | FA type x dispatch group x status: open, average age, overdue | activities with SP and premise | as of | FA type (multi), dispatch group, status set |
| Common | To Do Backlog | daily | To Do type x role: open, assigned, average age | entries with the related account | as of | type (multi), role, priority |
| Common | Batch Run Health | daily | batch control: runs, errors, records, duration | runs | window on run date | batch control (multi), status |

Legacy `SC_*` list reports covered by the above: Billed Revenue, Billed Usage, Billing Overview, Bill
Print Audit (add as "Bill Print Routing" if a client asks), Unbilled Billing, Payment Tender, Tender
Control, Deposit Control, OriginPay Payments (client product; keep out of the standard set), FT/GL,
Adjustment, AR Aging (= Aged Debt As Of Date), SA Arrears Revenue, Collection Process, Severance
Process, Customer Contacts, Case, To Do, Batch, Field Work Activities, Asset, Vacant Premise
Consumption (= Unbilled Usage with the vacancy switch), SA Rate History (a customer-ops detail:
add on request), Left/Right Side V (account / service point 360 lists: Ad Hoc territory).

## Build order

1. Template step first: the interactive Table layout (summary table + detail table with group
   rows), proven on ONE existing report in the viewer on Origin_DEV (sort, filter, hide, export).
   Then every report gets it for free.
2. Position reports with the as-of mode: Cases Open And Aging, Collections Pipeline, Field
   Activity Backlog, To Do Backlog, Active Customers And SAs, Deposits Held, Meters Not Reading.
3. Window reports: Disconnects And Reconnects, Cashier Drawer Balancing, Bills In Error, Installs
   And Removals, SA Starts And Stops, Customer Contacts, Batch Run Health, Bill Cycle Calendar,
   Billed Usage And Revenue, Write-Off Activity, Unapplied And Overpaid, Unbilled Usage.
4. Relative dates for scheduling: date-range controls (`MONTH-1`, `WEEK-1`, `DAY-1`) on every
   report, so a schedule never needs editing.

Each report lands with: its spec in `generate_sql_report_pack.py`, its tests, a deploy to
Origin_DEV, the Oracle tie, and a saved-filtered-copy check; promotion to clients on Chase's word.
