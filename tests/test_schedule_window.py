"""A scheduled report must apply the window its own email claims.

`_build_sql` took its date field from `required_date_field` alone. No dbt canvas sets one
-- it is a CISADM-era notion for snapshots too large to scan unfiltered -- so on every
canvas-backed org the date filter was simply never added: the user picked "trailing 30
days" in the schedule dialog and received the whole table.

The email made it worse by asserting the window anyway: "Data window: trailing 30 days as
of <date>". A report that quietly widens its own scope is bad; one that widens it and
then states the narrow scope in writing is how a number ends up in a board pack wrong.

Same fallback the KPI runner and NLQ metrics already use, and the email now describes
what was actually applied.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.report_schedules import schedule_date_field, window_sentence  # noqa: E402


class TestScheduleDateField:
    def test_windows_on_the_canvas_default(self):
        """Every canvas with a date declares a MEASURED default; that is the window."""
        assert schedule_date_field({"default_date_field": "Accounting Date"}) == "Accounting Date"

    def test_returns_none_when_the_canvas_genuinely_has_no_date(self):
        assert schedule_date_field({"default_date_field": None}) is None
        assert schedule_date_field({}) is None


class TestWindowSentence:
    def test_states_the_window_that_was_applied(self):
        assert "trailing 30 days" in window_sentence("Accounting Date", 30, "2026-09-01")

    def test_names_the_field_so_the_reader_knows_which_date_was_windowed(self):
        # "trailing 30 days" is ambiguous on a canvas with eight date columns.
        assert "Accounting Date" in window_sentence("Accounting Date", 30, "2026-09-01")

    def test_says_plainly_when_no_window_could_be_applied(self):
        sentence = window_sentence(None, 30, "2026-09-01")
        assert "trailing" not in sentence
        assert "all" in sentence.lower()


def test_the_builder_no_longer_reads_required_date_field_alone():
    """Guard the regression: the fallback must stay in the SQL path, not just the email."""
    source = (ROOT / "api" / "report_schedules.py").read_text()
    assert 'date_field = snapshot.get("required_date_field")' not in source
