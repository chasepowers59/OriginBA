"""A frozen copy's windows end where its data ends.

Ellensburg's TEST instance is a copy of production that stopped receiving activity: it bills
about 11,700 a month through May 2026, runs its last normal bill-cycle day on 18 June (1,764
bills on the 17th), and is quiet after that (2 bills in August, 1 in September; measured
2026-09-28 on ORIGINBA_REPORTING). Every "last N days" window ended at the wall clock, so the
home page read "Billed revenue, last 30 days: $268.20" -- true, and useless for a demo.

An organization may now declare `data_as_of` (ISO date) in portal_organizations.json. Every
relative window for that org ends there instead of today, and the payloads say so, so the
screen reads "30 days to 18 Jun 2026" rather than implying it is live. An org without the key
keeps ending at today: the default is the live behaviour, the anchor is an opt-in for copies.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api import reporting_dates  # noqa: E402


@pytest.fixture
def orgs(monkeypatch):
    table = {
        "frozen": {"id": "frozen", "data_as_of": "2026-06-18"},
        "live": {"id": "live"},
        "bad": {"id": "bad", "data_as_of": "not-a-date"},
    }
    monkeypatch.setattr(reporting_dates, "get_organization", lambda org_id: table.get(org_id))
    return table


class TestReportingToday:
    def test_a_frozen_org_ends_at_its_declared_date(self, orgs):
        assert reporting_dates.reporting_today("frozen") == date(2026, 6, 18)

    def test_a_live_org_ends_today(self, orgs):
        assert reporting_dates.reporting_today("live") == date.today()

    def test_no_org_ends_today(self, orgs):
        assert reporting_dates.reporting_today() == date.today()

    def test_an_unparseable_anchor_falls_back_to_today_rather_than_breaking_every_query(self, orgs):
        assert reporting_dates.reporting_today("bad") == date.today()

    def test_the_declared_anchor_is_reported_only_when_it_applies(self, orgs):
        assert reporting_dates.data_as_of("frozen") == "2026-06-18"
        assert reporting_dates.data_as_of("live") is None
        assert reporting_dates.data_as_of("bad") is None


class TestWindows:
    def test_the_shared_window_ends_at_the_anchor(self, orgs):
        assert reporting_dates.reporting_window(30, organization_id="frozen") == ("2026-05-19", "2026-06-18")

    def test_the_kpi_windows_end_at_the_anchor(self, orgs, monkeypatch):
        from api import kpi_runner
        monkeypatch.setattr(kpi_runner, "reporting_today", reporting_dates.reporting_today)
        (cs, ce), (ps, pe), _ = kpi_runner.date_windows(30, organization_id="frozen")
        assert (cs, ce) == ("2026-05-19", "2026-06-18")
        assert date.fromisoformat(pe) <= date.fromisoformat(cs)   # the prior window sits before the current one

    def test_the_kpi_windows_for_a_live_org_are_unchanged(self, orgs):
        from api import kpi_runner
        (_, ce), _, _ = kpi_runner.date_windows(30, organization_id="live")
        assert ce == date.today().isoformat()

    def test_the_nlq_window_ends_at_the_anchor(self, orgs):
        from api import nlq_metrics
        assert nlq_metrics._window(30, "frozen") == ("2026-05-19", "2026-06-18")


class TestTheRealRegistry:
    def test_ellensburg_declares_the_measured_anchor(self):
        from api.organizations import get_organization
        assert get_organization("ellensburg").get("data_as_of") == "2026-06-18"

    def test_an_anchor_is_never_in_the_future(self):
        from api.organizations import load_organizations
        for org in load_organizations():
            if org.get("data_as_of"):
                assert date.fromisoformat(org["data_as_of"]) <= date.today(), org["id"]


class TestTheAssistantKnows:
    def test_a_frozen_org_prompt_anchors_windows_on_its_date(self, orgs, monkeypatch):
        from api import assistant
        monkeypatch.setattr(assistant, "tool_list_canvases", lambda org_id, engine: [])
        head = assistant.system_prompt("frozen", "Frozen Town", "oracle")[0]["text"]
        # closed on both ends: the copy holds rows after its as-of, and ">= start" alone added
        # $601,089.26 of July billing to one cycle in the first demo run
        assert "BETWEEN DATE '2026-06-18' - 90 AND DATE '2026-06-18'" in head
        assert "bound BOTH ends" in head and "runs through 2026-06-18" in head
        assert "TRUNC(SYSDATE) - 90" not in head

    def test_a_live_org_prompt_is_unchanged(self, orgs, monkeypatch):
        from api import assistant
        monkeypatch.setattr(assistant, "tool_list_canvases", lambda org_id, engine: [])
        head = assistant.system_prompt("live", "Live Town", "oracle")[0]["text"]
        assert ">= TRUNC(SYSDATE) - 90" in head and "runs through" not in head
