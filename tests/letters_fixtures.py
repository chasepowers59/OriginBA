"""Synthetic letters for the letters tests: invented names, addresses and ids, never client data."""
from __future__ import annotations

import dataclasses
from datetime import date, datetime
from decimal import Decimal

from api.letters.model import (Debt, DebtService, Kind, LateFee, Letter, MailingAddress,
                               ReturnedPayment)

NAME = "Rivera,Alex"
STREET = "100 Example Avenue"
ADDRESS = MailingAddress(name1=NAME, address1=STREET, address2="Apt 4", city="Springfield",
                         state="IL", postal="62701", country="USA")
WATER = DebtService("5000000001", "Water Residential (monthly)", STREET, Decimal("84.87"))


def base(letter_id: str, kind: Kind, template: str, contact_type: str, *, body: str = "",
         debt: Debt | None = None, returned: ReturnedPayment | None = None,
         fee: LateFee | None = None) -> Letter:
    return Letter(
        letter_id=letter_id, cc_id=letter_id[3:] if letter_id.startswith("CC-") else None,
        kind=kind, template_code=template, contact_type=contact_type,
        contact_type_description=kind.label, letter_date=date(2028, 3, 8),
        created_at=datetime(2028, 3, 8, 6, 30), account_id="1000000001", person_id="2000000001",
        customer_name=NAME, mailing_address=ADDRESS, copies=1, body=body, printed_at=None,
        account_balance=Decimal("187.45"), debt=debt, returned_payment=returned, late_fee=fee)


def reminder() -> Letter:
    return base("CC-3000000001", Kind.REMINDER, "CIR-REG-REM", "REG-REMINDER", debt=Debt(
        "Collection", "4000000001", "NORMAL-DEBT", Decimal("132.69"), date(2028, 2, 27),
        date(2028, 3, 18), "Automated collections call", None, None,
        (DebtService("5000000002", "Gas Residential", STREET, Decimal("69.43")),
         DebtService("5000000003", "Water Residential (monthly)", STREET, Decimal("63.26")))))


def disconnect() -> Letter:
    """A warning: the cut is still ahead (a severance event pending)."""
    return base("CC-3000000002", Kind.DISCONNECT, "CIR-SP-DISCN", "DISCON-WARN", debt=Debt(
        "Severance", "4000000002", "SEV-STD", Decimal("84.87"), date(2028, 2, 27),
        date(2028, 3, 18), "Disconnect service for non-payment", date(2028, 3, 18), None, (WATER,)))


def disconnected() -> Letter:
    """The letter follows a COMPLETED cut, so the repository has upgraded it."""
    return base("CC-3000000003", Kind.DISCONNECTED, "CIR-SP-DISCN", "DISCONNECTED", debt=Debt(
        "Severance", "4000000002", "SEV-STD", Decimal("84.87"), date(2028, 2, 27),
        date(2028, 3, 20), "Expire service agreement", None, date(2028, 3, 6), (WATER,)))


def final_notice() -> Letter:
    return base("CC-3000000004", Kind.FINAL_NOTICE, "CIR-AGY-WARN", "AGENCY-WARN", debt=Debt(
        "Write-Off", "4000000003", "WO-STD", Decimal("212.40"), date(2028, 2, 27),
        date(2028, 3, 22), "Collection agency referral", None, None,
        (dataclasses.replace(WATER, amount=Decimal("212.40")),)))


def nsf() -> Letter:
    return base("CC-3000000005", Kind.NSF, "CIR-NSF", "NSF", returned=ReturnedPayment(
        "600000000001", Decimal("20.00"), date(2028, 3, 1), Decimal("598.45"), "Check"))


def late_fee() -> Letter:
    return base("ADJ-600000000002", Kind.LATE_FEE, "", "", fee=LateFee(
        "600000000002", Decimal("10.88"), date(2028, 3, 8), "5000000004", "Electric Residential", STREET))


def generic() -> Letter:
    return base("CC-2", Kind.GENERIC, "CIR-PROMISE", "PROMISE",
                body="Your promise to pay $80.00 by March 20 has been recorded.")


def as_kind(letter: Letter, kind: Kind) -> Letter:
    return dataclasses.replace(letter, kind=kind, contact_type_description=kind.label)


def every_kind() -> list[Letter]:
    return [reminder(), disconnect(), disconnected(), final_notice(), nsf(), late_fee(), generic(),
            as_kind(reminder(), Kind.DEPOSIT), as_kind(reminder(), Kind.PAYMENT_PLAN),
            as_kind(reminder(), Kind.CASH_ONLY), as_kind(reminder(), Kind.AUTOPAY_ENDED),
            as_kind(final_notice(), Kind.LIEN)]
