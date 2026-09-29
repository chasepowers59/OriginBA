"""Letter types from config/letters.yml: contact type first, then template, then description.

Ported from the letter-print app's LetterCatalogTest. Every code below is a real C2M code
(base-product CIR-* and the per-client customs read from the clients' own config); none of
it is customer data.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.letters.catalog import Catalog, catalog  # noqa: E402
from api.letters.model import Kind  # noqa: E402


class KindTests(unittest.TestCase):
    def setUp(self):
        self.c = catalog()

    def test_demo25_template_codes_resolve_to_their_kinds(self):
        c = self.c
        self.assertEqual(c.kind("CIR-REG-REM", "REG-REMINDER"), Kind.REMINDER)
        self.assertEqual(c.kind("CIR-OD-REM", "ODBIL-REMIND"), Kind.REMINDER)
        self.assertEqual(c.kind("CIR-DEP-REM", "DEP-REMINDER"), Kind.DEPOSIT)
        self.assertEqual(c.kind("CIR-SP-DISCN", "DISCONNECTED"), Kind.DISCONNECT)
        self.assertEqual(c.kind("CIR-AGY-WARN", "AGENCY-WARN"), Kind.FINAL_NOTICE)
        self.assertEqual(c.kind("CIR-NSF", "NSF"), Kind.NSF)
        self.assertEqual(c.kind("CIR-AUTOCALL", "AUTOCALL"), Kind.NOT_A_LETTER)

    def test_the_fleet_wide_standard_templates_all_classify(self):
        """The Origin standard set: every one of these is configured at all five 25.4 clients."""
        c = self.c
        for template, kind in [("CIR-LRG-REM", Kind.REMINDER), ("CIR-CHA-REM", Kind.REMINDER),
                               ("CIR-LS-REM", Kind.REMINDER), ("CIR-BUD-REM", Kind.PAYMENT_PLAN),
                               ("CIR-CASHONLY", Kind.CASH_ONLY), ("CIR-STAPYNSF", Kind.AUTOPAY_ENDED),
                               ("CIR-OD-DISC", Kind.DISCONNECT), ("BADDEBT2", Kind.FINAL_NOTICE),
                               ("CM-DELINQ", Kind.LIEN), ("TXRLLTR", Kind.LIEN), ("RTNCHECK", Kind.NSF),
                               ("SHUTOFFPOOR", Kind.DISCONNECT)]:
            with self.subTest(template=template):
                self.assertEqual(c.kind(template, "?"), kind)
        self.assertEqual(c.kind("CIR-SP-DISCN", "?"), Kind.DISCONNECT,
                         '"You have been disconnected": the data upgrades it, never the template')
        self.assertEqual(c.kind("CM04DOORTAG", "DOORTAG"), Kind.NOT_A_LETTER, "a door tag is hung, not mailed")

    def test_unknown_codes_fall_back_to_the_regexes_then_generic(self):
        c = self.c
        self.assertEqual(c.kind("ELL-SHUTOFF", "X"), Kind.DISCONNECT, "template code regex")
        self.assertEqual(c.kind("L-99", "FINAL-WARN"), Kind.FINAL_NOTICE, "contact type regex")
        self.assertEqual(c.kind("", "PAST-DUE-2"), Kind.REMINDER)
        self.assertEqual(c.kind("MISC-1", "MISC"), Kind.GENERIC)

    def test_the_contact_type_wins_over_a_stale_letter_template(self):
        """Ellensburg's own pairing: the contact type says what the utility means, the template is stale."""
        c = self.c
        self.assertEqual(c.kind("CM04-DELINQ", "DISCWARNING"), Kind.DISCONNECT,
                         "template says delinquency/lien, contact type says disconnect warning")
        self.assertEqual(c.kind("CM04-DELINQ", "SOMETHING-ELSE"), Kind.LIEN,
                         "with no contact type match the template decides, and this one is a lien letter")
        self.assertEqual(c.kind("CM04INA1NOTC", "FIRSTNOTICE"), Kind.REMINDER)
        self.assertEqual(c.kind("CM04INALNOTC", "LASTNOTICE"), Kind.FINAL_NOTICE)
        self.assertEqual(c.kind("CIR-STAPYNSF", "STOP-APAYNTC"), Kind.AUTOPAY_ENDED)

    def test_an_unlisted_code_classifies_from_the_contact_type_description(self):
        """What makes an unconfigured client work: every description below is a real one from
        the four Oracle 25.4 clients, and none of their codes is listed in letters.yml."""
        c = self.c
        for code, description, kind in [
            ("X1", "Shut Off Poor Pay Customer", Kind.DISCONNECT),
            ("X2", "Bad Debt Write Off Notification Letter", Kind.FINAL_NOTICE),
            ("X3", "Deposit Increase Warning", Kind.DEPOSIT),
            ("X4", "Return Check", Kind.NSF),
            ("X5", "Tax Roll Landlord Contact", Kind.LIEN),
            ("X6", "Late notice for active accounts", Kind.REMINDER),
            ("X7", "Last Notice - Inactive Account", Kind.FINAL_NOTICE),
            ("X8", "First Notice - Inactive Account", Kind.REMINDER),
            ("X9", "Budget Payment Plan Late Notice", Kind.PAYMENT_PLAN),
            ("XB", "Water Leak Notification", Kind.GENERIC),
            ("XC", "No Biller", Kind.GENERIC),
        ]:
            with self.subTest(description=description):
                self.assertEqual(c.kind(code, code, description), kind)
        self.assertEqual(c.kind("XA", "XA", "Autopay termination notice (NSF)"), Kind.AUTOPAY_ENDED,
                         "autopay is matched before NSF, or this reads as a returned payment")
        self.assertEqual(c.kind(None, None), Kind.GENERIC)

    def test_budget_activated_is_a_welcome_not_a_delinquency(self):
        """Regression: the bare word "budget" once swept "Non-billed budget activated" into
        payment_plan. A plan letter has to be about the plan going WRONG."""
        self.assertEqual(self.c.kind("CIR-NBB-PLAN", "NBB-ACTIV", "Non-billed budget activated"), Kind.GENERIC)
        self.assertFalse(self.c.is_letter(Kind.GENERIC, "BUD"), "and outside a collections class it is not a letter")

    def test_only_collection_class_contacts_are_letters_when_the_template_is_unknown(self):
        c = self.c
        self.assertTrue(c.is_letter(Kind.REMINDER, "GEN"), "a known collections kind is a letter whatever its class")
        self.assertTrue(c.is_letter(Kind.GENERIC, "C&C"))
        self.assertTrue(c.is_letter(Kind.GENERIC, " c&c "), "codes are trimmed and compared upper case")
        self.assertFalse(c.is_letter(Kind.GENERIC, "GEN"), "a welcome letter is not a collections letter")
        self.assertFalse(c.is_letter(Kind.NOT_A_LETTER, "C&C"))

    def test_cut_events_by_client_code_then_base_product_wording(self):
        c = self.c
        self.assertTrue(c.is_cut_event("CUT-NONPAY", "Disconnect service for non-payment"), "demo25's own code")
        self.assertTrue(c.is_cut_event("ELL-99", "Cut for non-payment"), "another client's code, base-product wording")
        self.assertFalse(c.is_cut_event("DISCON-WARN", "Disconnect warning"), "a warning is not the cut")
        self.assertFalse(c.is_cut_event("EXPIRE-SA", "Expire service agreement"))
        self.assertEqual(c.late_fee_adjustment_types, ("LPC",))


