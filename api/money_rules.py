"""What counts as money, per canvas, in one place.

Only frozen bill segments are billed money, only frozen financial transactions are money
at all, and a cancelled payment or tender is money that came back out. Every sum a page,
card, governed metric or ready-to-run report shows over these canvases carries the canvas's
filters below, plus its measure's where one has a rule of its own; tests/test_money_rules.py
checks each one against this table. Found 2026-09-28: governed
billed revenue, governed payments and the cashiering 'Payments collected' card all summed
cancelled or unfrozen rows (Ellensburg Cycle 5: $2,699,379.89 shown, $2,682,879.14 true).
"""
from __future__ import annotations

from typing import Any

FROZEN = {"field": "Is Frozen", "op": "eq", "value": True}
NOT_CANCELLED = {"field": "Is Cancelled", "op": "eq", "value": False}
# PAY_STATUS_FLG is a base-product lookup: 30 Freezable, 50 Frozen, 60 Cancelled.
PAYMENT_FROZEN = {"field": "Payment Status Code", "op": "eq", "value": "50"}
# Billed quantity counts only on usage lines: tier lines repeat a quantity, and derived SQI
# lines (days, multipliers, credits) and demand/power-factor lines are not consumption
# (Ellensburg 2026-09-30: a 31.85M unit-less bar, Gallons 47% high without it).
IS_USAGE = {"field": "Is Usage", "op": "eq", "value": True}

# canvas -> the filters any SUM over it must carry
MONEY_FILTERS: dict[str, list[dict[str, Any]]] = {
    "rpt_bill_segment": [FROZEN, NOT_CANCELLED],
    "rpt_billed_usage": [FROZEN, NOT_CANCELLED, IS_USAGE],
    "rpt_financial_txn": [FROZEN],
    "rpt_payment": [PAYMENT_FROZEN],
    "rpt_payment_tender": [NOT_CANCELLED],
}

# (canvas, measure) -> the filters a SUM of that measure also needs. An adjustment
# cancellation FT (AX) carries the cancelled adjustment's amount with the SAME sign, so only
# AD rows of a standing adjustment count (CI_ADJ status 50 Frozen, 60 Cancelled; base product).
# Ellensburg 2026-09-30: $15,572,430.42 shown, $15,096,751.09 standing.
STANDING_ADJUSTMENT = [{"field": "Is Adjustment", "op": "eq", "value": True},
                       {"field": "Adjustment Status Code", "op": "eq", "value": "50"}]
MEASURE_FILTERS: dict[tuple[str, str], list[dict[str, Any]]] = {
    ("rpt_financial_txn", "Adjustment Amount"): STANDING_ADJUSTMENT,
    ("rpt_financial_txn", "Adjustment Base Amount"): STANDING_ADJUSTMENT,
}


def missing_money_filters(snapshot_id: str, query: dict[str, Any],
                          default_lens: list[dict[str, Any]] | None = None) -> list[str]:
    """The required filters a query that sums over this canvas does not carry. A card's
    default lens (its first) applies unless the reader picks another, so it counts."""
    summed = [m.get("field") for m in query.get("measures") or [] if m.get("agg") == "sum"]
    if not summed:
        return []
    have = {(f.get("field"), f.get("op"), f.get("value"))
            for f in [*(query.get("filters") or []), *(default_lens or [])]}
    required = [*MONEY_FILTERS.get(snapshot_id, []),
                *(f for field in summed for f in MEASURE_FILTERS.get((snapshot_id, field), []))]
    missing = [f["field"] for f in required if (f["field"], f["op"], f["value"]) not in have]
    return list(dict.fromkeys(missing))
