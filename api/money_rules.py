"""What counts as money, per canvas, in one place.

Only frozen bill segments are billed money, only frozen financial transactions are money
at all, and a cancelled payment or tender is money that came back out. Every sum a page,
card or governed metric shows over these canvases carries the canvas's filters below;
tests/test_money_rules.py checks each one against this table. Found 2026-09-28: governed
billed revenue, governed payments and the cashiering 'Payments collected' card all summed
cancelled or unfrozen rows (Ellensburg Cycle 5: $2,699,379.89 shown, $2,682,879.14 true).
"""
from __future__ import annotations

from typing import Any

FROZEN = {"field": "Is Frozen", "op": "eq", "value": True}
NOT_CANCELLED = {"field": "Is Cancelled", "op": "eq", "value": False}
# PAY_STATUS_FLG is a base-product lookup: 30 Freezable, 50 Frozen, 60 Cancelled.
PAYMENT_FROZEN = {"field": "Payment Status Code", "op": "eq", "value": "50"}

# canvas -> the filters any SUM over it must carry
MONEY_FILTERS: dict[str, list[dict[str, Any]]] = {
    "rpt_bill_segment": [FROZEN, NOT_CANCELLED],
    "rpt_billed_usage": [FROZEN, NOT_CANCELLED],
    "rpt_financial_txn": [FROZEN],
    "rpt_payment": [PAYMENT_FROZEN],
    "rpt_payment_tender": [NOT_CANCELLED],
}


def missing_money_filters(snapshot_id: str, query: dict[str, Any],
                          default_lens: list[dict[str, Any]] | None = None) -> list[str]:
    """The required filters a query that sums over this canvas does not carry. A card's
    default lens (its first) applies unless the reader picks another, so it counts."""
    if not any(m.get("agg") == "sum" for m in query.get("measures") or []):
        return []
    have = {(f.get("field"), f.get("op"), f.get("value"))
            for f in [*(query.get("filters") or []), *(default_lens or [])]}
    return [f["field"] for f in MONEY_FILTERS.get(snapshot_id, [])
            if (f["field"], f["op"], f["value"]) not in have]
