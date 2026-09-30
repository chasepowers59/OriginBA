# Live Domain Fit Assessment

Date: 2026-04-23

## Purpose
Assess whether the retained `Live Domain` report families in the SmartCity standard offering are structurally aligned to their intended subject area and safe enough to keep as live semantic-layer reporting.

This is not a data-parity signoff. It is a structural fit review based on:
- exported Jaspersoft Domains and Ad Hoc views
- join-tree grain
- whether the saved views stay close to the intended business object
- known fan-out and custom-query risks

## Overall Position

### Safe to keep live
- Cashiering:
  - `Payment - Domain`
  - `Tender - Domain`
  - `Pay Plan - Domain`
  - `Deposit Control - Domain`
- Common:
  - `Batch Process - Domain`
  - `Bill Segment Exception - Domain`
  - `Usage Transaction Exception - Domain`
  - `VEE Exception - Domain`
  - `To Do - Domain`
- Customer Operations:
  - `Account Alert - Domain`
  - `Case - Domain`
  - `Customer - Domain`
  - `Customer Contact - Domain`
  - `Premise - Domain`
- New Services:
  - `New Services - Domain`
- Debt Management:
  - `Collection Process - Domain`
  - `SA Snapshot - Domain`
  - `Severance Process - Domain`
  - `Write Off Process - Domain`
  - `Write Offs - Domain`
- Field Operations:
  - `Field Activity - Domain`

### Keep with caution
- `M-Side - Domain`
- `C-Side - Domain`
- `To Do w/ Account Info - Domain`
- `Collection Process Amounts - Domain`
- `Debt Class - Domain`
- `Crew - Domain`
- `Location/Organization - Domain`

### Do not use as-is
- `AutoPay/Balances - Domain`
- `Payment Segments - Account View`

## Meter Operations Note

There is no true exported `Asset` Domain in the current live package set.

The closest retained live resource is `M-Side - Domain`, and it is not an asset registry domain. It is a `premise -> service point` domain with status and location enrichment.

That means:
- you can make useful service-point / meter-operations views from it
- you cannot honestly present it as a true enterprise asset report layer

Best meter-operations live reports from current resources:
- `Service Point Installations by Month`
  - based on `CI_SP.INSTALL_DT`
  - segmented by SP type, source status, cycle, route
- `Disconnected Service Points by Type and Location`
  - effectively the existing `M-Side - Disconnected Meters` pattern
  - segmented by disconnect location and SP type

Additional safe variants from the same Domain:
- `Service Point Inventory by Type and Source Status`
- `Abolished Service Points by Month`

I would avoid naming any of these `Asset` unless the client is comfortable that they are really service-point/device-adjacent operational views, not a governed asset master.

## Workstream Assessment

