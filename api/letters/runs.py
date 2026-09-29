"""Letter runs: a frozen list of letters that a second person approves before it is released as one
print file.

A run stores ids, counts and a fingerprint per letter -- a hash of everything the printed page says
(words, amounts, dates, address) -- and never the words themselves. Release re-reads the letters and
compares fingerprints, so a letter C2M changed after approval is never printed unapproved.

draft -> approved -> released; draft or approved -> cancelled. Approval is refused to the run's
creator (four eyes). Runs live in the organization's store; past MAX_RUNS the oldest released or
cancelled run makes room, and a run still open is never dropped: the new draft is refused instead.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import re
import threading
import uuid
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from api.letters.catalog import Words
from api.letters.composer import compose
from api.letters.model import Kind, Letter
from api.org_store import OrgRecordStore

ROOT = Path(__file__).resolve().parents[2]
RUNS_PATH = ROOT / "data" / "analytics_portal" / "letter_runs.json"
MAX_RUNS = 200
# One print file is rendered in memory (~4 ms and ~3 KB a page): 5,000 letters is ~20 s and ~15 MB,
# and a month at Ellensburg is ~3,200.
MAX_RUN_LETTERS = 5_000
RUN_ID = re.compile(r"^[0-9a-f]{32}$")
PRINTED = ("all", "printed", "not_printed")
OPEN, FINISHED = ("draft", "approved"), ("released", "cancelled")

_store = OrgRecordStore("letter_runs", lambda: RUNS_PATH, "runs")
_lock = threading.Lock()        # one read-modify-write at a time in this process


class RunError(Exception):
    def __init__(self, status: int, detail: str, **counts: int):
        super().__init__(detail)
        self.status, self.detail, self.counts = status, detail, counts


def fingerprint(letter: Letter, words: Words, client_name: str) -> str:
    """Everything the page prints, hashed. Not the print stamp C2M adds after mailing."""
    content = {"id": letter.letter_id, "kind": letter.kind.value, "date": letter.letter_date,
               "account": letter.account_id, "template": letter.template_code, "imb": letter.imb,
               "address": letter.mailing_address.lines(), "customer": letter.customer_name,
               "services": letter.debt.services if letter.debt else (), "client": client_name,
               "composed": dataclasses.asdict(compose(letter, words))}
    text = json.dumps(content, sort_keys=True, default=lambda v: dataclasses.asdict(v)
                      if dataclasses.is_dataclass(v) else str(v))
    return hashlib.blake2b(text.encode(), digest_size=16).hexdigest()


def clean_filters(raw: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(raw or {})
    kinds, printed = raw.pop("kinds", []) or [], raw.pop("printed", "all") or "all"
    known = {k.value for k in Kind}
    if raw or not isinstance(kinds, list) or not set(kinds) <= known or printed not in PRINTED:
        raise RunError(422, "A run is chosen by letter type (kinds) and printed status (printed) only.")
    return {"kinds": list(dict.fromkeys(kinds)), "printed": printed}


def select(letters: list[Letter], filters: dict[str, Any]) -> list[Letter]:
    kinds, printed = set(filters["kinds"]), filters["printed"]
    return [l for l in letters
            if (not kinds or l.kind.value in kinds)
            and (printed == "all" or (printed == "printed") == (l.printed_at is not None))]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _same_person(actor: dict[str, str], other: dict[str, str]) -> bool:
    return actor["id"] == other.get("id") or actor["email"].lower() == (other.get("email") or "").lower()


def _make_room(organization_id: str) -> None:
    runs = sorted(_store.list(organization_id), key=lambda r: r["created_at"])
    finished = [r for r in runs if r["status"] in FINISHED]
    excess = len(runs) - MAX_RUNS + 1
    if excess > len(finished):
        raise RunError(409, f"This organization has reached its limit of {MAX_RUNS} runs still waiting for "
                            "approval or release. Release or cancel one, then create the run again.")
    for r in finished[:max(excess, 0)]:
        _store.delete(r["id"], organization_id)


def create(organization_id: str, date_from: date, date_to: date, filters: dict[str, Any],
           letters: list[Letter], words: Words, client_name: str, actor: dict[str, str]) -> dict[str, Any]:
    chosen = select(letters, filters)
    if not chosen:
        raise RunError(422, "No letters in this window match; there is nothing to put in a run.")
    if len(chosen) > MAX_RUN_LETTERS:
        raise RunError(422, f"A run holds at most {MAX_RUN_LETTERS:,} letters and this one would hold "
                            f"{len(chosen):,}. Choose a shorter window or fewer letter types.")
    at = _now()
    run = {"id": uuid.uuid4().hex, "organization_id": organization_id, "from": date_from.isoformat(),
           "to": date_to.isoformat(), "filters": filters, "status": "draft", "created_by": actor, "created_at": at,
           "history": [{"status": "draft", "by": actor["email"], "at": at}],
           "by_kind": dict(Counter(l.kind.value for l in chosen)),
           "manifest": [[l.letter_id, fingerprint(l, words, client_name)] for l in chosen]}
    with _lock:
        _make_room(organization_id)
        _store.add(run)
    return run


def list_runs(organization_id: str) -> list[dict[str, Any]]:
    return sorted(_store.list(organization_id), key=lambda r: r["created_at"], reverse=True)


def get(organization_id: str, run_id: str) -> dict[str, Any]:
    run = next((r for r in _store.list(organization_id) if r["id"] == run_id), None)
    if run is None:
        raise RunError(404, "No such run in this organization.")
    return run


def _move(organization_id: str, run_id: str, to: str, actor: dict[str, str], allowed: tuple[str, ...],
          refuse: dict[str, str], **fields: Any) -> dict[str, Any]:
    with _lock:
        run = get(organization_id, run_id)
        if run["status"] not in allowed:
            raise RunError(409, refuse[run["status"]])
        at = _now()
        run.update(status=to, history=[*run["history"], {"status": to, "by": actor["email"], "at": at}],
                   **{f"{to}_by": actor, f"{to}_at": at}, **fields)
        _store.update(run)
    return run


_NOT_DRAFT = {"approved": "This run is already approved.", "released": "This run has been released.",
              "cancelled": "This run was cancelled."}


def approve(organization_id: str, run_id: str, actor: dict[str, str]) -> dict[str, Any]:
    run = get(organization_id, run_id)
    if run["status"] == "draft" and _same_person(actor, run["created_by"]):
        raise RunError(403, "You created this run, so someone else must approve it.")
    return _move(organization_id, run_id, "approved", actor, ("draft",), _NOT_DRAFT)


def cancel(organization_id: str, run_id: str, actor: dict[str, str], is_admin: bool) -> dict[str, Any]:
    run = get(organization_id, run_id)
    if not is_admin and not _same_person(actor, run["created_by"]):
        raise RunError(403, "Only the person who created this run, or an administrator, can cancel it.")
    return _move(organization_id, run_id, "cancelled", actor, OPEN,
                 {"released": "A released run cannot be cancelled.", "cancelled": "This run was cancelled."})


def require_releasable(run: dict[str, Any]) -> None:
    if run["status"] not in ("approved", "released"):
        raise RunError(409, "Approve this run before releasing it." if run["status"] == "draft"
                       else "This run was cancelled.")


def letters_to_print(run: dict[str, Any], letters: list[Letter], words: Words, client_name: str) -> list[Letter]:
    """The manifest's letters in manifest order; a 409 when any changed or disappeared."""
    by_id = {l.letter_id: l for l in letters}
    missing = sum(1 for letter_id, _ in run["manifest"] if letter_id not in by_id)
    changed = sum(1 for letter_id, fp in run["manifest"]
                  if letter_id in by_id and fingerprint(by_id[letter_id], words, client_name) != fp)
    if changed or missing:
        parts = ([f"{changed:,} letter{' changed' if changed == 1 else 's changed'}"] if changed else []) + \
                ([f"{missing:,} letter{' no longer exists' if missing == 1 else 's no longer exist'}"] if missing else [])
        raise RunError(409, f"Since this run was created, {' and '.join(parts)} in the customer system. Cancel "
                            "it and create a new run, so the letters are approved as they will print.",
                       changed=changed, missing=missing)
    return [by_id[letter_id] for letter_id, _ in run["manifest"]]


