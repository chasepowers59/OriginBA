"""Letters from the raw CISADM tables: printable customer contacts (CI_CC) with the collection,
severance or write-off process behind each, the NSF contact's returned payment, and late payment
charge adjustments as letters of their own.

EVERY query is scoped by the same filter -- a contact-date window, or one CC_ID -- and fetched once
for the whole set rather than once per letter. Measured on Ellensburg: a month is 1,775 letters,
and the per-letter shape cost ~29s of database time and ~7,100 round trips against about 7s and 11
round trips batched. The single-letter path runs the identical SQL with a one-row filter, so there
is one code path to trust.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Any, Callable

from api.letters import source as letter_source
from api.letters.catalog import Catalog, catalog
from api.letters.model import (Debt, DebtService, Kind, LateFee, Letter, MailingAddress,
                               ReturnedPayment)

LETTER_ID = re.compile(r"^(CC|ADJ)-(\d{1,14})$")

_WINDOW = "c.cc_dttm >= %(from_ts)s and c.cc_dttm < %(to_ts)s"
_ONE_CONTACT = "c.cc_id = %(cc_id)s"
_FEE_WINDOW = "a.cre_dt >= %(from_ts)s and a.cre_dt < %(to_ts)s"
_ONE_FEE = "a.adj_id = %(adj_id)s"

# Base-product event statuses (CI_LOOKUP_VAL, owner F1).
_COMPLETED, _CANCELED = "30", "40"

# The process each kind of letter comes from.
_PROCESS = {Kind.REMINDER: "Collection", Kind.DEPOSIT: "Collection", Kind.PAYMENT_PLAN: "Collection",
            Kind.DISCONNECT: "Severance", Kind.FINAL_NOTICE: "Write-Off", Kind.LIEN: "Write-Off"}


def _s(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _money(value: Any) -> Decimal:
    return Decimal("0") if value is None else Decimal(value)


def _copies(value: Any) -> int:
    return max(int(value or 1), 1)


def _day(value: Any) -> date | None:
    return value.date() if isinstance(value, datetime) else value


def _premise_line(address1: str, city: str, state: str, postal: str) -> str:
    tail = f"{city}{', ' + state if state else ''} {postal}".strip()
    return f"{address1}, {tail}" if address1 and tail else address1 or tail


def _address(r: dict[str, Any]) -> MailingAddress:
    """The person's address when C2M's address source says PER and the person has one; else the
    account's mailing premise."""
    p = "p_" if _s(r.get("address_source")) == "PER" and _s(r.get("p_address1")) else "m_"
    return MailingAddress(_s(r.get("name1")), _s(r.get("name2")), _s(r.get("name3")),
                          *(_s(r.get(f"{p}{k}")) for k in ("address1", "address2", "address3", "address4",
                                                             "city", "state", "postal", "country")))


def _service(r: dict[str, Any], amount_key: str) -> DebtService:
    return DebtService(_s(r.get("sa_id")), _s(r.get("service_type")),
                       _premise_line(_s(r.get("address1")), _s(r.get("city")), _s(r.get("state")), _s(r.get("postal"))),
                       _money(r.get(amount_key)))


