"""The Data Quality headline must count findings, not the display cap.

Each rule's rows are capped at ROW_CAP for the response payload, and `count` was set to
the CAPPED length -- then the "Act now" headline summed those. Measured on Demo 25.4:
588 devices never registered at the head-end and 867 future-dated bills, so the real
act-now backlog is 1,455. The page said 200: two rules pinned at the cap of 100.

A worklist that under-reports itself by 7x is worse than one that reports nothing, since
"200 to work through" reads as a manageable afternoon. The cap is a payload limit and
belongs to the rows; the count belongs to the finding.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.dq_routes import summarise_counts  # noqa: E402


def rule(severity: str, total: int, shown: int) -> dict:
    return {"severity": severity, "total": total, "count": shown}


class TestHeadlineCounts:
    def test_counts_every_finding_not_only_the_shown_rows(self) -> None:
        rules = [rule("action", 588, 100), rule("action", 867, 100)]
        assert summarise_counts(rules)["act_now"] == 1455

    def test_review_is_counted_the_same_way(self) -> None:
        rules = [rule("review", 300, 100), rule("action", 5, 5)]
        summary = summarise_counts(rules)
        assert summary["review"] == 300
        assert summary["act_now"] == 5

    def test_info_severity_is_in_neither_headline(self) -> None:
        summary = summarise_counts([rule("info", 40, 40)])
        assert summary["act_now"] == 0
        assert summary["review"] == 0

    def test_an_uncapped_rule_is_unchanged(self) -> None:
        assert summarise_counts([rule("action", 7, 7)])["act_now"] == 7

    def test_a_rule_that_errored_contributes_nothing(self) -> None:
        rules = [{"severity": "action", "error": "boom"}, rule("action", 3, 3)]
        assert summarise_counts(rules)["act_now"] == 3

    def test_falls_back_to_count_when_no_total_is_present(self) -> None:
        """Defensive: a rule shape without `total` must not silently score zero."""
        assert summarise_counts([{"severity": "action", "count": 9}])["act_now"] == 9


def test_the_route_no_longer_sums_the_capped_count() -> None:
    source = (ROOT / "api" / "dq_routes.py").read_text()
    assert 'sum(e["count"] for e in out if e.get("severity") == "action")' not in source