def mark_released(organization_id: str, run_id: str, actor: dict[str, str], pages: int) -> dict[str, Any]:
    return _move(organization_id, run_id, "released", actor, ("approved",),
                 {"released": "This run has been released.",
                  "cancelled": "This run was cancelled while its print file was being prepared."}, pages=pages)


def public(run: dict[str, Any], actor: dict[str, str], *, with_letters: bool = False) -> dict[str, Any]:
    """The run as the page shows it: people by email, counts by type, no fingerprints."""
    email = lambda key: (run.get(key) or {}).get("email")  # noqa: E731
    out = {"id": run["id"], "status": run["status"], "from": run["from"], "to": run["to"],
           "filters": run["filters"], "created_by": email("created_by"), "created_at": run["created_at"],
           "created_by_you": _same_person(actor, run["created_by"]),
           "approved_by": email("approved_by"), "approved_at": run.get("approved_at"),
           "released_by": email("released_by"), "released_at": run.get("released_at"), "pages": run.get("pages"),
           "cancelled_by": email("cancelled_by"), "cancelled_at": run.get("cancelled_at"),
           "history": run["history"],
           "counts": {"letters": len(run["manifest"]),
                      "by_kind": [{"kind": k, "label": Kind(k).label, "count": n}
                                  for k, n in sorted(run["by_kind"].items(), key=lambda kv: -kv[1])]}}
    if with_letters:
        out["letter_ids"] = [letter_id for letter_id, _ in run["manifest"]]
    return out
