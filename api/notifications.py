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

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def smtp_configured() -> bool:
    return bool((os.environ.get("SMTP_HOST") or "").strip())


def clean_recipients(raw: list[str] | None) -> list[str]:
    """Normalized addresses, or ValueError naming the bad one."""
    recipients = [str(r).strip().lower() for r in (raw or [])]
    if not recipients:
        raise ValueError("At least one recipient is required")
    for r in recipients:
        if not EMAIL_RE.match(r):
            raise ValueError(f"Not a valid email address: {r}")
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
    port = int(os.environ.get("SMTP_PORT") or 587)
    with smtplib.SMTP(host, port, timeout=30) as smtp:
        if (os.environ.get("SMTP_STARTTLS") or "true").lower() != "false":
            smtp.starttls()
        user = (os.environ.get("SMTP_USERNAME") or "").strip()
        if user:
            smtp.login(user, os.environ.get("SMTP_PASSWORD") or "")
        smtp.send_message(msg)
