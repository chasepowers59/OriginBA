# Governed Snapshot Client Reporting Guide

## Purpose

This guide helps utility clients and report builders choose the right governed Oracle snapshot for a business question, understand what population each table carries (including status and date scope), and map snapshots to common municipal utility reporting needs.

It covers:

- **Active 7** — production rollout set (finance, billing, meter ops)
- **Consolidation 12** — phase-2 rollout (customer ops, field ops, cashiering, debt, common)
- **Additional governed snapshots** — already built with Domain XML; rollout tier varies by client

For deployment order and refresh scripts, see:

- [00_active_snapshot_deployment_manifest.md](../deployment_steps/00_active_snapshot_deployment_manifest.md)
- [00_consolidation_snapshot_deployment_manifest.md](../deployment_steps/00_consolidation_snapshot_deployment_manifest.md)

For importable Jaspersoft Domains, see [snapshot_xml_inventory.md](snapshot_xml_inventory.md) (`domains/exports/manual_imports/*_End_User_Friendly.xml`).

---

## How clients use snapshots

Governed snapshots are **pre-joined, pre-described Oracle tables** refreshed on a schedule. Clients point Jaspersoft Domains, Ad Hoc views, Topics, and pixel-perfect reports at a snapshot instead of rebuilding CISADM join graphs at runtime.

| Client need | Snapshot approach |
|---|---|
| Self-service analysis by billing, finance, or ops staff | Import Domain XML → Ad Hoc |
| Scheduled operational dashboards | Domain or Topic + dashboard |
| Regulator or council packs | JRXML report on snapshot Domain |
| Cross-workstream questions | Join Domains at shared keys (`ACCT_ID`, `SA_ID`, `PREM_ID`, dates) or build a dashboard with multiple panels |

**Design principle:** Snapshots load **full business status on the driving population** (open, closed, canceled, pending, complete) unless the snapshot has an intentional business scope (pipeline, debt-only, BODA field work). Filter status in JRS when the question is operational (“open only”, “canceled last month”).

**Refresh model:**

| Phase | Procedure | Meaning |
|---|---|---|
| Baseline | `02a_full_history_refresh_procedure.sql` | One-time full seed for Ad Hoc history |
| Operational | `02_refresh_snapshot_procedure.sql` | Rolling window maintenance (6 or 12 months) with “still relevant” retention for open/incomplete work |

---

## Master reference matrix

Legend for **Population scope**:

- **Full** — all rows on driving table (all statuses carried as columns)
- **Debt** — only SAs/accounts with positive governed arrears on frozen FT
- **Pipeline** — pending/recent start-service SAs only (`10`/`20`; excludes declined/canceled proposals)
- **BODA** — field activities/crews with BODA profile (matches legacy Standard Offering domain population)
- **Dedup** — excludes redundant FT rows (`REDUNDANT_SW = 'N'`)
- **Completed bills** — completed bill segments only (billing truth)

