"""Collections letters for the caller's organization: the list for a date window, one letter with
its words and the process behind it, and its PDF.

Postgres organizations read through their warehouse, Oracle organizations through their own
connection (letters.source picks the SQL); any other engine is answered 501.
"""
from __future__ import annotations

import dataclasses
import logging
from datetime import date
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.routing import APIRoute

from api.access_audit import record_access_event
from api.reporting_dates import data_as_of
from api.auth.dependencies import AuthContext, require_permission
from api.demo_db import demo_configured
from api.executive_dashboard import is_not_connected_error
from api.letters import render, repository
from api.letters.catalog import Words, catalog
from api.letters.composer import compose
from api.letters.model import Letter
from api.letters.source import RowCeilingExceeded
from api.org_db import require_org_for_data
from api.organizations import organization_display_name
from api.row_security import require_unrestricted
from api.snapshot_catalog import org_backend
from api.warehouse_db import warehouse_configured

logger = logging.getLogger(__name__)

NO_STORE = {"Cache-Control": "no-store"}
MAX_WINDOW_DAYS = 366


class _NoStore(APIRoute):
    """Every answer here names customers, amounts owed, or which letters exist: never cached,
    refusals included."""

    def get_route_handler(self) -> Callable:
        handler = super().get_route_handler()

        async def no_store(request):
            try:
                response = await handler(request)
            except HTTPException as exc:
                exc.headers = {**(exc.headers or {}), **NO_STORE}
                raise
            response.headers.update(NO_STORE)
            return response
        return no_store


router = APIRouter(prefix="/portal/letters", tags=["letters"], route_class=_NoStore)
READ = Depends(require_permission("letters:read"))


def _org(ctx: AuthContext) -> str:
    require_unrestricted(ctx)          # a letter cannot be cut down to a person's row rules
    org_id = require_org_for_data(ctx)
    engine, _ = org_backend(org_id)
    if engine == "postgres":
        configured = warehouse_configured(org_id)
    elif engine == "oracle":
        configured = demo_configured(org_id)
    else:
        raise HTTPException(status_code=501, detail="Letters are not available for this organization yet.")
    if not configured:
        raise HTTPException(status_code=503, detail="Letters need this organization's database, and none is configured.")
    return org_id


def _read(fn: Callable, *args: Any) -> Any:
    try:
        return fn(*args)
    except RowCeilingExceeded as exc:
        raise HTTPException(status_code=422, detail="This window holds more letter data than one request may "
                                                    "read. Choose a shorter window.") from exc
    except Exception as exc:  # noqa: BLE001 -- the driver's text can name hosts and users
        logger.exception("letters read failed")
        if is_not_connected_error(str(exc)):
            raise HTTPException(status_code=503, detail="This organization's database cannot be reached right "
                                                        "now. Try again shortly.") from exc
        raise HTTPException(status_code=502, detail="The letters could not be read from this organization's "
                                                    "database.") from exc


def _one(org_id: str, letter_id: str) -> Letter:
    if not repository.LETTER_ID.match(letter_id):
        raise HTTPException(status_code=422, detail="A letter id looks like CC-1234567890 or ADJ-123456789012.")
    letter = _read(repository.get_letter, org_id, letter_id)
    if letter is None:
        raise HTTPException(status_code=404, detail="No such letter in this organization.")
    return letter


def _words(org_id: str) -> tuple[Words, str]:
    words = catalog().words(org_id)
    return words, words.client_name or organization_display_name(org_id) or org_id


