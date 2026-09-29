"""The letter PDF: one page per letter, the address in the #10 window, the IMb golden.

Laid out from the letter-print app's templates/letter.jrxml (JRXML coordinates are points,
as are reportlab's). Geometry is asserted on the layout, not by parsing the PDF, so a test
can say exactly which element strayed into the window.
"""
from __future__ import annotations

import dataclasses
import json
import re
import shutil
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

import reportlab

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import letters_fixtures as fx  # noqa: E402
from api.letters import render  # noqa: E402
from api.letters.catalog import catalog  # noqa: E402
from api.letters.model import DebtService  # noqa: E402

DEMO = catalog().words("demo25")
IMB = "01234567094987654321" + "01234567891"      # USPS-B-3200's example: tracking + routing


def pages(pdf: bytes) -> int:
    return len(re.findall(rb"/Type\s*/Page\b(?!s)", pdf))


def crowded():
    """Everything at once: a long agent note, a dozen services, a five-line address and an IMb."""
    services = tuple(DebtService(f"50000001{i:02d}", "Water Residential (monthly)", "100 Example Avenue",
                                 Decimal("10.00")) for i in range(12))
    d = fx.reminder()
    return dataclasses.replace(
        d, body="Customer called about the balance. " * 60, imb=IMB,
        debt=dataclasses.replace(d.debt, services=services),
        mailing_address=dataclasses.replace(d.mailing_address, name2="Attn Accounts Payable",
                                            address3="Building 2"))


class PdfTests(unittest.TestCase):
    def test_a_pdf_per_letter_of_exactly_one_page(self):
        for letter in fx.every_kind() + [crowded()]:
            with self.subTest(kind=letter.kind, letter=letter.letter_id):
                out = render.render_letters([letter], DEMO, "Demo Utility")
                self.assertTrue(out.pdf.startswith(b"%PDF-"))
                self.assertEqual((out.pages, pages(out.pdf)), (1, 1))

    def test_a_batch_is_one_page_per_letter_in_the_callers_order(self):
        letters = fx.every_kind()
        out = render.render_letters(letters, DEMO, "Demo Utility")
        self.assertEqual((out.pages, pages(out.pdf)), (len(letters), len(letters)))

    def test_the_font_is_named_and_a_fallback_says_so(self):
        out = render.render_letters([fx.reminder()], DEMO, "Demo Utility")
        self.assertIn(out.font, ("DejaVu Sans", "Helvetica"))
        self.assertEqual(out.note is None, out.font == "DejaVu Sans")


class LayoutTests(unittest.TestCase):
    def test_the_address_block_and_the_imb_sit_inside_the_10_window(self):
        for letter in fx.every_kind() + [crowded()]:
            with self.subTest(letter=letter.letter_id, kind=letter.kind):
                placed = render.layout(dataclasses.replace(letter, imb=IMB), DEMO, "Demo Utility")
                for role in ("address", "imb"):
                    box = placed.box(role)
                    self.assertTrue(box.inside(render.ADDRESS_ZONE), f"{role} {box} outside {render.ADDRESS_ZONE}")

    def test_nothing_but_the_addressing_shows_through_the_window(self):
        """The at-a-glance box names the amount owed: it must never show through the envelope."""
        for letter in fx.every_kind() + [crowded()]:
            with self.subTest(letter=letter.letter_id, kind=letter.kind):
                placed = render.layout(dataclasses.replace(letter, imb=IMB), DEMO, "Demo Utility")
                seen = {i.role for i in placed.items if i.box.overlaps(render.WINDOW)}
                self.assertLessEqual(seen, {"return_address", "address", "imb"})

    def test_the_body_never_runs_into_the_remittance_stub(self):
        for letter in fx.every_kind() + [crowded()]:
            with self.subTest(letter=letter.letter_id, kind=letter.kind):
                placed = render.layout(letter, DEMO, "Demo Utility")
                body = [i.box.bottom for i in placed.items if i.role == "body"]
                self.assertTrue(body)
                self.assertLessEqual(max(body), render.STUB_TOP)

    def test_the_specimen_carries_no_client_s_strings(self):
        """Only the demo's own words are configured: no real client name may be baked into the layout."""
        orgs = json.loads((ROOT / "config" / "portal_organizations.json").read_text())
        orgs = orgs if isinstance(orgs, list) else orgs.get("organizations", [])
        names = {o["display_name"].lower() for o in orgs if o.get("engine") == "oracle" and o["id"] != "demo"}
        self.assertTrue(names)
        for letter in fx.every_kind():
            text = " ".join(i.text for i in render.layout(letter, DEMO, "Demo Utility").items if i.text).lower()
            for name in names:
                self.assertNotIn(name, text)


class ImbTests(unittest.TestCase):
    def test_the_usps_b_3200_golden(self):
        self.assertEqual(render.imb_bars("01234567094987654321", "01234567891"),
                         "AADTFFDFTDADTAADAATFDTDDAAADDTDTTDAFADADDDTFFFDDTTTADFAAADFTDAADA")

    def test_thirty_one_digits_is_the_only_valid_shape(self):
        self.assertTrue(render.valid_imb(IMB))
        for bad in (IMB[:-1], IMB + "3", IMB[:5] + "O" + IMB[6:], None, "09" + IMB[2:]):
            with self.subTest(code=bad):
                self.assertFalse(render.valid_imb(bad))


class FontTests(unittest.TestCase):
    def test_dejavu_sans_when_present_else_helvetica_with_a_note(self):
        vera = Path(reportlab.__file__).parent / "fonts"
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copy(vera / "Vera.ttf", Path(tmp) / "DejaVuSans.ttf")      # a metric stand-in: DejaVu grew from Vera
            shutil.copy(vera / "VeraBd.ttf", Path(tmp) / "DejaVuSans-Bold.ttf")
            found = render.resolve_font((Path(tmp),))
            self.assertEqual((found.name, found.note), ("DejaVu Sans", None))
            out = render.render_letters([fx.reminder()], DEMO, "Demo Utility", font=found)
            self.assertEqual(out.pages, 1)
        missing = render.resolve_font((Path(tmp) / "nowhere",))
        self.assertEqual(missing.name, "Helvetica")
        self.assertIn("DejaVu Sans", missing.note)


if __name__ == "__main__":
    unittest.main()
