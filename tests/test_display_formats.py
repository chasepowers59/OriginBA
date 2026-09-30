"""UI-16: the words the server writes for a reader use the portal's formats.

Dates read "Sep 1, 2026" (never "1 Sep 2026"), and negative money reads "-$12,071.26"
(never "$-12,071.26"), the same as apps/analytics-portal/src/lib/format.ts.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.nlq_metrics import _fmt  # noqa: E402
from api.ori_insights import _amount  # noqa: E402
from api.report_schedules import window_sentence  # noqa: E402


def test_the_emailed_window_names_its_date_like_the_portal():
    assert window_sentence("Accounting Date", 30, "2026-09-01").endswith("as of Sep 1, 2026.")


def test_negative_money_puts_the_sign_before_the_dollar():
    assert _fmt(-12071.26, "currency") == "-$12,071.26"
    assert _amount(-12071.26, "currency") == "-$12,071.26"
    assert _amount(1234.5, "currency") == "$1,234.50"


def test_no_reader_facing_date_is_written_day_first():
    """The letters keep their own house style (a customer letter, not the portal)."""
    day_first = re.compile(r"%-?d %b")
    offenders = [str(p.relative_to(ROOT)) for p in (ROOT / "api").rglob("*.py")
                 if "letters" not in p.parts and day_first.search(p.read_text())]
    assert offenders == []