| Snapshot | Workstream | Grain | Driving source | Rolling window | Population scope (baseline) | Status / scope notes | Trusted measure | Domain XML |
|---|---|---|---|---|---|---|---|---|
| `FT_RPT_CURR` | Finance | `FT_ID` | `CI_FT` | 12 mo | Dedup | All FT types/statuses; not GL line grain | `CUR_AMT` | Yes |
| `FT_GL_DISTRIBUTION_RPT_CURR` | Finance | `FT_ID` + `GL_SEQ_NBR` | `CI_FT_GL` | 6 mo | Dedup | GL line detail; not FT header totals | `GL_AMOUNT` | Yes |
| `BILLABLE_CHARGE_RPT_CURR` | Finance | `BILLABLE_CHG_ID` + `LINE_SEQ` | `CI_B_CHG_LINE` | 6 mo | Full | All charge line statuses | `CHARGE_AMT` | Yes |
| `BSEG_BILLED_USAGE_RPT_CURR` | Billing | `BSEG_ID` | `CI_BSEG` + `CI_BILL` | 12 mo | Completed bills | Segment/bill statuses as columns | `TOTAL_BILL_SQ`, `TOTAL_CALC_AMT` | Yes |
| `BSEG_SQ_USAGE_RPT_CURR` | Billing | `BSEG_ID` + determinant key | `CI_BSEG_SQ` | 12 mo | Completed bills | UOM / TOU / SQI breakdown | `TOTAL_BILL_SQ` | Yes |
| `D1_USAGE_RPT_CURR` | Meter ops | `D1_USAGE_ID` | `D1_USAGE` | 12 mo | Full | Usage BO status as column; requires anchor datetime | count / context | Yes |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | Meter ops | `D1_USAGE_ID` + `SEQ_NUM` | `D1_USAGE` + scalar detail | 12 mo | Full | Scalar quantities by determinant | `QUANTITY`, `FINAL_QUANTITY` | Yes |
| `D1_MSRMT_RPT_CURR` | Meter ops | final measurement | `D1_MSRMT` (processed) | 12 mo | Full | Measurement status/use/condition as columns | measurement values | Yes |
| `DEVICE_SP_RPT_CURR` | Meter ops | `D1_DVC_ID` | `D1_DVC` | 6 mo | Full | Device/SP/ install status as columns | count at device grain | Yes |
| `PAY_TNDR_CASH_RPT_CURR` | Cashiering | `PAY_TENDER_ID` | `CI_PAY_TNDR` | 6 mo | Full | Tender/pay/deposit statuses as columns | `TENDER_AMT` | Yes |
| `PAY_EVENT_RPT_CURR` | Cashiering | `PAY_ID` | `CI_PAY` | 6 mo | Full | Payment status, cancel reason as columns | `PAY_AMT` | Yes |
| `ACCT_DEBT_RPT_CURR` | Debt | `ACCT_ID` | `CI_FT` → `CI_SA` | 6 mo | Debt | Active SA (`20`) with governed arrears | `TOTAL_DEBT` | Yes |
| `SA_AGED_BAL_RPT_CURR` | Debt | `SA_ID` | `CI_FT` → `CI_SA` | 6 mo | Debt | SA with positive arrears; op refresh scopes active/recently ended SA | `TOTAL_DEBT` | Yes |
| `COLL_PROC_RPT_CURR` | Debt | `COLL_PROC_ID` | `CI_COLL_PROC` | 6 mo | Full | Process status as column | context only | Yes |
| `WO_PROC_RPT_CURR` | Debt | `WO_PROC_ID` | `CI_WO_PROC` | 6 mo | Full | Write-off process status as column | context / counts | Yes |
| `ACCT_CUSTOMER_RPT_CURR` | Customer ops | `ACCT_ID` | `CI_ACCT` | 6 mo | Full | All accounts; dormant accounts age out in `02` | aggregates | Yes |
| `CASE_PREM_CONTACT_RPT_CURR` | Customer ops | `CASE_ID` | `CI_CASE` | 6 mo | Full | Open + closed cases; filter in JRS | count at case grain | Yes |
| `NEW_SERVICE_PIPELINE_RPT_CURR` | New services | `SA_ID` | `CI_SA` | 6 mo | Pipeline | Pending `10` + recent active `20`; excludes declined/canceled proposals | count at SA grain | Yes |
| `FIELD_ACTIVITY_RPT_CURR` | Field ops | `D1_ACTIVITY_ID` | `D1_ACTIVITY` (FA) | 6 mo | BODA | All FA statuses (completed, canceled, open); BODA population only | count / aging | Yes |
| `CREW_OPS_RPT_CURR` | Field ops | `CREW_ID` | `C1_REPRESENTATIVE` | 6 mo | BODA | Crew status + rolled-up FA metrics | rollups | Yes |
| `OPS_EXCEPTION_RPT_CURR` | Common | `EXCP_SOURCE` + key | `CI_BSEG_EXCP`, `D1_USAGE_EXCP`, `D1_VEE_EXCP` | 6 mo | Full | Open/closed exception flags as columns | count | Yes |
| `WORKFLOW_QUEUE_RPT_CURR` | Common | `QUEUE_SOURCE` + key | `CI_TD_ENTRY`, `CI_BATCH_INST` | 6 mo | Full | All to-do statuses + batch threads on baseline | count / duration | Yes |

---

## Active 7 — production snapshots

These are the first tables deployed on client test databases. They underpin most **Finance**, **Billing and Rates**, and **Meter Operations** snapshot reports in the [Standard Offering library](../../../docs/smartcity_standard_offering_report_library.md).

### Finance

#### `FT_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Monitor financial transaction volume, revenue mix, adjustment activity, and GL distribution health at transaction header grain. |
| **Example reports** | Financial Transaction - Total Transactions by Type; GL Distribution Status; Billed Revenue Trend; Payment Account Detail; Service Type FT Summary |
| **Filter in JRS** | `FT_TYPE_FLG`, `GL_DISTRIB_STATUS`, `SA_STATUS_FLG`, `ADJ_STATUS_FLG`, bill cycle, customer class |
| **Do not use for** | GL account totals → use `FT_GL_DISTRIBUTION_RPT_CURR` |
| **Population** | All non-redundant FT rows; canceled/pending/frozen statuses retained |

#### `FT_GL_DISTRIBUTION_RPT_CURR`

