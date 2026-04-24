# Live Domain Active Standard Offering QA

Date: `2026-04-24`

## Purpose

This document narrows live-domain QA scope to only the caution-risk families
that are actually active in the current SmartCity standard offering.

Items that are already excluded, secondary-only, or not part of the active
standard library are intentionally left out.

This document was updated after direct business clarification that:

- `M-Side - Domain` is no longer used in the active standard offering
- `C-Side - Domain` is no longer used in the active standard offering
- debt-management and cashiering are not part of the current active 7-snapshot
  implementation track

That means live-domain QA is not part of the current active snapshot workstream,
even though debt-class notes are retained here for future offering cleanup.

## Active Caution Families In Scope

There are no active live-domain QA targets in the current 7-snapshot
implementation track.

The debt-class note below is retained as deferred standard-offering guidance,
not as an active snapshot-optimization item.

### `Debt Class - Domain`

Active standard-offering report using this family:

- `Arrears by Debt Class`

Why this needs QA:

- the domain appears to be a bespoke aggregate layer, not a standard raw
  semantic grain
- aggregate-layer reports can be useful, but only if their grouping logic is
  provably stable

What to validate:

1. direct SQL parity for debt-class totals on a recent slice
2. confirm that one debt class is not duplicated across joins or summarization
3. document the exact business definition of the debt-class grouping
4. determine whether the live-domain report should remain active or be moved to
   the governed `ACCT_DEBT_RPT_CURR` layer

## Explicitly Out Of Scope For This QA Pass

These are not active-caution targets for the current pass:

- `M-Side - Domain`
- `C-Side - Domain`
- `Payment Segments - Account View`
- `AutoPay Drafts By Scheduled Date`
- `Autopay Accounts With Active Deposits`
- `Crew Detail`
- `Location Organization Detail`
- `To Do w/ Account Info`
- `Collection Process Amounts - Domain`

Reasons:

- no longer used in the active standard offering
- excluded from active standard content
- secondary only
- or not confirmed as active in the official standard library

## Recommended Next QA Sequence

1. `Debt Class - Domain` (deferred)

Why this order:

- it is the only caution live-domain family still carried forward in these
  notes after `M-Side` and `C-Side` were removed
- there is also a governed replacement path already designed in
  `ACCT_DEBT_RPT_CURR`, so the QA decision can directly inform whether the
  standard offering should stay live-domain here or migrate to the governed
  debt snapshot
