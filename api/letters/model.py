"""One printable letter and the process facts behind it.

A letter is a customer contact C2M created with Print Letter = Y (a collection, severance or
write-off "send letter" event, or an NSF contact), or a frozen late payment charge adjustment.
Letter ids are "CC-<cc_id>" and "ADJ-<adj_id>".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class Kind(str, Enum):
    """The letters C2M's credit & collections, write-off and payment processes send."""
    REMINDER = "reminder"
    DEPOSIT = "deposit"
    PAYMENT_PLAN = "payment_plan"
    CASH_ONLY = "cash_only"
    AUTOPAY_ENDED = "autopay_ended"
    LIEN = "lien"
    DISCONNECT = "disconnect"
    # Derived, never configured: a severance letter whose process has already completed its cut.
    DISCONNECTED = "disconnected"
    FINAL_NOTICE = "final_notice"
    NSF = "nsf"
    LATE_FEE = "late_fee"
    GENERIC = "generic"
    NOT_A_LETTER = "not_a_letter"

    @property
    def label(self) -> str:
        return _LABELS[self]


_LABELS = {
    Kind.REMINDER: "Past due reminder", Kind.DEPOSIT: "Deposit request", Kind.PAYMENT_PLAN: "Payment plan notice",
    Kind.CASH_ONLY: "Cash-only notice", Kind.AUTOPAY_ENDED: "Automatic payment cancelled",
    Kind.LIEN: "Lien or tax roll notice", Kind.DISCONNECT: "Disconnection notice",
    Kind.DISCONNECTED: "Service disconnected", Kind.FINAL_NOTICE: "Final notice", Kind.NSF: "Returned payment",
    Kind.LATE_FEE: "Late payment charge", Kind.GENERIC: "Collections letter", Kind.NOT_A_LETTER: "Not a letter",
}


@dataclass(frozen=True)
class MailingAddress:
    """The recipient block as C2M resolves it (person or mailing premise)."""
    name1: str = ""
    name2: str = ""
    name3: str = ""
    address1: str = ""
    address2: str = ""
    address3: str = ""
    address4: str = ""
    city: str = ""
    state: str = ""
    postal: str = ""
    country: str = ""

    def lines(self) -> tuple[str, ...]:
        city = f"{self.city}{', ' + self.state if self.state else ''} {self.postal}".strip()
        return tuple(s.strip() for s in (self.name1, self.name2, self.name3, self.address1, self.address2,
                                         self.address3, self.address4, city) if s and s.strip() and s.strip() != ",")


@dataclass(frozen=True)
class DebtService:
    sa_id: str
    service_type: str
    premise_address: str
    amount: Decimal


@dataclass(frozen=True)
class Debt:
    """The collection / severance / write-off process behind a letter and the dates its own events
    announce: the next action still ahead, and (severance) when service is scheduled to be cut or
    was actually cut."""
    process_type: str
    process_id: str
    template_code: str
    arrears_amount: Decimal
    arrears_as_of: date | None
    next_action_on: date | None
    next_action_type: str
    cut_scheduled_on: date | None
    cut_completed_on: date | None
    services: tuple[DebtService, ...]


@dataclass(frozen=True)
class ReturnedPayment:
    """CI_CC_CHAR C1-ADJ -> the NSF fee adjustment -> the cancelled tender."""
    adjustment_id: str
    fee_amount: Decimal
    payment_date: date | None
    payment_amount: Decimal | None
    tender_type: str


@dataclass(frozen=True)
class LateFee:
    adjustment_id: str
    amount: Decimal
    charged_on: date
    sa_id: str
    service_type: str
    premise_address: str


@dataclass(frozen=True)
class Letter:
    letter_id: str
    cc_id: str | None
    kind: Kind
    template_code: str
    contact_type: str
    contact_type_description: str
    letter_date: date
    created_at: datetime
    account_id: str
    person_id: str
    customer_name: str
    mailing_address: MailingAddress
    copies: int
    body: str
    printed_at: datetime | None
    account_balance: Decimal
    debt: Debt | None = None
    returned_payment: ReturnedPayment | None = None
    late_fee: LateFee | None = None
    imb: str | None = None      # the 31-digit Intelligent Mail barcode, once a mailer has assigned one
