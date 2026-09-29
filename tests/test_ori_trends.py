"""Ori's trends: unusual months, a projection that has earned its place, and a plain read.

Every home card with a date window gets a monthly history (complete months only, ending at
the organization's reporting date; its default lens and filters, so the history is the card's
own number month by month). From it:

- An UNUSUAL MONTH is the latest complete month outside the range of the 12 before it, at
  least 3.5 robust deviations (modified z, median and MAD) and 15% from their median, with
  enough volume to matter (the findings' floors). Seasonal peaks inside last year's range
  are not unusual. At most three, most extreme first.
- A PROJECTION of the next three months uses the same months last year scaled by how the
  last three months compared with a year earlier, or the average of the last 12 months,
  whichever missed the three-month TOTAL less replayed on the organization's own past
  months (the total is what the headline states). It is published only when that miss was
  at most 15% in a typical case and at most 25% in four cases of five, over at least 8
  checks; its range is that 80th-percentile past miss either side.
- ORI'S READ is one short paragraph from the compare-mode home summary: big moves named,
  moderate ones named, steady cards grouped.
"""
from __future__ import annotations

import sys
import unittest
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import ori_series  # noqa: E402
from api.ori_insights import anomalies, brief, forecasts  # noqa: E402

META = {"billed": {"label": "Billed revenue", "format": "currency"},
        "bills": {"label": "Bills", "format": "number"}}


def series(values, start=(2023, 6)):
    y, m = start
    out = []
    for v in values:
        out.append({"month": f"{y:04d}-{m:02d}", "value": float(v)})
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


BASE12 = [640, 1674, 2535, 1846, 2110, 2728, 1820, 1955, 2557, 1732, 1822, 2532]


class ApproxTests(unittest.TestCase):
    def test_estimates_read_like_format_ts_compact(self):
        from api.ori_insights import _approx
        cases = [(11242511.38, "currency", "$11.2M"), (9438880.07, "currency", "$9.44M"), (13046142.69, "currency", "$13M"),
                 (35298.4, "number", "35.3K"), (999950, "currency", "$1M"), (-9500, "currency", "-$9,500.00"),
                 (-12071.26, "currency", "-$12.1K"), (9412.4, "number", "9,412"), (2.5e9, "number", "2.5B")]
        for value, fmt, want in cases:
            self.assertEqual(_approx(value, fmt), want, value)


class MonthTests(unittest.TestCase):
    def test_only_complete_months_up_to_the_reporting_date(self):
        self.assertEqual(ori_series.complete_months(date(2026, 6, 18), 3), ["2026-03", "2026-04", "2026-05"])
        self.assertEqual(ori_series.complete_months(date(2026, 5, 31), 2), ["2026-04", "2026-05"])
        self.assertEqual(ori_series.complete_months(date(2026, 1, 10), 2), ["2025-11", "2025-12"])

    def test_rows_become_a_gapless_series_from_the_first_month_with_data(self):
        months = ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05"]
        rows = [[datetime(2025, 5, 1), Decimal("7.50")], [date(2025, 2, 1), 3], ["2025-04-01 00:00:00", None]]
        self.assertEqual(ori_series.series_from_rows(months, rows),
                         [{"month": "2025-02", "value": 3.0}, {"month": "2025-03", "value": 0.0},
                          {"month": "2025-04", "value": 0.0}, {"month": "2025-05", "value": 7.5}])
        self.assertEqual(ori_series.series_from_rows(months, []), [])

    def test_the_history_is_the_cards_own_number_by_month(self):
        kpi = {"id": "payments_collected", "snapshot_id": "rpt_payment", "date_field": "Payment Date",
               "value": {"dimensions": [], "measures": [{"field": "Pay Segment Amount", "agg": "sum"}],
                         "filters": [{"field": "X", "op": "eq", "value": 1}]},
               "lenses": [{"id": "frozen", "filters": [{"field": "Payment Status Code", "op": "eq", "value": "50"}]}]}
        calls = []

        def run(snapshot_id, spec, date_field, start, end, extra, *, organization_id, time_dimensions=None):
            calls.append((snapshot_id, spec, date_field, start, end, extra, organization_id, time_dimensions))
            return ["TD0", "m0"], [[date(2026, 5, 1), 10], [date(2026, 4, 1), 5]]

        with mock.patch.object(ori_series, "run_kpi_query", side_effect=run), \
             mock.patch.object(ori_series, "resolve_lenses", side_effect=lambda k, **_: k), \
             mock.patch.object(ori_series, "reporting_today", return_value=date(2026, 6, 18)):
            out = ori_series.monthly_history(kpi, "demo25", months=3)
        self.assertEqual(out, [{"month": "2026-04", "value": 5.0}, {"month": "2026-05", "value": 10.0}])
        [(snap, spec, field, start, end, extra, org, tds)] = calls
        self.assertEqual((snap, field, start, end, org), ("rpt_payment", "Payment Date", "2026-03-01", "2026-05-31", "demo25"))
        self.assertEqual(spec["filters"], [{"field": "X", "op": "eq", "value": 1}])
        self.assertEqual(extra, [{"field": "Payment Status Code", "op": "eq", "value": "50"}])
        self.assertEqual(tds, [{"field": "Payment Date", "grain": "month"}])
        self.assertGreaterEqual(spec["limit"], 3)


