# Bill Cycle Schedule - Domain (Standard Offering, built 2026-09-24)

`/SmartCity/Report/Standard_Offering/Billing_and_Rates/Bill_Cycle_Schedule/Bill_Cycle_Schedule___Domain`:
the billing calendar, one row per cycle window. Built by `scripts/jaspersoft/build_bill_cycle_schedule_domain.py`
(tests `tests/test_bill_cycle_schedule_domain.py`), imported with `jrs_import_domain.py`, promoted with `jrs_promote.py`.

Sets: 1 Bill Cycle Schedule (window dates, accounting and estimated dates, freeze complete), 1.1 Bills In
The Window (count, completed, pending, accounts billed, first/last completion, first bill date, last due
date), 1.2 Bill Segments In The Window (count, frozen, canceled, open, estimated, with exceptions, SAs),
1.3 Cycle Today And Neighbouring Windows (accounts on cycle, ACTIVE accounts on cycle, window sequence,
previous window end, next window start, gap in days), 2 Flags And Formulas (freeze complete, has bills,
past / current / future, past-and-not-frozen, active accounts not billed, freeze-complete-but-pending,
open segments, exceptions, window length, days window end to last completion, estimate to accounting),
Measures. All "today" arithmetic is SQL in the folds (the Ad Hoc engine evaluates DomEL `Today()` in
memory under the 300,000-row cap).

## Facts (Origin_DEV's database = Ellensburg 25.4 test, 2026-09-24)

- 436 windows, 10 cycles, 411 freeze complete; 405 past, 2 current, 29 future, 25 past-and-not-frozen.
- The join is cycle + window start EQUALITY: 361,952 of 724,783 bills carry a window; the other 360,401
  have NO cycle at all (off-cycle bills: blank cycle and window, out of a calendar's scope by
  definition) and 2,430 sit on a 2026-07-07 window that is missing from the schedule table itself.
  Zero unmatched bills fall inside any window's date range, so the legacy range join would have added
  nothing. Bill segments: 1,238,897 of 2,465,206 carry a window, the rest the same way.
- "Accounts on cycle" counts every account with the cycle code (18,367 on cycle 01) while only the
  ones with an ACTIVE service agreement are billable (2,427; the window billed 2,386): the not-billed
  gap is against the active count. It goes negative when accounts billed then have since closed.

## Proofs (all exact against Oracle)

Through the domain: 436 windows / 10 cycles; bills 361,952, completed 359,733; segments 1,238,897,
estimated 57,594, with exceptions 4,827; freeze Y 411 / N 25; past 405, current 2, future 29,
past-not-frozen 25. Per window, May-June 2026, every fold column to the row: cycle 01 2026-05-06
2,386 bills / 2,386 accounts / 8,672 segments / 18,367 on cycle / 2,427 active; cycle 05 2026-05-01
1,212 / 1,212 / 3,656 / 5,090; cycle 04 2026-05-20 1,198 / 3,923 / 8,094; cycle 06 2026-05-22
2,555 / 7,133 / 32,128; cycle 07 2026-05-29 134 / 256 / 397.