| Workstream | Domain | Root Grain | Verdict | Why |
|---|---|---|---|---|
| Cashiering | `Payment - Domain` | `CI_PAY` | Keep | Correct payment-header grain. |
| Cashiering | `Tender - Domain` | `CI_PAY_TNDR` | Keep | Correct tender grain and strongest cashiering live family. |
| Cashiering | `Pay Plan - Domain` | `CI_PP` | Keep | Correct pay plan header grain. |
| Cashiering | `Deposit Control - Domain` | `CI_TNDR_CTL` / `CI_DEP_CTL` | Keep | Appropriate for control-level balancing and ending balances. |
| Common | `Batch Process - Domain` | `CI_BATCH_INST` | Keep | Natural batch-run grain. |
| Common | `Bill Segment Exception - Domain` | `CI_BSEG_EXCP` | Keep | Natural exception grain. |
| Common | `Usage Transaction Exception - Domain` | `D1_USAGE_EXCP` | Keep | Natural exception grain and aligned to billing-impact use case. |
| Common | `VEE Exception - Domain` | `D1_VEE_EXCP` | Keep | Natural VEE exception grain. |
| Common | `To Do - Domain` | `CI_TD_ENTRY` | Keep | Natural to-do entry grain. |
| Common | `To Do w/ Account Info - Domain` | Custom query rooted on `CI_TD_ENTRY` context | Caution | Useful, but it resolves cross-context account/prem/person info through custom query logic. |
| Customer Operations | `Account Alert - Domain` | `CI_ACCT` | Keep | Appropriate for account-alert operational reporting. |
| Customer Operations | `Case - Domain` | `CI_CASE` | Keep | Case header grain is appropriate for case workload and aging reports. |
| Customer Operations | `Customer - Domain` | `CI_PER` | Keep | Proper customer/person grain. |
| Customer Operations | `Customer Contact - Domain` | `CI_CC` | Keep | Proper customer-contact grain. |
| Customer Operations | `Premise - Domain` | `CI_PREM` | Keep | Appropriate premise grain for premise reporting. |
| Customer Operations | `C-Side - Domain` | `CI_SA` | Caution | Useful for service/customer-side operational views, but not a pure customer master grain. |
| Meter Operations / Customer Operations V | `M-Side - Domain` | `CI_PREM` joined inner to `CI_SP` | Caution | Usable for service point / disconnected meter style views, but not a true asset or device master. Premises without SPs are excluded. |
| New Services | `New Services - Domain` | `CI_SA` | Keep | Correct for new-service / pending-SA reporting. |
| Debt Management | `Collection Process - Domain` | `CI_COLL_PROC` with child events | Keep with normal care | Good process grain, but reports should be explicit when event joins are involved. |
| Debt Management | `Collection Process Amounts - Domain` | Custom query aggregates | Caution | Looks intentionally aggregated and safer than raw joins, but it is custom logic and should be validated before heavy reuse. |
| Debt Management | `Debt Class - Domain` | Custom query | Caution | Appears to be a bespoke debt-class aggregate layer, not a standard raw semantic grain. |
| Debt Management | `SA Snapshot - Domain` | `CMS_SA_SNAPSHOT` | Keep | Already governed snapshot-style source, lower live-join risk. |
| Debt Management | `Severance Process - Domain` | `CI_SEV_PROC` | Keep | Appropriate severance process grain. |
| Debt Management | `Write Off Process - Domain` | `CI_WO_PROC` | Keep | Appropriate write-off process grain. |
| Debt Management | `Write Offs - Domain` | `C1_BI_WOPROC_VW` | Keep | View-based debt/write-off reporting source; acceptable if used as write-off summary reporting. |
| Field Operations | `Field Activity - Domain` | `D1_ACTIVITY` | Keep | Correct activity/work-order-style grain. |
| Field Operations | `Crew - Domain` | `C1_REPRESENTATIVE` | Caution | Likely okay for crew lookup and assignment rollups, but less central than activity grain. |
| Field Operations | `Location/Organization - Domain` | `W1_NODE` | Caution | Large join graph; better for reference/structure views than core KPI reporting. |

## Known Problem Areas

### 1. Auto Pay
- Current Domain is a custom `Financial + Equipment` mashup.
- It is not a governed cashiering grain.
- Accounts can be multiplied by service-point/equipment context.
- Keep out of the standard offering until rebuilt.

### 2. Payment Segments
- The saved report called `Payment Segments - Account View` is mostly finance/billing content.
- It is not a reliable payment-segment report.
- Remove or rebuild from proper `CI_PAY_SEG` grain later.

### 3. M-Side
- This is the closest current live resource for meter/device-adjacent reporting.
- It is still a service-point/premise view, not a true device or asset semantic layer.
- Safe only for narrowly framed SP/meter operations use cases.

## Practical Recommendation

### Keep in the standard offering now
- all retained live families listed as `Keep`
- the `Caution` families only for the specific report concepts already selected in the offering

### Do not expand casually from caution domains
- `M-Side`
- `C-Side`
- `To Do w/ Account Info`
- `Collection Process Amounts`
- `Debt Class`
- `Location/Organization`
- `Crew`

### Exclude until rebuilt
- autopay family
- misleading payment-segment family

## Minimum Validation Before Final Signoff

For each retained live family, validate a recent slice against direct SQL:

1. row count parity at the intended grain
2. no unexpected multiplication after optional enrichments
3. key business metric parity on one known date range

Priority validation order:
1. `M-Side`
2. `Collection Process Amounts`
3. `Debt Class`
4. `To Do w/ Account Info`
5. `Field Activity`