class AnomalyTests(unittest.TestCase):
    def test_a_month_far_outside_the_year_before_is_unusual(self):
        [a] = anomalies({"billed": series(BASE12 + [153])}, META)
        self.assertEqual((a["kpi_id"], a["month"], a["direction"]), ("billed", "2024-06", "low"))
        self.assertEqual(a["headline"], "Billed revenue for Jun 2024: unusually low")
        self.assertEqual(a["question"], "What made billed revenue so low in Jun 2024? What changed from the months before?")
        self.assertEqual(a["detail"], "$153.00, below every one of the 12 months before "
                                      "($640.00 to $2,728.00; typical $1,900.50).")
        self.assertIn("Jun 2024", a["question"])

    def test_a_month_inside_the_years_range_is_not_unusual(self):
        self.assertEqual(anomalies({"billed": series(BASE12 + [2700])}, META), [])
        self.assertEqual(anomalies({"billed": series(BASE12 + [2728])}, META), [])

    def test_needs_a_full_year_before_it(self):
        self.assertEqual(anomalies({"billed": series(BASE12[1:] + [153])}, META), [])

    def test_thin_volume_is_not_unusual(self):
        self.assertEqual(anomalies({"bills": series([5, 6, 5, 7, 6, 5, 6, 7, 5, 6, 5, 6, 1])}, META), [])

    def test_a_flat_series_moves_only_past_fifteen_percent(self):
        self.assertEqual(anomalies({"bills": series([100] * 12 + [110])}, META), [])
        [a] = anomalies({"bills": series([100] * 12 + [130])}, META)
        self.assertEqual(a["direction"], "high")
        self.assertEqual(a["detail"], "130, above every one of the 12 months before (100 to 100; typical 100).")

    def test_at_most_three_most_extreme_first(self):
        hist = {f"k{i}": series(BASE12 + [2728 + 400 * i]) for i in range(1, 6)}
        meta = {k: {"label": k, "format": "currency"} for k in hist}
        self.assertEqual([a["kpi_id"] for a in anomalies(hist, meta)], ["k5", "k4", "k3"])


def seasonal(years, growth=1.05, shape=(80, 75, 90, 100, 120, 150, 170, 165, 130, 100, 85, 80)):
    out = []
    for y in range(years):
        out += [s * 1000 * growth ** y for s in shape]
    return out