class _Reader:
    def __init__(self, src: letter_source.Source, cat: Catalog):
        self.src, self.cat = src, cat

    def keyed(self, name: str, key: str, filter_sql: str, binds: dict) -> dict[str, dict[str, Any]]:
        return {_s(r[key]): r for r in self.src.rows(name, filter_sql, binds)}

    def grouped(self, name: str, filter_sql: str, binds: dict) -> dict[str, list[dict[str, Any]]]:
        out: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in self.src.rows(name, filter_sql, binds):
            out[_s(r["process_id"])].append(r)
        return out

    def contact_letters(self, filter_sql: str, binds: dict) -> list[Letter]:
        rows = self.src.rows("letters", filter_sql, binds)
        if not rows:
            return []
        balances = self.keyed("balances", "cc_id", filter_sql, binds)
        processes = {
            "Collection": (self.keyed("collection_processes", "cc_id", filter_sql, binds),
                           self.grouped("collection_events", filter_sql, binds),
                           self.grouped("collection_services", filter_sql, binds)),
            "Severance": (self.keyed("severance_processes", "cc_id", filter_sql, binds),
                          self.grouped("severance_events", filter_sql, binds), None),
            "Write-Off": (self.keyed("writeoff_processes", "cc_id", filter_sql, binds),
                          self.grouped("writeoff_events", filter_sql, binds),
                          self.grouped("writeoff_services", filter_sql, binds)),
        }
        returned = self.keyed("returned_payments", "cc_id", filter_sql, binds)
        out = []
        for r in rows:
            cc_id = _s(r["cc_id"])
            kind = self.cat.kind(r.get("template_code"), r.get("contact_type"), r.get("contact_type_description"))
            if not self.cat.is_letter(kind, r.get("contact_class")):
                continue
            created: datetime = r["cc_dttm"]
            letter_date = created.date()
            debt = None
            if kind in _PROCESS:
                headers, events, services = processes[_PROCESS[kind]]
                debt = self.debt(_PROCESS[kind], headers.get(cc_id), events, services, letter_date)
            # Measured on demo25: the disconnect-letter event fires after the cut event, so a
            # severance letter whose process has already cut service is DISCONNECTED, not a warning.
            if kind is Kind.DISCONNECT and debt is not None and debt.cut_completed_on is not None:
                kind = Kind.DISCONNECTED
            payment = None
            if kind is Kind.NSF and cc_id in returned:
                p = returned[cc_id]
                payment = ReturnedPayment(_s(p.get("adjustment_id")), _money(p.get("fee_amount")),
                                          _day(p.get("payment_date")),
                                          None if p.get("payment_amount") is None else _money(p["payment_amount"]),
                                          _s(p.get("tender_type")))
            out.append(Letter(
                letter_id=f"CC-{cc_id}", cc_id=cc_id, kind=kind, template_code=_s(r.get("template_code")),
                contact_type=_s(r.get("contact_type")), contact_type_description=_s(r.get("contact_type_description")),
                letter_date=letter_date, created_at=created, account_id=_s(r.get("account_id")),
                person_id=_s(r.get("person_id")), customer_name=_s(r.get("customer_name")),
                mailing_address=_address(r), copies=_copies(r.get("copies")), body=_s(r.get("body")),
                printed_at=r.get("letter_print_dttm"),
                account_balance=_money((balances.get(cc_id) or {}).get("balance")),
                debt=debt, returned_payment=payment))
        return out

    def debt(self, process_type: str, header: dict | None, events: dict, services: dict | None,
             letter_date: date) -> Debt | None:
        if header is None:
            return None
        process_id = _s(header["process_id"])
        if services is None:        # severance: the process is one SA and the header carries it
            sas = (_service(header, "arrears_amount"),)
        else:
            sas = tuple(_service(s, "amount") for s in services.get(process_id, ()))
        # A process created with ARS_AMT 0 (demo25: 3 of 10) still lists its SAs' arrears; the SA sum
        # is the amount then.
        arrears = _money(header.get("arrears_amount"))
        if arrears == 0:
            arrears = sum((s.amount for s in sas), Decimal("0"))
        on, on_type, cut_scheduled, cut_completed = self.timeline(events.get(process_id, ()), letter_date)
        return Debt(process_type, process_id, _s(header.get("template_code")), arrears,
                    _day(header.get("arrears_as_of")), on, on_type, cut_scheduled, cut_completed, sas)

    def timeline(self, events, letter_date: date):
        """What the process's own events say is coming. The next action is the earliest
        not-cancelled event triggered after the letter -- completed ones count, so a reprint of an
        old letter still announces the date the original announced."""
        on = cut_scheduled = cut_completed = None
        on_type = ""
        for e in events:
            status, code, descr = _s(e.get("status_cd")), _s(e.get("event_type_cd")), _s(e.get("event_type"))
            trigger, completion = _day(e.get("trigger_dt")), _day(e.get("completion_dt"))
            if status == _CANCELED:
                continue
            if trigger and trigger > letter_date and (on is None or trigger < on):
                on, on_type = trigger, descr
            if not self.cat.is_cut_event(code, descr):
                continue
            if status == _COMPLETED:
                if completion and completion <= letter_date and (cut_completed is None or completion > cut_completed):
                    cut_completed = completion
            elif trigger and trigger > letter_date and (cut_scheduled is None or trigger < cut_scheduled):
                cut_scheduled = trigger
        return on, on_type, cut_scheduled, cut_completed

    def late_fee_letters(self, filter_sql: str, binds: dict) -> list[Letter]:
        types = list(self.cat.late_fee_adjustment_types)
        if not types:
            return []
        binds = {**binds, "types": types}
        rows = self.src.rows("late_fees", filter_sql, binds)
        if not rows:
            return []
        balances = self.keyed("late_fee_balances", "adj_id", filter_sql, binds)
        out = []
        for r in rows:
            adj_id, charged = _s(r["adj_id"]), r["charged_on"]
            charged_on = _day(charged)
            fee = LateFee(adj_id, _money(r.get("amount")), charged_on, _s(r.get("sa_id")), _s(r.get("service_type")),
                          _premise_line(_s(r.get("sp_address1")), _s(r.get("sp_city")), _s(r.get("sp_state")),
                                        _s(r.get("sp_postal"))))
            out.append(Letter(
                letter_id=f"ADJ-{adj_id}", cc_id=None, kind=Kind.LATE_FEE, template_code="", contact_type="",
                contact_type_description=Kind.LATE_FEE.label, letter_date=charged_on,
                created_at=charged if isinstance(charged, datetime) else datetime.combine(charged, time()),
                account_id=_s(r.get("account_id")), person_id=_s(r.get("person_id")),
                customer_name=_s(r.get("customer_name")), mailing_address=_address(r),
                copies=_copies(r.get("copies")), body="", printed_at=None,
                account_balance=_money((balances.get(adj_id) or {}).get("balance")), late_fee=fee))
        return out


