"""config/letters.yml: which kind of letter each C2M template / contact type is, which contact
classes count as credit & collections, which adjustment types are late fees, which severance
events cut service, and the words (phone, payment URL, fees, signature) each client's letters carry."""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from api.letters.model import Kind

CONFIG = Path(__file__).resolve().parents[2] / "config" / "letters.yml"


@dataclass(frozen=True)
class Words:
    client_name: str
    disconnect_grace_days: int
    reconnect_fee: Decimal
    contact_phone: str
    payment_url: str
    office_hours: str
    utility_address: tuple[str, ...]
    remit_address: tuple[str, ...]
    payee: str
    department: str
    signature: str
    notes: tuple[str, ...]
    logo: str
    brand_color: str
    accent_color: str
    lien_action: str

    @property
    def accent_or_brand(self) -> str:
        return self.accent_color or self.brand_color


def _norm(code: Any) -> str:
    return "" if code is None else str(code).strip().upper()


def _hex(value: Any) -> str:
    h = str(value).strip().replace("#", "").upper()
    if h and not re.fullmatch(r"[0-9A-F]{6}", h):
        raise ValueError(f"letters.yml colour '{value}' is not six hex digits")
    return h


class Catalog:
    def __init__(self, root: dict[str, Any]):
        self._by_template: dict[str, Kind] = {}
        self._by_contact_type: dict[str, Kind] = {}
        for name, lists in (root.get("kinds") or {}).items():
            kind = Kind(name)
            for t in lists.get("templates") or ():
                self._by_template[_norm(t)] = kind
            for t in lists.get("contact_types") or ():
                self._by_contact_type[_norm(t)] = kind
        self._patterns = [(Kind(p["kind"]), re.compile(p["regex"])) for p in root.get("patterns") or ()]
        self._collection_classes = {_norm(c) for c in root.get("collection_contact_classes") or ()}
        self.late_fee_adjustment_types = tuple(_norm(t) for t in root.get("late_fee_adjustment_types") or ())
        cut = root.get("severance_cut_events") or {}
        self._cut_codes = {_norm(c) for c in cut.get("codes") or ()}
        self._cut_regex = re.compile(cut["regex"]) if cut.get("regex") else None
        self._defaults = root.get("defaults") or {}
        self.clients: dict[str, dict[str, Any]] = root.get("clients") or {}

    @classmethod
    def load(cls, path: Path = CONFIG) -> Catalog:
        return cls(yaml.safe_load(path.read_text(encoding="utf-8")) or {})

    def kind(self, template_code: str | None, contact_type: str | None, description: str | None = "") -> Kind:
        """Exact CONTACT TYPE first, then the template code, then the regexes over the contact type,
        its description and the template; GENERIC otherwise.

        The contact type is what the process event configuration selects and what an agent sees on
        the account, so it carries the utility's intent; the template is only the print artefact,
        and a stale one stays attached. Measured at Ellensburg: contact type DISCWARNING "Disconnect
        Warning Letter" points at template CM04-DELINQ "Delinquency/Lien Letter (To be scrapped?)".
        The description is what makes an unconfigured client work: descriptions are meaningful
        fleet-wide ("Shut Off Poor Pay Customer", "Tax Roll Contact") where codes are local.
        """
        t, c, d = _norm(template_code), _norm(contact_type), _norm(description)
        if c in self._by_contact_type:
            return self._by_contact_type[c]
        if t in self._by_template:
            return self._by_template[t]
        for signal in (c, d, t):
            if signal:
                for kind, regex in self._patterns:
                    if regex.search(signal):
                        return kind
        return Kind.GENERIC

    def is_letter(self, kind: Kind, contact_class: str | None) -> bool:
        """A recognised collections kind is a letter in any class; an unknown template only inside a
        collections class."""
        if kind is Kind.NOT_A_LETTER:
            return False
        return kind is not Kind.GENERIC or _norm(contact_class) in self._collection_classes

    def is_cut_event(self, event_type_code: str | None, description: str | None) -> bool:
        if _norm(event_type_code) in self._cut_codes:
            return True
        if self._cut_regex is None:
            return False
        return bool(self._cut_regex.search(event_type_code or "") or self._cut_regex.search(description or ""))

    def words(self, client_id: str | None) -> Words:
        client = self.clients.get(client_id or "") or {}

        def pick(key: str, fallback: Any) -> Any:
            for source in (client, self._defaults):
                if source.get(key) is not None:
                    return source[key]
            return fallback

        def lines(key: str) -> tuple[str, ...]:
            return tuple(str(v) for v in pick(key, ()))

        return Words(
            client_name=str(pick("client_name", "")),
            disconnect_grace_days=int(pick("disconnect_grace_days", 10)),
            reconnect_fee=Decimal(str(pick("reconnect_fee", 0))).quantize(Decimal("0.01")),
            contact_phone=str(pick("contact_phone", "")), payment_url=str(pick("payment_url", "")),
            office_hours=str(pick("office_hours", "")), utility_address=lines("utility_address"),
            remit_address=lines("remit_address"), payee=str(pick("payee", "")),
            department=str(pick("department", "")), signature=str(pick("signature", "Customer Service")),
            notes=lines("notes"), logo=str(pick("logo", "")),
            brand_color=_hex(pick("brand_color", "006FAC")), accent_color=_hex(pick("accent_color", "")),
            lien_action=str(pick("lien_action", "recorded as a lien against the property")),
        )


@lru_cache(maxsize=1)
def catalog() -> Catalog:
    return Catalog.load()