class WordsTests(unittest.TestCase):
    def test_client_words_override_the_defaults_and_unknown_clients_get_the_defaults(self):
        c = catalog()
        demo, other = c.words("demo25"), c.words("nowhere")
        self.assertEqual(demo.contact_phone, "(555) 555-0100")
        self.assertEqual(demo.reconnect_fee, Decimal("35.00"))
        self.assertEqual(demo.disconnect_grace_days, 10)
        self.assertEqual(other.contact_phone, "")
        self.assertEqual(other.reconnect_fee, Decimal("0"))
        self.assertEqual(other.signature, "Customer Service")
        self.assertEqual(demo.brand_color, "006FAC")
        self.assertEqual(demo.accent_or_brand, "006FAC", "no accent configured: the brand colour")
        self.assertEqual(demo.logo, "")

    def test_a_client_accent_and_a_bad_colour(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "letters.yml"
            path.write_text("clients:\n  sample:\n    brand_color: '#223b64'\n    accent_color: F20018\n")
            words = Catalog.load(path).words("sample")
            self.assertEqual((words.brand_color, words.accent_or_brand), ("223B64", "F20018"))
            path.write_text("clients:\n  sample:\n    brand_color: navy\n")
            with self.assertRaises(ValueError):
                Catalog.load(path).words("sample")

    def test_the_shipped_config_names_no_client_but_the_demo(self):
        """Phase 1 serves demo25 only; a real client's words arrive with its own phase."""
        self.assertEqual(set(catalog().clients), {"demo25"})


if __name__ == "__main__":
    unittest.main()