class ForecastTests(unittest.TestCase):
    def test_a_regular_series_is_projected_three_months_with_its_range(self):
        values = seasonal(3)
        [f] = forecasts({"billed": series(values, start=(2023, 6))}, META)
        self.assertEqual([p["month"] for p in f["forecast"]], ["2026-06", "2026-07", "2026-08"])
        expected = [v * 1.05 for v in values[-12:-9]]
        for p, want in zip(f["forecast"], expected):
            self.assertAlmostEqual(p["value"], want, places=2)
            self.assertLessEqual(p["low"], p["value"])
            self.assertGreaterEqual(p["high"], p["value"])
        self.assertAlmostEqual(f["total"], sum(expected), places=2)
        self.assertLess(f["typical_error_pct"], 0.01)
        self.assertGreaterEqual(f["checks"], 8)
        self.assertEqual(len(f["history"]), 12)
        self.assertEqual(f["history"][-1]["month"], "2026-05")
        # an estimate reads like a KPI headline (format.ts formatCompact); a measured value keeps every digit
        self.assertEqual(f["headline"], "Billed revenue: about $284K over Jun to Aug 2026")
        self.assertIn("same months last year", f["detail"])
        self.assertIn("Jun to Aug 2026", f["question"])

    def test_a_level_series_without_a_season_uses_the_twelve_month_average(self):
        # Ellensburg payments, 2026-09-29: last year's months missed by 17.7%, the 12-month average by 14.6%
        x, noisy = 7, []
        for _ in range(36):
            x = (1103515245 * x + 12345) % 2 ** 31
            noisy.append(3_500_000 * (1 + 0.5 * (x / 2 ** 31 - 0.5)))
        [f] = forecasts({"billed": series(noisy)}, META)
        self.assertIn("average of the last 12 months", f["detail"])
        self.assertAlmostEqual(f["forecast"][0]["value"], sum(noisy[-12:]) / 12, places=2)
        self.assertLess(f["typical_error_pct"], 15)
        [g] = forecasts({"billed": series(seasonal(3))}, META)
        self.assertIn("same months last year", g["detail"])

    def test_the_three_month_total_is_what_is_tested_and_stated(self):
        # payments slip between months: single months miss by ~19%, three-month totals by ~6%
        x, slips = 11, []
        for _ in range(37):
            x = (1103515245 * x + 12345) % 2 ** 31
            slips.append(x / 2 ** 31 * 1_200_000)
        values = [3_500_000 + slips[i + 1] - slips[i] for i in range(36)]
        [f] = forecasts({"billed": series(values)}, META)
        self.assertLess(f["typical_error_pct"], 10)
        self.assertEqual(f["checks"], 19)
        self.assertIn("three-month total", f["detail"])
        self.assertLessEqual(f["total_low"], f["total"])
        self.assertLess(f["total_high"] - f["total_low"], sum(p["high"] - p["low"] for p in f["forecast"]))

    def test_a_range_too_wide_to_inform_is_not_projected(self):
        # Ellensburg field activities, 2026-09-29: typical miss 11% but "between 6,173 and 15,514"
        values = seasonal(3)
        values[30] *= 2.5
        values[34] *= 2.5
        self.assertEqual(forecasts({"billed": series(values)}, META), [])

    def test_an_irregular_series_is_not_projected(self):
        noisy = [349, 1342, 675, 355, 966, 270, 14891, 3132, 303, 294, 6433, 949, 11280, 2164, 878, 629, 1011, 294,
                 306, 11879, 713, 558, 1367, 250, 384, 12382, 640, 1674, 2535, 1846]
        self.assertEqual(forecasts({"billed": series(noisy)}, META), [])

    def test_needs_eight_past_checks_and_positive_history(self):
        self.assertEqual(forecasts({"billed": series(seasonal(3)[-23:])}, META), [])
        values = seasonal(3)
        values[-14] = 0.0
        values[-13] = 0.0
        values[-15] = 0.0
        self.assertEqual(forecasts({"billed": series(values)}, META), [])

    def test_a_range_spanning_the_new_year_names_both_years(self):
        [f] = forecasts({"bills": series(seasonal(3), start=(2023, 11))}, META)
        self.assertEqual(f["headline"], "Bills: about 284K over Nov 2026 to Jan 2027")


def card(kid, label, change, fmt="number", **kw):
    return {"id": kid, "label": label, "format": fmt, "value": 100.0, "prior_value": 90.0, "change_pct": change,
            "compare_label": "vs prior 30d", "error": None, **kw}


class BriefTests(unittest.TestCase):
    PERIOD = {"label": "Last 30 days to Jun 18, 2026", "days": 30}

    def test_big_moves_named_first_then_moderate_then_steady_grouped(self):
        summary = {"period": self.PERIOD, "kpis": [
            card("billed_revenue", "Billed revenue", -17.9), card("payments_collected", "Payments", 9.2),
            card("bills_completed", "Bills", 1.0), card("field_activities", "Field activities", -3.4),
            card("customer_contacts", "Customer contacts", 0.2),
            card("accounts_receivable", "Accounts receivable", None, compare_label=None)]}
        self.assertEqual(brief(summary),
                         "In the last 30 days to Jun 18, 2026, billed revenue fell 18% against the 30 days before. "
                         "Payments rose 9%. Bills, field activities and customer contacts held within 5%.")

    def test_two_steady_cards_and_no_moves(self):
        summary = {"period": {"label": "Last 30 days", "days": 30},
                   "kpis": [card("a", "Bills", 1.0), card("b", "Payments", -2.0)]}
        self.assertEqual(brief(summary), "In the last 30 days, bills and payments held within 5% of the 30 days before.")

    def test_failed_or_windowless_cards_say_nothing(self):
        summary = {"period": self.PERIOD, "kpis": [card("a", "Bills", 20.0, error="could not connect"),
                                                   card("b", "Payments", None)]}
        self.assertIsNone(brief(summary))
        self.assertIsNone(brief({"kpis": []}))

    def test_thin_cards_are_not_named_as_moves(self):
        # demo25, 2026-09-29: "bills rose 200%" on 1 -> 3 bills, while the findings (same floors) said nothing
        summary = {"period": {"label": "Last 30 days", "days": 30}, "kpis": [
            card("a", "Billed revenue", 55.0, fmt="currency", value=236.0, prior_value=152.0),
            card("b", "Payments", -8.0, fmt="currency", value=5994.0, prior_value=6320.0),
            card("c", "Bills", 200.0, value=3.0, prior_value=1.0)]}
        self.assertEqual(brief(summary), "In the last 30 days, payments fell 8% against the 30 days before. "
                                         "Billed revenue and bills had too little activity to compare.")

    def test_several_big_moves_are_listed_together(self):
        summary = {"period": self.PERIOD, "kpis": [card("a", "Bills", 40.0), card("b", "Payments", -25.0),
                                                   card("c", "Field activities", 16.0)]}
        self.assertEqual(brief(summary), "In the last 30 days to Jun 18, 2026, bills rose 40%, payments fell 25% "
                                         "and field activities rose 16% against the 30 days before.")


