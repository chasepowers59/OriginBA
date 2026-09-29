"""The words on each kind of letter. Ported from the letter-print app's LetterComposerTest,
with synthetic letters (tests/letters_fixtures.py) and demo25's words from config/letters.yml."""
from __future__ import annotations

import dataclasses
import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import letters_fixtures as fx  # noqa: E402
from api.letters.catalog import catalog  # noqa: E402
from api.letters.composer import compose, salutation  # noqa: E402
from api.letters.model import Debt, Kind  # noqa: E402

DEMO = catalog().words("demo25")
NOWHERE = catalog().words("nowhere")


def text(c) -> str:
    return "\n".join(c.paragraphs)


def row(c, label: str, value: str) -> bool:
    return (label, value) in c.glance


class ComposerTests(unittest.TestCase):
    def test_a_reminder_names_the_past_due_amount_its_as_of_date_and_the_pay_by_date(self):
        c = compose(fx.reminder(), DEMO)
        self.assertEqual(c.salutation, "Dear Alex Rivera,")
        self.assertEqual(c.subject, "Reminder: your account is past due")
        t = text(c)
        for part in ("$132.69", "February 27, 2028", "March 18, 2028"):
            self.assertIn(part, t)
        self.assertEqual(c.callout, "Please pay $132.69 by March 18, 2028.")
        self.assertEqual(c.glance_label, "Amount past due")
        self.assertEqual(c.glance_amount, Decimal("132.69"))
        self.assertTrue(row(c, "Pay by", "March 18, 2028") and row(c, "Account balance", "$187.45"), c.glance)
        self.assertEqual(c.services_title, "Services with a past due balance")
        self.assertEqual(c.stub_date, "March 18, 2028")

    def test_a_disconnection_notice_names_the_service_the_premise_the_cut_off_date_and_the_fee(self):
        c = compose(fx.disconnect(), DEMO)
        self.assertEqual(c.subject, "NOTICE OF DISCONNECTION FOR NON-PAYMENT")
        t = text(c)
        for part in ("Water Residential (monthly)", fx.STREET, "$84.87", "on or after March 18, 2028", "$35.00"):
            self.assertIn(part, t)
        self.assertIn("payment arrangement", t.lower(), "the statutory offer of a payment plan")
        self.assertEqual(c.callout, "To keep your service on, pay $84.87 before March 18, 2028.")
        self.assertTrue(row(c, "Disconnection on or after", "March 18, 2028") and row(c, "Reconnection fee", "$35.00"))

    def test_without_a_scheduled_event_the_grace_period_decides_and_a_zero_fee_is_left_out(self):
        d = fx.disconnect()
        no_date = dataclasses.replace(d, debt=Debt("Severance", "1", "SEV-STD", d.debt.arrears_amount,
                                                   d.debt.arrears_as_of, None, "", None, None, d.debt.services))
        c = compose(no_date, NOWHERE)
        self.assertIn("on or after March 18, 2028", text(c), "letter date + 10 grace days")
        self.assertNotIn("reconnection fee", text(c))
        self.assertEqual(c.ways, (), "a client with no words configured gets no ways-to-pay block")
        self.assertEqual(c.notes, ())

    def test_a_reminder_without_a_process_speaks_about_the_balance_as_of_the_letter_date(self):
        orphan = dataclasses.replace(fx.reminder(), debt=None, customer_name="Overland, Inc.")
        c = compose(orphan, DEMO)
        self.assertEqual(c.salutation, "Dear Overland, Inc.,")
        self.assertIn("$187.45", text(c))
        self.assertIn("March 8, 2028", text(c))
        self.assertEqual(c.callout, "Please pay $187.45 now.")
        self.assertNotIn("listed below", text(c), "no process, no services table: nothing is listed")
        self.assertNotIn("the date above", text(c), "and no date was given")

    def test_a_letter_after_the_cut_says_service_was_disconnected_and_what_restores_it(self):
        c = compose(fx.disconnected(), DEMO)
        self.assertEqual(c.subject, "IMPORTANT: your service has been disconnected")
        t = text(c)
        self.assertIn("was disconnected on March 6, 2028", t)
        self.assertIn("$84.87", t)
        self.assertIn("$35.00", t)
        self.assertIn("closed on March 20, 2028", t, "the next severance event is the account closure")
        self.assertEqual(c.callout, "To restore your service, pay $84.87 now.")
        self.assertEqual(c.glance_label, "Amount to restore service")
        self.assertTrue(row(c, "Disconnected on", "March 6, 2028"))
        self.assertEqual(c.stub_date, "", "a restore letter asks for payment now, not by a date")

    def test_a_final_notice_warns_of_the_agency_referral_date(self):
        c = compose(fx.final_notice(), DEMO)
        t = text(c)
        self.assertIn("$212.40", t)
        self.assertIn("March 22, 2028", t)
        self.assertIn("collection agency", t.lower())
        self.assertEqual(c.callout, "Pay $212.40 by March 22, 2028 to avoid referral to a collection agency.")

    def test_an_nsf_letter_names_the_returned_payment_the_fee_and_the_amount_to_replace(self):
        c = compose(fx.nsf(), DEMO)
        self.assertEqual(c.subject, "Your payment was returned by your bank")
        t = text(c)
        for part in ("$598.45", "March 1, 2028", "(check)", "$20.00", "$187.45"):
            self.assertIn(part, t)
        self.assertEqual(c.glance_label, "Amount to replace")
        self.assertEqual(c.glance_amount, Decimal("618.45"), "payment + fee")
        self.assertEqual(c.stub_date, "")

    def test_a_late_fee_letter_names_the_charge_the_service_and_the_date(self):
        c = compose(fx.late_fee(), DEMO)
        t = text(c)
        for part in ("$10.88", "Electric Residential", "March 8, 2028"):
            self.assertIn(part, t)
        self.assertTrue(row(c, "Charged on", "March 8, 2028"))
        self.assertEqual(c.stub_amount, Decimal("187.45"), "the stub asks for the balance, not the fee")

    def test_the_payment_plan_cash_only_and_autopay_letters_say_what_changed(self):
        plan = compose(fx.as_kind(fx.reminder(), Kind.PAYMENT_PLAN), DEMO)
        self.assertEqual(plan.subject, "Your payment plan is past due")
        self.assertIn("$132.69", text(plan))
        self.assertIn("cancelled", text(plan).lower())
        cash = compose(fx.as_kind(fx.reminder(), Kind.CASH_ONLY), DEMO)
        self.assertIn("cashier's check", text(cash))
        self.assertIn("$187.45", text(cash))
        apay = compose(fx.as_kind(fx.reminder(), Kind.AUTOPAY_ENDED), DEMO)
        self.assertEqual(apay.subject, "Your automatic payment has been cancelled")
        self.assertIn("returned unpaid", text(apay))

    def test_a_lien_letter_says_what_happens_to_the_property_in_the_client_s_words(self):
        c = compose(fx.as_kind(fx.final_notice(), Kind.LIEN), DEMO)
        self.assertEqual(c.subject, "Unpaid balance to be certified against the property")
        self.assertIn("$212.40", text(c))
        self.assertIn("recorded as a lien against the property on March 22, 2028", text(c))

    def test_an_unknown_collections_template_prints_the_contact_text(self):
        g = compose(fx.generic(), DEMO)
        self.assertEqual(g.subject, "Collections letter")
        self.assertIn("promise to pay", text(g))
        self.assertIn("$187.45", text(g), "the account balance is always stated")
        self.assertEqual(g.callout, "")

    def test_the_client_words_become_the_ways_to_pay_the_notes_and_the_signature_block(self):
        c = compose(fx.reminder(), DEMO)
        self.assertEqual(len(c.ways), 4, c.ways)
        self.assertTrue(c.ways[0].startswith("Online, any time: https://pay.example.org"))
        self.assertIn("payable to Demo Utility", c.ways[2])
        self.assertIn("PO Box 1000", c.ways[2])
        self.assertEqual(len(c.notes), 3)
        self.assertEqual(c.closing, "Sincerely,\n\nCustomer Accounts Team\nCredit & Collections")

    def test_no_letter_points_at_a_date_it_does_not_give(self):
        for letter in fx.every_kind():
            if letter.debt is None:
                continue
            undated = dataclasses.replace(letter, debt=dataclasses.replace(letter.debt, next_action_on=None))
            with self.subTest(kind=letter.kind):
                t = text(compose(undated, DEMO))
                self.assertNotIn("the date above", t)
                self.assertNotIn("that date", t)

    def test_every_kind_composes(self):
        for letter in fx.every_kind():
            with self.subTest(kind=letter.kind):
                c = compose(letter, DEMO)
                self.assertTrue(c.subject)
                self.assertTrue(c.paragraphs)


class SalutationTests(unittest.TestCase):
    def test_c2m_last_comma_first_becomes_a_name_and_businesses_are_left_alone(self):
        self.assertEqual(salutation("Walker,Peter"), "Dear Peter Walker,")
        self.assertEqual(salutation("Brazil,Mark S"), "Dear Mark S Brazil,")
        self.assertEqual(salutation("Overland, Inc."), "Dear Overland, Inc.,")
        self.assertEqual(salutation("Piggly Wiggly"), "Dear Piggly Wiggly,")
        self.assertEqual(salutation(""), "Dear Customer,")
        self.assertEqual(salutation(None), "Dear Customer,")


if __name__ == "__main__":
    unittest.main()
