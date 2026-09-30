"""The words on each kind of letter.

CISADM stores no letter text (CI_LETTER_TMPL points at an extract algorithm; the wording lives
with the print vendor), so the body is composed here from what the process knows, in the shape
state disconnection rules require: the amount, its as-of date, the date something happens, what
it costs to undo, how to pay, how to get help, and how to reach the utility. The contact's own
text (DESCRLONG), when an agent wrote one, is appended to the body.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from api.letters.catalog import Words
from api.letters.model import Debt, DebtService, Kind, Letter

_BUSINESS = re.compile(r"(?i)\b(inc|llc|llp|ltd|corp|co|company|corporation|trust|estate|dba|assoc|association|"
                       r"church|school|district|city|county|partners|group|properties|apartments|hoa)\b")


@dataclass(frozen=True)
class Composed:
    """subject: the bold line under the salutation. callout: the one sentence that matters, set in a
    box. glance: the at-a-glance box (headline amount and its label, then (label, value) rows).
    ways: the "Ways to pay" lines. notes: the small print. stub_*: the remittance stub."""
    salutation: str
    subject: str
    paragraphs: tuple[str, ...]
    callout: str
    glance_label: str
    glance_amount: Decimal
    glance: tuple[tuple[str, str], ...]
    services_title: str
    ways: tuple[str, ...]
    notes: tuple[str, ...]
    closing: str
    stub_amount: Decimal
    stub_date: str


def money(amount: Decimal | None) -> str:
    return f"${amount if amount is not None else Decimal('0'):,.2f}"


def fmt(d: date | None) -> str:
    return f"{d:%B} {d.day}, {d.year}" if d else ""


def by(d: date | None) -> str:
    return f" by {fmt(d)}" if d else ""


def salutation(name: str | None) -> str:
    """C2M stores person names as LAST,FIRST; a business name has no such split."""
    n = (name or "").strip()
    if not n:
        return "Dear Customer,"
    last, comma, first = n.partition(",")
    last, first = last.strip(), first.strip()
    if comma and last and first and not _BUSINESS.search(first) and not _BUSINESS.search(last):
        return f"Dear {first} {last},"
    return f"Dear {n},"


def ways(w: Words) -> tuple[str, ...]:
    out = []
    if w.payment_url:
        out.append(f"Online, any time: {w.payment_url}")
    if w.contact_phone:
        out.append(f"By phone: {w.contact_phone}" + (f", {w.office_hours}" if w.office_hours else ""))
    remit = w.remit_address or w.utility_address
    if remit:
        out.append("By mail: send the stub below with a check or money order"
                   + (f" payable to {w.payee}" if w.payee else "") + f" to {', '.join(remit)}.")
    if w.utility_address:
        out.append(f"In person: {', '.join(w.utility_address)}" + (f", {w.office_hours}" if w.office_hours else ""))
    return tuple(out)


def _service_phrase(s: DebtService | None) -> str:
    if s is None:
        return "service"
    return f"{s.service_type} service" + (f" at {s.premise_address}" if s.premise_address else "")


def _debt_rows(g: list, debt: Debt, date_label: str | None) -> None:
    g.append(("Past due as of", fmt(debt.arrears_as_of)))
    if date_label and debt.next_action_on:
        g.append((date_label, fmt(debt.next_action_on)))


def compose(letter: Letter, w: Words) -> Composed:
    p: list[str] = []
    g: list[tuple[str, str]] = [("Account number", letter.account_id)]
    balance = letter.account_balance
    # A reminder raised outside a process (a batch overdue-bills letter, or a contact older than the
    # account's processes) speaks about the account balance as of the letter date instead.
    debt = letter.debt or Debt("Account", "", "", balance, letter.letter_date, None, "", None, None, ())
    first = debt.services[0] if debt.services else None
    arrears, as_of, nxt = money(debt.arrears_amount), fmt(debt.arrears_as_of), debt.next_action_on
    callout = services_title = ""
    stub_date: date | None = None
    kind = letter.kind

    if kind is Kind.REMINDER:
        subject, glance_label, glance_amount, stub_date = (
            "Reminder: your account is past due", "Amount past due", debt.arrears_amount, nxt)
        p.append(f"Our records show that your account has a past due balance of {arrears} as of {as_of}."
                 + (" The services and amounts are listed below." if debt.services else ""))
        p.append(f"Please pay this amount{by(nxt)} to avoid further collection activity. Continued non-payment may "
                 "lead to disconnection of service, a security deposit requirement and a charge to the credit "
                 "rating on your account.")
        p.append("If you have already paid, thank you, and please disregard this notice. If you cannot pay the full "
                 "amount, call us" + (" before the date above" if nxt else "")
                 + ": a payment arrangement may be available to you.")
        callout = f"Please pay {arrears}" + (f" by {fmt(nxt)}." if nxt else " now.")
        services_title = "Services with a past due balance"
        _debt_rows(g, debt, "Pay by")
    elif kind is Kind.DEPOSIT:
        subject, glance_label, glance_amount, stub_date = (
            "A security deposit is now required on your account", "Amount past due", debt.arrears_amount, nxt)
        p.append("Because of the payment history on your account, a security deposit is now required to continue "
                 f"service. Your account also has a past due balance of {arrears} as of {as_of}.")
        p.append(f"Please call us{by(nxt)} to arrange the deposit, or to discuss a payment arrangement for the past "
                 "due amount. The deposit is held on your account and refunded with interest after a period of "
                 "on-time payments.")
        callout = f"Call us{by(nxt)} to arrange your deposit."
        services_title = "Services with a past due balance"
        _debt_rows(g, debt, "Respond by")
    elif kind is Kind.PAYMENT_PLAN:
        subject, glance_label, glance_amount, stub_date = (
            "Your payment plan is past due", "Amount past due", debt.arrears_amount, nxt)
        p.append("A scheduled payment on your payment plan has not been received. Your account has a past due "
                 f"balance of {arrears} as of {as_of}.")
        p.append(f"Please bring the plan current{by(nxt)}. If a plan payment is missed, the plan may be cancelled, "
                 "the full balance becomes due at once, and normal collection activity resumes, which can include "
                 "disconnection of service.")
        p.append("If your circumstances have changed, call us" + (" before the date above" if nxt else "")
                 + ": we may be able to revise the plan.")
        callout = f"Please pay {arrears}{by(nxt)} to keep your plan."
        services_title = "Services on this plan"
        _debt_rows(g, debt, "Pay by")
    elif kind is Kind.CASH_ONLY:
        subject, glance_label, glance_amount = (
            "Your account is now on cash-only payment terms", "Account balance", balance)
        p.append("Because payments on your account have been returned unpaid, we can no longer accept personal "
                 "checks or automatic bank payments. Until further notice, please pay by cash, cashier's check, "
                 "money order or card.")
        p.append(f"Your account balance is {money(balance)}. Paying on time for a sustained period lets us restore "
                 "your usual payment options; call us to ask when your account qualifies.")
        callout = "Please pay by cash, cashier's check, money order or card."
    elif kind is Kind.AUTOPAY_ENDED:
        subject, glance_label, glance_amount = (
            "Your automatic payment has been cancelled", "Account balance", balance)
        p.append("Your automatic payment was cancelled because a payment was returned unpaid by your bank. Your bills "
                 f"will no longer be paid automatically, and your account balance is {money(balance)}.")
        p.append("Please pay each bill by its due date. Once your account is current you can enrol in automatic "
                 "payment again online or by phone; an unpaid balance may lead to collection activity, including "
                 "disconnection of service.")
        callout = f"Please pay {money(balance)} and pay future bills yourself until you re-enrol."
    elif kind is Kind.DISCONNECTED:
        subject, glance_label, glance_amount = (
            "IMPORTANT: your service has been disconnected", "Amount to restore service", debt.arrears_amount)
        fee = w.reconnect_fee > 0
        p.append(f"Your {_service_phrase(first)} was disconnected on {fmt(debt.cut_completed_on)} "
                 f"for non-payment of {arrears}.")
        p.append(f"To have service restored, pay the full amount of {arrears}"
                 + (f". A reconnection fee of {money(w.reconnect_fee)} will be added to your account" if fee else "")
                 + ", and a security deposit may be required. Service is normally restored on the next business "
                   "day after payment clears.")
        p.append("If the balance remains unpaid, your account "
                 + (f"is scheduled to be closed on {fmt(nxt)}" if nxt else "will be closed")
                 + " and the balance may be referred to a collection agency. If you cannot pay the full amount, call "
                   "us: a payment arrangement or an assistance program may let us restore your service sooner.")
        callout = f"To restore your service, pay {arrears} now."
        services_title = "Disconnected service"
        g += [("Disconnected on", fmt(debt.cut_completed_on)), ("Past due amount", arrears)]
        if fee:
            g.append(("Reconnection fee", money(w.reconnect_fee)))
    elif kind is Kind.DISCONNECT:
        cut_off = debt.cut_scheduled_on or nxt or letter.letter_date + timedelta(days=w.disconnect_grace_days)
        subject, glance_label, glance_amount, stub_date = (
            "NOTICE OF DISCONNECTION FOR NON-PAYMENT", "Amount to keep service on", debt.arrears_amount, cut_off)
        fee = w.reconnect_fee > 0
        p.append(f"Your {_service_phrase(first)} has a past due balance of {arrears} as of {as_of}, "
                 "and previous notices have not been answered.")
        p.append(f"Unless we receive payment of {arrears}, this service will be disconnected on or after "
                 f"{fmt(cut_off)}. Once service is disconnected, the full past due balance must be paid"
                 + (f", a reconnection fee of {money(w.reconnect_fee)} applies," if fee else "")
                 + " and a security deposit may be required before service is restored.")
        p.append(f"If you cannot pay the full amount, call us before {fmt(cut_off)}: a payment arrangement or an "
                 "assistance program may keep your service on. If you have already paid, thank you, and please "
                 "disregard this notice.")
        callout = f"To keep your service on, pay {arrears} before {fmt(cut_off)}."
        services_title = "Service subject to disconnection"
        _debt_rows(g, debt, None)
        g.append(("Disconnection on or after", fmt(cut_off)))
        if fee:
            g.append(("Reconnection fee", money(w.reconnect_fee)))
    elif kind is Kind.LIEN:
        subject, glance_label, glance_amount, stub_date = (
            "Unpaid balance to be certified against the property", "Unpaid balance", debt.arrears_amount, nxt)
        p.append(f"Your account has an unpaid balance of {arrears} as of {as_of}. Because it has not been paid, the "
                 f"balance is scheduled to be {w.lien_action}" + (f" on {fmt(nxt)}." if nxt else "."))
        p.append("Once that happens the balance is collected against the property itself, additional charges and "
                 "interest may be added, and the record is public, which can affect a sale or a refinance.")
        p.append(f"To prevent it, pay {arrears}{by(nxt)}. If you cannot pay in full, call us"
                 + (" before that date" if nxt else "") + ": an arrangement made in time can keep the balance off.")
        callout = f"Pay {arrears}{by(nxt)} to prevent this."
        services_title = "Services with an unpaid balance"
        _debt_rows(g, debt, "Pay by")
    elif kind is Kind.FINAL_NOTICE:
        subject, glance_label, glance_amount, stub_date = (
            "FINAL NOTICE before referral to a collection agency", "Unpaid balance", debt.arrears_amount, nxt)
        p.append(f"Despite previous notices, your account has an unpaid balance of {arrears}. This is our final "
                 "notice before the balance is referred for collection.")
        p.append(f"Unless payment in full is received{by(nxt)}, the balance will be referred to an outside collection "
                 "agency and may be reported to credit reporting agencies. Collection costs may be added to the "
                 "amount you owe, and future service may require a deposit.")
        p.append("To resolve this now, pay the balance in full or call us to discuss a payment arrangement. If you "
                 "have already paid, thank you, and please disregard this notice.")
        callout = f"Pay {arrears}{by(nxt)} to avoid referral to a collection agency."
        services_title = "Services with an unpaid balance"
        _debt_rows(g, debt, "Pay by")
    elif kind is Kind.NSF and letter.returned_payment is not None:
        r = letter.returned_payment
        replace = (r.payment_amount or Decimal("0")) + r.fee_amount
        subject, glance_label, glance_amount = ("Your payment was returned by your bank", "Amount to replace", replace)
        p.append("Your payment" + (f" of {money(r.payment_amount)}" if r.payment_amount is not None else "")
                 + (f" dated {fmt(r.payment_date)}" if r.payment_date else "")
                 + (f" ({r.tender_type.lower()})" if r.tender_type else "")
                 + " was returned unpaid by your bank. The payment has been reversed on your account"
                 + (f" and a returned payment fee of {money(r.fee_amount)} has been added" if r.fee_amount > 0 else "")
                 + f". Your account balance is now {money(balance)}.")
        p.append("Please replace the payment promptly with guaranteed funds: cash, a cashier's check, a money order, "
                 "or a card payment online or by phone. An unreplaced payment leaves the original amount past due "
                 "and may lead to collection activity, including disconnection of service.")
        callout = f"Please replace {money(replace)} with guaranteed funds now."
        if r.payment_amount is not None:
            g.append(("Returned payment", money(r.payment_amount)))
        if r.payment_date:
            g.append(("Payment date", fmt(r.payment_date)))
        g.append(("Returned payment fee", money(r.fee_amount)))
    elif kind is Kind.LATE_FEE and letter.late_fee is not None:
        f = letter.late_fee
        subject, glance_label, glance_amount = (
            "A late payment charge has been added to your account", "Late payment charge", f.amount)
        p.append(f"A late payment charge of {money(f.amount)} was added on {fmt(f.charged_on)} to your "
                 f"{f.service_type} service" + (f" at {f.premise_address}" if f.premise_address else "")
                 + " because payment was not received by the due date on your bill.")
        p.append("The charge will appear on your next bill. Paying each bill by its due date avoids further charges; "
                 "if you pay through automatic payment, the charge stops once the account is current. If you have "
                 "already paid, thank you.")
        callout = f"Your account balance is {money(balance)}."
        g.append(("Charged on", fmt(f.charged_on)))
    else:
        subject = letter.contact_type_description or kind.label
        glance_label, glance_amount = "Account balance", balance

    if letter.body.strip():
        p.append(letter.body.strip())
    if kind is Kind.GENERIC:
        p.append(f"Your account balance is {money(balance)}. Please contact us with any questions about your account.")
    g.append(("Account balance", money(balance)))
    closing = f"Sincerely,\n\n{w.signature}" + (f"\n{w.department}" if w.department else "")
    # The stub asks for what settles the matter: the process amount, the replacement for a returned
    # payment, else the balance.
    stub_amount = balance if kind in (Kind.LATE_FEE, Kind.GENERIC) else glance_amount
    return Composed(salutation(letter.customer_name), subject, tuple(p), callout, glance_label, glance_amount,
                    tuple(g), services_title, ways(w), w.notes, closing, stub_amount, fmt(stub_date))