def list_letters(organization_id: str, date_from: date, date_to: date, *, connection: Callable | None = None,
                 ceiling: int = letter_source.ROW_CEILING, cat: Catalog | None = None) -> list[Letter]:
    """Contacts by contact date plus late fees by charge date, both days inclusive, oldest first."""
    binds = {"from_ts": datetime.combine(date_from, time()),
             "to_ts": datetime.combine(date_to + timedelta(days=1), time())}
    with letter_source.open_source(organization_id, connection=connection, ceiling=ceiling) as src:
        reader = _Reader(src, cat or catalog())
        letters = reader.contact_letters(_WINDOW, binds) + reader.late_fee_letters(_FEE_WINDOW, binds)
    return sorted(letters, key=lambda l: (l.created_at, l.letter_id))


def get_letter(organization_id: str, letter_id: str, *, connection: Callable | None = None,
               ceiling: int = letter_source.ROW_CEILING, cat: Catalog | None = None) -> Letter | None:
    m = LETTER_ID.match(letter_id or "")
    if not m:
        raise ValueError(f"not a letter id: {letter_id!r}")
    prefix, number = m.groups()
    with letter_source.open_source(organization_id, connection=connection, ceiling=ceiling) as src:
        reader = _Reader(src, cat or catalog())
        found = (reader.contact_letters(_ONE_CONTACT, {"cc_id": number}) if prefix == "CC"
                 else reader.late_fee_letters(_ONE_FEE, {"adj_id": number}))
    return found[0] if found else None
