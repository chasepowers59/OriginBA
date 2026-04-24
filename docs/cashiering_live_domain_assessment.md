# Cashiering Live Domain Assessment

Date: 2026-04-23

Source reviewed:
- `C:\Users\cvpow\Downloads\Re__extracted\Cashiering_unzipped`
- Repository path in export:
  - `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Cashiering`

## Purpose
Confirm whether the current cashiering live Domains and Ad Hoc views are structurally accurate enough to support the SmartCity standard offering without misleading users.

## Overall Verdict

### Safe to keep as live reporting, with normal validation
- `Payment - Domain`
- `Tender - Domain`
- `Pay Plan - Domain`
- `Deposit Control - Domain`

### Do not trust as-is
- `Payment Segments - Account View`
- `AutoPay/Balances - Domain`
- reports under `Auto_Pay`

## Domain-by-Domain Findings

| Folder | Domain / Report Family | Driving Grain | Current Assessment | Notes |
|---|---|---|---|---|
| `Payment_Header` | `Payment - Domain` | `CI_PAY` | Usable | Saved views stay on payment header plus payment event. Customer-name joins still assume one main/primary person row. |
| `Payment_Header` | `Payment Segments - Account View` | Not truly payment-segment grain | Not usable | Saved view is mostly finance/billing content (`CI_FT`, `CI_BSEG`, `CI_SA`, `CI_ACCT`, `CI_PREM`) with only limited `CI_PAY_SEG` usage. |
| `Payment_Tender` | `Tender - Domain` | `CI_PAY_TNDR` | Usable | Saved views are aligned to tender grain. Main caution is optional control/name enrichment. |
| `Payment_Tender` | `Tender New - Domain` | `CI_PAY_TNDR` | Not active / not assessed for use | Export contains it, but the current saved views point to `Payment_Tender___Domain`, not `Tender_New___Domain`. |
| `Pay_Plan` | `Pay Plan - Domain` | `CI_PP` | Usable | Saved views stay mostly on pay plan header and formulas. |
| `Deposit_Control` | `Deposit Control - Domain` | `CI_TNDR_CTL` + `CI_DEP_CTL` | Usable with scope caution | Current saved views stay on control-level fields and do not appear to mix in tender-deposit detail. |
| `Auto_Pay` | `AutoPay/Balances - Domain` | Mixed custom query | Not usable | Custom `Financial` + `Equipment` query joined by account id is not a governed cashiering grain. |

## Saved View Review

### Payment Header
Reports reviewed:
- `Payment - Unfrozen Payments`
- `Payment - Cancel Reasons`
- `Payment - Creation Trends`
- `Payment - Lost Revenue Overview`

Observed field usage:
- dominated by `CI_PAY`
- secondarily `CI_PAY_EVENT`

Conclusion:
- The core payment views are directionally correct for payment-header reporting.
- They are not payment-segment reports.
- Use them for payment counts, creation trend, status/cancel trend, and header-level operational review.

### Payment Segments
Report reviewed:
- `Payment Segments - Account View`

Observed field usage:
- `CI_SA(36), CI_PREM(32), CI_BSEG(31), CI_FT(28), CI_ACCT(21), NewSet2(17), CI_ADJ(14), CI_PAY_SEG(7), CI_BAL_CTL_GRP_2(7), NewSet1(6)`

Conclusion:
- This report title is misleading.
- It is not centered on `CI_PAY_SEG`.
- It should not be presented as an authoritative cashiering payment-segment view.

### Tender
Reports reviewed:
- `Tender - Accounts with Highest NSF Payment Cancellations`
- `Tender - Payment Tender Distribution`
- `Tender - Payment Type Distribution`
- `Tender - Tender Amount Distribution`

Observed field usage:
- dominated by `CI_PAY_TNDR`
- secondarily `CI_PAY_EVENT`
- some description/formula sets

Conclusion:
- These are the strongest live cashiering reports in the export.
- They are aligned to tender grain and are appropriate for tender-focused reporting.
- Caution only if the business needs missing-control / orphan exception visibility, because the Domain still enriches through control and customer joins.

### Pay Plan
Reports reviewed:
- `Pay Plan - Active Pay Plans`
- `Pay Plan - Distribution Pay Plans`
- `Pay Plan - Cancel Reason Distribution Trend`
- `Pay Plan - Recently Canceled Pay Plans`
- `Pay Plan - Health Status`

Observed field usage:
- dominated by `CI_PP`
- formulas via `NewSet1` / `NewSet2`

Conclusion:
- These are acceptable live views for pay plan reporting.
- They are aligned to pay plan header grain.
- The current saved views are not leaning on the broader domain joins in a way that obviously creates fan-out.

### Deposit Control / Tender Control
Reports reviewed:
- `Deposit Control - Unbalanced Deposit Controls`
- `Deposit Control - Unbalanced Tender Controls`
- `Deposit Control - Deposit and Tender Control Details`
- `Deposit Control - Ending Balances`
- `Deposit Control - Ending Balances (Tender)`

Observed field usage:
- dominated by `CI_TNDR_CTL`
- secondarily `CI_DEP_CTL`
- formulas via `NewSet1` / `NewSet2`

Conclusion:
- These are acceptable live views for control-balancing and ending-balance reporting.
- The current saved views appear to stay on the control-level join tree, which is much safer than mixing in tender-deposit detail.
- These should be described as deposit/tender control reports, not as detailed tender-deposit transaction reports.

### Auto Pay
Reports reviewed:
- `Auto Pay - Autopay accounts with active deposits`
- `Auto Pay - Drafts By Scheduled Date`

Observed field usage:
- `Financial(8), Equipment(7)`

Conclusion:
- Not trustworthy as-is.
- The Domain is a custom mashup query, not a clean cashiering semantic layer.
- It is likely to duplicate account rows whenever the account has multiple equipment/service-point records.
- This confirms the current autopay family should be excluded until rebuilt.

## Recommendation for the Current Standard Offering

### Keep live
- Payment header reports, except `Payment Segments - Account View`
- Tender reports
- Pay plan reports
- Deposit control / tender control reports

### Remove or defer
- `Payment Segments - Account View`
- all `Auto_Pay` reports

## Minimum Validation Still Recommended

Before final client-facing use, run a slice validation for each retained family:

1. `Payment`
- compare row counts in a recent date slice between Domain report output and `CI_PAY`
- verify one row per payment header in the detail-style view

2. `Tender`
- compare row counts in a recent date slice between Domain report output and `CI_PAY_TNDR`
- verify canceled NSF counts against direct SQL

3. `Pay Plan`
- compare counts by status against `CI_PP`
- verify canceled pay plans and active pay plans on a small slice

4. `Deposit Control / Tender Control`
- verify unbalanced counts and ending balances on a recent control date slice
- confirm users understand these are control-level views, not detailed deposit transaction views

## Practical Decision

If we need to move now:
- proceed with live Domains for `Payment`, `Tender`, `Pay Plan`, and `Deposit Control`
- explicitly exclude `Auto Pay`
- explicitly exclude `Payment Segments - Account View`

If we later need stronger cashiering governance:
- rebuild `Auto Pay` from a proper Oracle grain
- rebuild payment-segment reporting from `CI_PAY_SEG` first, then enrich outward carefully