| | |
|---|---|
| **Utility use case** | GL posting reconciliation, revenue by distribution code, batch-level GL review, write-off and adjustment GL tracing. |
| **Example reports** | General Ledger - GL Account and Distribution; Revenue Totals; Write Off Amounts; By Batch Number; Accounts Receivable |
| **Filter in JRS** | GL account, distribution code, `GL_DISTRIB_STATUS`, FT type, accounting date |
| **Do not use for** | Unduplicated FT header totals → use `FT_RPT_CURR` |

### Billing and rates

#### `BSEG_BILLED_USAGE_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Billed consumption and billed amount at completed bill-segment grain; cycle performance; estimated vs actual; rebills and cancellations. |
| **Example reports** | Billed Usage and Amount Charged; Billed Amount by Customer Class / Utility Type / Rate Schedule; Canceled Segments; Estimated Segment; Rebills; Account Level View |
| **Filter in JRS** | `BSEG_STAT_FLG`, bill cycle, customer class, SA type, completion date |
| **Population** | Completed bill population (billing truth); canceled segments **included** for exception analysis |

#### `BSEG_SQ_USAGE_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Determinant-level billed quantity (UOM, TOU, SQI); tiered usage; class × UOM segmentation. |
| **Example reports** | Billed Usage - Segment Determinant; Across Customer Class & UOM; Tiered Billed Usage; By SA Type & Class |
| **Do not use for** | Segment-level dollar totals without understanding determinant grain → prefer `BSEG_BILLED_USAGE_RPT_CURR` for amount |

### Meter operations

#### `D1_USAGE_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Usage transaction pipeline monitoring; billing bridge status; subscription/route/cycle operations. |
| **Example reports** | Usage Transaction - By SA Type; by Subscription Type; Usage - Account View (header-level) |
| **Filter in JRS** | `BO_STATUS_CD`, usage reason, route, cycle, service provider |

#### `D1_USAGE_SCALAR_DTL_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Scalar quantity analysis, high-usage customer identification, premise/class consumption research. |
| **Example reports** | Usage - Highest Usage Customers; Customer Class and UOM; Premise Consumption; by Measuring Component ID |
| **Trusted sums** | `QUANTITY`, `FINAL_QUANTITY` at usage × sequence grain |

#### `D1_MSRMT_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Final accepted measurement review, estimated read exceptions, cycle read totals, measurement condition trends. |
| **Example reports** | Measurement - IMD Summary; Reads and Totals by Cycle; Measurements - Estimated; by Service Point ID; Meter Reads - Counts by Component Type |

---

## Consolidation 12 — phase-2 snapshots

Deploy after active 7 baseline on a client. These unlock Standard Offering reports that today use **Live Domain** sources in customer ops, field ops, cashiering, debt, and common exception/to-do areas.

### Customer operations

#### `ACCT_CUSTOMER_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Account master for outreach, segmentation, life-support identification, open-alert monitoring without alert-row fan-out. |
| **Example reports (target)** | Customer - Critical Care & Safety; C-Side - Accounts on Life Support; Account Alert - Collections Risk; premise/SA population summaries |
| **Key columns** | Customer class, bill cycle, contacts, `OPEN_ALERT_COUNT`, `ACTIVE_SA_COUNT`, life-support flags |
| **Population** | All accounts on baseline; operational refresh drops long-dormant accounts with no recent SA/alert activity |

#### `CASE_PREM_CONTACT_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Case workload, aging, closure outcomes, premise overlays, latest customer-contact context per case. |
| **Example reports (target)** | Case - Open Cases by Account/Class; Cases Created by Month; Average Case Duration; Closed Case Outcomes; Time in Previous State |
| **Filter in JRS** | `CASE_STATUS_CD`, case type, owner, customer class — **open vs closed is a report filter, not a load filter** |
| **Do not use for** | Row-per-contact history or case log transitions |

### New services

#### `NEW_SERVICE_PIPELINE_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Start-service backlog, stale pending SAs, recently connected services, enrollment trace by division/geography. |
| **Example reports (target)** | New Services - Pending Service Agreements; New Service Counts; Premise Growth |
| **Intentional scope** | **Not all SAs** — only pipeline statuses (`SA_STATUS_FLG` `10`/`20`, proposal not declined/canceled) |
| **Key columns** | `STALE_PENDING_SW`, `DAYS_SINCE_CREATED`, `SA_STATUS_DESC`, premise address, SA type |

### Field operations

