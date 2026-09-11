"""An alert you can save but that can never fire is worse than one you cannot save.

Four executive KPIs are WINDOWLESS stock metrics -- billing accounts, service agreements,
accounts receivable, past-due balance. A stock has no prior period, so the runner returns
prior_value=None and change_pct=None for all of them, and evaluate_condition correctly
refuses to breach on None ("no data never breaches").

The consequence was silent: "alert me when Accounts receivable changes by more than 10%"
saved happily, looked configured, and could not fire in principle -- not once, not ever.
Measured: all four windowless KPIs return change_pct=None every run.

So the refusal moves to the moment of configuration, where there is somebody to tell.
The value conditions (above/below) stay available on stock metrics, because those are
exactly the questions worth asking of a balance.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.kpi_alerts import AlertError, assert_condition_can_fire  # noqa: E402


class TestPercentChangeOnAStockMetric:
    @pytest.mark.parametrize("condition", ["pct_change_above", "pct_change_below"])
    def test_is_refused_with_a_reason(self, condition: str) -> None:
        with pytest.raises(AlertError) as exc:
            assert_condition_can_fire("accounts_receivable", condition)
        message = str(exc.value).lower()
        assert "period" in message or "point-in-time" in message
        # The message must name the alternative, not just say no.
        assert "above" in message or "below" in message


class TestWhatStaysAllowed:
    @pytest.mark.parametrize("condition", ["above", "below"])
    def test_a_threshold_on_a_stock_metric_is_fine(self, condition: str) -> None:
        assert_condition_can_fire("accounts_receivable", condition)

    @pytest.mark.parametrize(
        "condition", ["above", "below", "pct_change_above", "pct_change_below"]
    )
    def test_every_condition_is_fine_on_a_windowed_kpi(self, condition: str) -> None:
        assert_condition_can_fire("billed_revenue", condition)

    def test_an_unknown_kpi_is_left_to_the_existing_check(self) -> None:
        """Not this function's job to decide the KPI exists."""
        assert_condition_can_fire("no_such_kpi", "pct_change_above")


def test_the_four_stock_metrics_are_the_ones_guarded() -> None:
    from api.executive_dashboard import EXECUTIVE_KPIS

    windowless = {k["id"] for k in EXECUTIVE_KPIS if k.get("windowless")}
    assert windowless == {
        "total_customers",
        "active_service_agreements",
        "accounts_receivable",
        "past_due_balance",
    }
    for kpi_id in windowless:
        with pytest.raises(AlertError):
            assert_condition_can_fire(kpi_id, "pct_change_above")
