# Budget domain: budget accounts, late fees, budget changes

`/SmartCity/Report/Standard_Offering/Billing_and_Rates/Budget_Billing/Budget___Domain`

Built for College Station's request (2026-09-29): active accounts on budget billing, those with
late fees in the past year, and budget accounts updated each month. Patch:
`scripts/jaspersoft/patch_budget_domain.py` (tests: `tests/test_budget_domain_patch.py`), applied
in place by `jrs_domain_patch_apply.py --patch patch_budget_domain`. `schema.reference.xml` is the
Origin_DEV schema before the patch, `schema.patched.xml` what the server holds after it.

## The rules, measured before they were written

| Question | Rule | Why not the obvious one |
| --- | --- | --- |
| Is an account on budget? | An SA on a budget-ELIGIBLE SA type (`CI_SA_TYPE.ELIG_BUDGET_SW = 'Y'`), Active or Pending Stop (`20`, `30`), whose current recurring charge (latest `CI_SA_RCHG_HIST` row not in the future) is above zero | The budget plan code is on 104,826 College Station accounts; 965 are on budget. Amount > 0 without the eligibility flag adds 496 flat recurring charges |
| Late fees | Frozen adjustments (`CI_ADJ.ADJ_STATUS_FLG = '50'`) in the last 12 months, by adjustment type; cancelled (`60`) counted apart | Summing `ADJ_AMT` over `CI_FT` counts a cancelled fee twice (charge and cancel both carry it); grouping `CI_FT` timed out at College Station |
| Which adjustment type is the late fee | The client's own LPC algorithm names it: College Station `CM-LATEPYMT` "LPC Adjustment Type" = `LPC`; Ellensburg `C2M-LPC-PCT` = `LPC`. It is the VIEW's saved filter, never the domain's | Client configuration |
| Who changed a budget | Not recorded: `CI_SA_RCHG_HIST` has no source column; `CI_BUD_RVW` keeps only each account's latest review (1,617 rows = 1,617 accounts). The change tree lists every change with the latest review beside it | |

## What the patch adds (nothing existing changes: `domain_schema.additions_only` is empty)

- **JoinTree_1** (the original SA x recurring-charge tree): `Budget Eligible SA Type` and
  `Is On Budget` (set `1.) Budget Status`).
- **JoinTree_2 `2.) Budget Accounts`**: one row per account on budget (`BA_BUDGET`, always
  included, so an account-only view still lists only budget accounts). Account, main customer,
  plan, bill cycle, class, monthly budget amount, budget SA counts, latest review; and
  `2.) Adjustments (Last 12 Months)` -- one row per adjustment TYPE, so filter it to one type.
- **JoinTree_3 `3.) Budget Changes`**: one row per budget amount change (`BC_CHANGE`, always
  included): prior, new and change amount, Budget Started / Increased / Decreased / Ended /
  Restarted, change month, SA type and status, latest review.

## Validation (Origin_DEV = Ellensburg 25.4 TEST database, 2026-09-30)

| Check | Domain | Oracle |
| --- | --- | --- |
| Accounts on budget / monthly budget total | 389 / $90,580 | 389 / $90,580 |
| Budget accounts with LPC in 12 months / fees / amount | 68 / 142 / $1,414.63 | 68 / 142 / $1,414.63 |
| Budget changes, Sep 2025 (accounts / SAs) | 129 / 413 | 129 / 413 |
| Budget changes, Jul 2026 | 260 / 987 | 260 / 987 |
| `Is On Budget = Y` on JoinTree_1, distinct accounts | 389 | 389 |

Apply proof: read back byte-equal, metadata lists all 11 sets, all 5 views bound to the domain
still execute, probe 389 rows in 0.9 s. College Station TEST (Oracle, same SQL): 965 accounts,
5,552 budget SAs, $336,581 monthly; 594 with LPC, 4,330 fees, $28,884.35.

## The three views (College Station's request)

1. **Budget Billing - Active Accounts**: Budget Accounts tree, one row per account: Account ID,
   Main Customer Name, Budget Plan, Customer Class, Bill Cycle, Monthly Budget Amount, Budget
   Service Agreements, Latest Budget Amount Effective Date. No filter needed.
2. **Budget Billing - Late Fees Last 12 Months**: the same, plus Adjustments Assessed and
   Adjustment Amount (Frozen); filters Adjustment Type Code = the client's late-fee type (LPC at
   College Station and Ellensburg) and Adjustments Assessed > 0.
3. **Budget Billing - Budget Changes by Month**: Budget Changes tree, Change Month as rows, Change
   Kind as columns, Distinct Accounts as the measure; filter Change Effective Date in the last 12
   months up to today (a few future-dated recurring-charge rows exist -- 2030-2032 at Ellensburg).