#### `FIELD_ACTIVITY_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Field work scheduling, overdue orders, cancellation analysis, appointment-required populations, SP/premise context on work. |
| **Example reports (target)** | Field Activity - Upcoming Field Work; Overdue Work Orders; Cancellations; Trends by Task Type; Average Days per Field Task |
| **Filter in JRS** | `BO_STATUS_CD` (completed, canceled, pending, etc.), activity type, division, appointment flag |
| **Scope note** | BODA-profiled field activities only (matches legacy Field Activity domain population) |

#### `CREW_OPS_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Crew workload, open vs completed mix, aged open work by service area/capability. |
| **Example reports (target)** | Crew - Incomplete Work Orders; Completed and Discarded |
| **Do not use for** | Row-level appointment/contact detail → use `FIELD_ACTIVITY_RPT_CURR` |

### Meter operations (device)

#### `DEVICE_SP_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Installed meter/device inventory, serial traceability, current SP/premise placement, asset linkage. |
| **Example reports (target)** | Replaces live Device - Daily Installations / Disconnected Devices / Meters Not Recently Read once Domains repoint |
| **Filter in JRS** | `BO_STATUS_CD`, `CURRENTLY_INSTALLED_SW`, device type, SP type |
| **Do not use for** | Install-event history or measurement detail |

### Cashiering

#### `PAY_EVENT_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Payment header reporting with event date, status/cancel analysis, pay-plan presence, tender/deposit overlays at payment grain. |
| **Example reports (target)** | Payment - Creation Trends; Cancel Reasons; Unfrozen Payments; Lost Revenue Overview |
| **Filter in JRS** | `PAY_STATUS_FLG`, cancel reason, pay date |
| **Do not use for** | Tender-level channel mix → use `PAY_TNDR_CASH_RPT_CURR` |

### Finance (charges)

#### `BILLABLE_CHARGE_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Unbilled/billable charge line monitoring, charge template workload, SA/account charge context before billing completes. |
| **Example reports** | Ad Hoc charge status dashboards; finance ops charge backlog by template and SA type |
| **Filter in JRS** | `BILLABLE_CHG_STAT`, charge dates, SA status |
| **Do not use for** | Posted billed segment reconciliation → use `BSEG_*` snapshots |

### Debt management

#### `SA_AGED_BAL_RPT_CURR`

| | |
|---|---|
| **Utility use case** | SA-level arrears outreach, aging buckets, premise-linked debt segmentation — **replacement for legacy SA Snapshot aged-balance live domain**. |
| **Example reports (target)** | SA Snapshot - Aged Debt by Customer Class; Arrear Buckets (By Class); Total Amount of Aged Arrears |
| **Intentional scope** | **Debt-only population** (positive governed arrears on frozen FT), not all service agreements |
| **Filter in JRS** | Customer class, debt class, SA type, bucket columns |

#### `WO_PROC_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Write-off process workload, template/status monitoring, next event tracking, process duration when BI view populated. |
| **Example reports (target)** | Write Off Process - Active Write Off Processes; Write Offs - Average Process Duration; Write Offs - Debt Written Off Trend |
| **Population** | All write-off process statuses on baseline; open processes retained outside window in operational mode |

### Common / cross-functional

#### `OPS_EXCEPTION_RPT_CURR`

| | |
|---|---|
| **Utility use case** | Unified billing/MDM exception triage across bill segment, usage, and VEE sources with primary to-do overlay. |
| **Example reports (target)** | Bill Segment Exception - Open Bill Segments; Usage Transaction Exceptions - Incomplete; VEE Exception severity/rule dashboards |
| **Filter in JRS** | `EXCP_SOURCE`, `OPEN_CLOSE_FLG`, severity, review status, linked to-do status |
| **Do not use for** | General to-do queue → use `WORKFLOW_QUEUE_RPT_CURR` |

#### `WORKFLOW_QUEUE_RPT_CURR`

| | |
|---|---|
| **Utility use case** | To-do backlog and batch thread monitoring; assignment aging; batch error counts. |
| **Example reports (target)** | To Do - Incomplete Entries; To Do - Unassigned Duration Trend; Batch Process - Incomplete Batch Runs; Recent Batches |
| **Filter in JRS** | `ENTRY_STATUS_FLG` (`O` open, `W` working, `C` complete), `QUEUE_SOURCE` (`TODO` vs `BATCH`), role, type |
| **Historical note** | Baseline includes **all** to-do statuses; operational refresh keeps open to-dos regardless of age |

---

## Additional governed snapshots (outside active-7 rollout)

These have Domain XML and SQL workspaces; client scheduling varies.

