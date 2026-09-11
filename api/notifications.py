"""Outbound email for the portal's scheduled deliveries and KPI alerts.

    SMTP_HOST / SMTP_PORT (587) / SMTP_USERNAME / SMTP_PASSWORD /
    SMTP_FROM / SMTP_STARTTLS (default true)

Nothing sends when SMTP_HOST is unset; callers check smtp_configured() and the
UI says so rather than failing silently.
"""
from __future__ import annotations

import os
import re
import smtplib
from email.message import EmailMessage

# Printable ASCII only, either side of the @. The previous pattern excluded `@` and
# WHITESPACE, which stops the CR/LF header-injection routes but admits every other
# control character: "a@b.com\x00" was accepted and reached the To header, where an MTA
# that truncates at NUL delivers somewhere other than what the portal recorded and
# showed the operator who approved it.
EMAIL_RE = re.compile(r"^[!-?A-~]+@[!-?A-~]+\.[!-?A-~]+$")


def smtp_configured() -> bool:
    return bool((os.environ.get("SMTP_HOST") or "").strip())


def allowed_recipient_domains() -> set[str]:
    """Domains a delivery may reach; empty means no restriction.

    Audit M6: recipients are validated for SHAPE only, so a saved view on a cadence can
    mail its CSV to any address. Which domains are acceptable is a per-deployment
    policy this file cannot know, so it reads PORTAL_ALLOWED_RECIPIENT_DOMAINS and is
    INERT until an operator sets it. Setting it is the control; this only enforces it.
    """
    raw = (os.environ.get("PORTAL_ALLOWED_RECIPIENT_DOMAINS") or "").strip()
    return {d.strip().lower() for d in raw.split(",") if d.strip()}


def clean_recipients(raw: list[str] | None) -> list[str]:
    """Normalized addresses, or ValueError naming the bad one."""
    recipients = [str(r).strip().lower() for r in (raw or [])]
    if not recipients:
        raise ValueError("At least one recipient is required")
    allowed = allowed_recipient_domains()
    for r in recipients:
        if not EMAIL_RE.match(r):
            raise ValueError(f"Not a valid email address: {r}")
        # Exact domain match, never a suffix: "origin.local" must not admit
        # "origin.local.attacker.example".
        if allowed and r.rsplit("@", 1)[1] not in allowed:
            raise ValueError(f"Recipient domain is not permitted: {r}")
    return recipients


def build_message(subject: str, recipients: list[str], body: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = (os.environ.get("SMTP_FROM") or "reports@originba.local").strip()
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)
    return msg


def send_message(msg: EmailMessage) -> None:
    host = (os.environ.get("SMTP_HOST") or "").strip()
    if not host:
        raise RuntimeError("SMTP_HOST is not configured")
    # A bad SMTP_PORT must not be the thing that raises: this runs inside the hourly
    # schedule runner, where an unhandled ValueError ends the whole pass rather than
    # one delivery, and the misconfiguration is a typo the operator cannot see.
    try:
        port = int(str(os.environ.get("SMTP_PORT") or 587).strip())
    except (TypeError, ValueError):
        port = 587
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if (os.environ.get("SMTP_STARTTLS") or "true").lower() != "false":
            smtp.starttls()
        user = (os.environ.get("SMTP_USERNAME") or "").strip()
        if user:
            smtp.login(user, os.environ.get("SMTP_PASSWORD") or "")
        smtp.send_message(msg)