def _summary(letter: Letter) -> dict[str, Any]:
    debt = letter.debt
    amount = (debt.arrears_amount if debt else letter.returned_payment.fee_amount if letter.returned_payment
              else letter.late_fee.amount if letter.late_fee else letter.account_balance)
    return {
        "letter_id": letter.letter_id, "kind": letter.kind.value, "kind_label": letter.kind.label,
        "template_code": letter.template_code,
        "contact_type": letter.contact_type_description or letter.contact_type,
        "letter_date": letter.letter_date, "account_id": letter.account_id,
        "recipient": letter.mailing_address.name1 or letter.customer_name, "amount": amount,
        "process_type": debt.process_type if debt else "", "process_id": debt.process_id if debt else "",
        "next_action_on": debt.next_action_on if debt else None,
        "printed": letter.printed_at is not None, "copies": letter.copies,
    }


def _audit(ctx: AuthContext, action: str, target_type: str, target_id: str, detail: str) -> None:
    """Ids and counts only: never a name, an address or an amount."""
    record_access_event(actor_email=ctx.email, actor_id=ctx.id, action=action, target_type=target_type,
                        target_id=target_id, detail=detail)


@router.get("/as-of")
def letters_as_of(ctx: AuthContext = READ) -> dict[str, Any]:
    """Where the organization's data ends (a frozen copy declares it), so the page opens on the
    last full month the data covers rather than the viewer's."""
    return {"data_as_of": data_as_of(_org(ctx))}


@router.get("")
def list_letters(ctx: AuthContext = READ, date_from: str = Query("", alias="from"),
                 date_to: str = Query("", alias="to")) -> dict[str, Any]:
    org_id = _org(ctx)
    try:
        start, end = date.fromisoformat(date_from), date.fromisoformat(date_to)
    except ValueError:
        raise HTTPException(status_code=422, detail="Give the window as from=YYYY-MM-DD&to=YYYY-MM-DD.") from None
    if end < start or (end - start).days >= MAX_WINDOW_DAYS:
        raise HTTPException(status_code=422, detail=f"A window runs forward and covers at most {MAX_WINDOW_DAYS} days.")
    letters = _read(repository.list_letters, org_id, start, end)
    _audit(ctx, "letters_list", "letters", org_id, f"from={start}; to={end}; letters={len(letters)}")
    return {"organization_id": org_id, "from": start, "to": end, "count": len(letters),
            "letters": [_summary(l) for l in letters]}


@router.get("/{letter_id}")
def letter_detail(letter_id: str, ctx: AuthContext = READ) -> dict[str, Any]:
    org_id = _org(ctx)
    letter = _one(org_id, letter_id)
    composed = dataclasses.asdict(compose(letter, _words(org_id)[0]))
    composed["glance"] = [{"label": label, "value": value} for label, value in composed["glance"]]
    _audit(ctx, "letter_preview", "letter", letter.letter_id, f"org={org_id}; account={letter.account_id}")
    return {
        "organization_id": org_id, "letter": _summary(letter),
        "recipient": {"customer_name": letter.customer_name, "person_id": letter.person_id,
                      "address_lines": list(letter.mailing_address.lines())},
        "composed": composed,
        "process": dataclasses.asdict(letter.debt) if letter.debt else None,
        "returned_payment": dataclasses.asdict(letter.returned_payment) if letter.returned_payment else None,
        "late_fee": dataclasses.asdict(letter.late_fee) if letter.late_fee else None,
        "account_balance": letter.account_balance, "contact_id": letter.cc_id, "body": letter.body,
        "created_at": letter.created_at, "printed_at": letter.printed_at,
    }


@router.get("/{letter_id}/pdf")
def letter_pdf(letter_id: str, ctx: AuthContext = READ) -> Response:
    org_id = _org(ctx)
    letter = _one(org_id, letter_id)
    out = render.render_letters([letter], *_words(org_id))
    _audit(ctx, "letter_pdf", "letter", letter.letter_id,
           f"org={org_id}; account={letter.account_id}; pages={out.pages}")
    headers = {"Content-Disposition": f'inline; filename="{letter.letter_id}.pdf"', "X-Letter-Font": out.font}
    if out.note:
        headers["X-Letter-Font-Note"] = out.note
    return Response(out.pdf, media_type="application/pdf", headers=headers)