| Snapshot | Utility use case | Example Standard Offering reports | Notes |
|---|---|---|---|
| `ACCT_DEBT_RPT_CURR` | Account-level debt exposure and collections segmentation | Collection Process - Arrears by Customer Class/Debt Class | Debt-only; active SA arrears rolled to account |
| `COLL_PROC_RPT_CURR` | Collections **process** workflow (not debt truth) | Collection Process - Active Collections; Upcoming Collection Events; Age of Unpaid Bills | `ARS_AMT` is context, not replacement for `TOTAL_DEBT` |
| `PAY_TNDR_CASH_RPT_CURR` | Tender channel mix, deposit/tender control ops | Tender - Payment Tender Distribution by Status; Tender Type Distribution | Tender grain; complements `PAY_EVENT_RPT_CURR` |

---

## Workstream chooser (quick)

```
Question about…                          → Start here
─────────────────────────────────────────────────────────────
Billed usage or billed $ on a bill       → BSEG_BILLED_USAGE_RPT_CURR
Billed quantity by UOM/TOU/SQI           → BSEG_SQ_USAGE_RPT_CURR
Financial transaction header $/counts    → FT_RPT_CURR
GL account / distribution detail         → FT_GL_DISTRIBUTION_RPT_CURR
Unbilled charge lines                    → BILLABLE_CHARGE_RPT_CURR
Usage process / billing bridge           → D1_USAGE_RPT_CURR
Usage scalar quantities                  → D1_USAGE_SCALAR_DTL_RPT_CURR
Final accepted reads/measurements        → D1_MSRMT_RPT_CURR
Device installed where / serial          → DEVICE_SP_RPT_CURR
Payment header / cancel / pay plan       → PAY_EVENT_RPT_CURR
Tender channel / cashiering detail       → PAY_TNDR_CASH_RPT_CURR
Account debt total                       → ACCT_DEBT_RPT_CURR
SA-level aging buckets                   → SA_AGED_BAL_RPT_CURR
Collections process activity             → COLL_PROC_RPT_CURR
Write-off process activity               → WO_PROC_RPT_CURR
Account/customer master                  → ACCT_CUSTOMER_RPT_CURR
Case workload                            → CASE_PREM_CONTACT_RPT_CURR
Start-service pipeline                   → NEW_SERVICE_PIPELINE_RPT_CURR
Field work order detail                  → FIELD_ACTIVITY_RPT_CURR
Crew workload                            → CREW_OPS_RPT_CURR
Billing/usage/VEE exceptions             → OPS_EXCEPTION_RPT_CURR
To-dos and batch threads                 → WORKFLOW_QUEUE_RPT_CURR
```

---

## Status and population rules (summary)

| Rule | Applies to |
|---|---|
| **Full status on driving table** | Most snapshots — cases, field activities, payments, to-dos, write-offs, exceptions, bill segments, usage, devices |
| **Filter in JRS, not in SQL** | Open-only queues, canceled-only analysis, completed-only KPIs when snapshot already carries the status column |
| **Intentional business scope** | `NEW_SERVICE_PIPELINE` (pipeline SAs); `SA_AGED_BAL` / `ACCT_DEBT` (debt only); `FIELD_ACTIVITY` / `CREW_OPS` (BODA population) |
| **Technical dedup** | `FT_*` snapshots exclude `REDUNDANT_SW = 'Y'` |
| **Rolling retention** | Old **completed/closed** rows may age out; **open/incomplete** rows typically stay (workflow queue, exceptions, write-offs, billable charges without end date) |

---

## Client rollout pattern

1. Deploy and baseline **active 7** → validate → schedule 6-hour refreshes.
2. Import Domain XML for active snapshots → migrate Finance/Billing/Meter snapshot reports.
3. Deploy **consolidation 12** → baseline `02a` → cutover to `02` → validate with `consolidation_demo_physical_table_qa.sql` pattern.
4. Repoint Live Domain Standard Offering reports to consolidation snapshot Domains where mapped above.
5. Keep status/date filters in **report input controls** or Ad Hoc filters so one snapshot serves both operational and historical views.

Runbook: [smartcity_consolidation_snapshot_rollout_runbook.md](../../../docs/smartcity_consolidation_snapshot_rollout_runbook.md)

Analytics portal POC (demo-only web explorer): [analytics_portal_poc.md](../../../docs/analytics_portal_poc.md)

---

## Related docs

- [workstream_snapshot_catalog.md](workstream_snapshot_catalog.md) — technical catalog and grain rules
- [business_question_snapshot_coverage.md](business_question_snapshot_coverage.md) — question-level coverage matrix
- [smartcity_standard_offering_report_library.md](../../../docs/smartcity_standard_offering_report_library.md) — full 104-report library
- Per-snapshot README under `sql/performance/snapshots/<workstream>/<subset>/`