class RouteTests(unittest.TestCase):
    def _ctx(self, rules=(), workstreams=("*",)):
        from api.auth.dependencies import AuthContext
        return AuthContext(id="u", email="u@x.gov", display_name="u", role="editor", client_id="demo25",
                           organization_id="demo25", organization_name="Demo", permissions={"snapshots:read"},
                           workstreams=list(workstreams), row_rules=tuple(rules))

    def test_trends_follow_workstream_grants_and_refuse_restricted_readers(self):
        from api import ori_routes
        hist = {"billed_revenue": series(BASE12 + [153]), "bills_completed": series([100] * 12 + [130])}
        meta = {"billed_revenue": {"label": "Billed revenue", "format": "currency", "workstream": "billing"},
                "bills_completed": {"label": "Bills", "format": "number", "workstream": "operations"}}
        with mock.patch.object(ori_routes, "require_org_for_data", return_value="demo25"), \
             mock.patch.object(ori_routes, "cached_history", return_value=(hist, meta)):
            both = ori_routes.ori_trends(ctx=self._ctx())
            billing = ori_routes.ori_trends(ctx=self._ctx(workstreams=("billing",)))
            unlisted = ori_routes.ori_trends(ctx=self._ctx(workstreams=()))
            restricted = ori_routes.ori_trends(ctx=self._ctx(rules=({"field": "Service Type", "values": ["W"]},)))
        self.assertEqual({a["kpi_id"] for a in both["anomalies"]}, {"billed_revenue", "bills_completed"})
        self.assertEqual(both["through"], "2024-06")
        self.assertEqual([a["kpi_id"] for a in billing["anomalies"]], ["billed_revenue"])
        self.assertEqual(unlisted["anomalies"], both["anomalies"])
        self.assertEqual(restricted, {"anomalies": [], "forecasts": [], "through": None})

    def test_findings_carry_ori_s_read(self):
        from api import ori_routes
        summary = {"period": {"label": "Last 30 days", "days": 30}, "kpis": [card("a", "Bills", 1.0)]}
        with mock.patch.object(ori_routes, "require_org_for_data", return_value="demo25"), \
             mock.patch("api.snapshot_explorer.cached_home_summary", return_value=summary):
            out = ori_routes.ori_findings(ctx=self._ctx())
        self.assertEqual(out["brief"], "In the last 30 days, bills held within 5% of the 30 days before.")


class HistoryKeepTests(unittest.TestCase):
    def test_a_history_missing_a_failed_card_is_not_kept(self):
        # review 2026-09-29: one card timing out left it without projections until the next build
        from api import summary_cache
        summary_cache.clear()
        kpis = [{"id": "a", "label": "A", "format": "number", "workstream": "billing"},
                {"id": "b", "label": "B", "format": "number", "workstream": "billing"}]
        calls = {"n": 0}

        def history(kpi, org):
            calls["n"] += 1
            if kpi["id"] == "b" and calls["n"] <= 2:
                raise RuntimeError("DPY-4024: call timeout")
            return series([100] * 13)
        with mock.patch("api.executive_dashboard.available_kpis", return_value=(kpis, None)), \
             mock.patch.object(ori_series, "monthly_history", side_effect=history), \
             mock.patch.object(ori_series, "data_version", return_value="V1"):
            first, _ = ori_series.cached_history("ellensburg")
            second, _ = ori_series.cached_history("ellensburg")
        self.assertEqual(set(first), {"a"})
        self.assertEqual(set(second), {"a", "b"})


class WarmTests(unittest.TestCase):
    def test_the_warmer_builds_the_monthly_history_after_a_rebuild(self):
        from api import cache_warmer as cw
        cw.reset()
        with mock.patch.object(cw, "data_version", return_value="V1"), \
             mock.patch.object(cw, "_workstreams", return_value=[]), \
             mock.patch.object(cw, "_opening_reports", return_value=[]), \
             mock.patch("api.snapshot_explorer.cached_home_summary", return_value={"kpis": []}), \
             mock.patch("api.dq_routes.warm"), \
             mock.patch.object(ori_series, "cached_history", return_value=({}, {})) as history:
            built = cw.warm_once("demo25")
        self.assertIn("ori trends", built)
        history.assert_called_once_with("demo25")


if __name__ == "__main__":
    unittest.main()
