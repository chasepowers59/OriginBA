"""Outbound mail: who it can reach, and what can be smuggled into a header.

Four functions here were named in no test — `smtp_configured` (9 uses),
`send_message` (6), `clean_recipients` (4), `build_message` (4) — while being the last
code between a saved view and an email leaving the building.

What was already sound, and is pinned here so it stays that way: a recipient carrying
CR or LF is rejected by `EMAIL_RE`, and a Subject carrying either is rejected by
Python's own header policy. Those are the two classic injection routes and both hold.

What was NOT: `EMAIL_RE` excludes `@` and WHITESPACE, so any other control character
passed. `a@b.com\\x00` was accepted and went into the To header, where an MTA that
truncates at NUL delivers somewhere other than what the portal recorded and shows the
operator. Addresses are now required to be printable ASCII.

M6 from docs/SECURITY_AUDIT_2026-09-01.md is the remaining exposure and it is a POLICY
question, not a bug: recipients are validated for SHAPE only, so a scheduled report's
CSV can be mailed to any address on a cadence. `PORTAL_ALLOWED_RECIPIENT_DOMAINS`
closes it where an operator configures it, and is INERT until they do — so setting it
is the deployment step, not this file.
"""

from __future__ import annotations

import os
import sys
import unittest
from email.message import EmailMessage
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from api.notifications import (  # noqa: E402
    build_message,
    clean_recipients,
    send_message,
    smtp_configured,
)


class CleanRecipientsTests(unittest.TestCase):
    def test_normalizes_case_and_surrounding_space(self):
        self.assertEqual(clean_recipients(["  A@B.COM  "]), ["a@b.com"])

    def test_requires_at_least_one(self):
        for empty in (None, []):
            with self.assertRaises(ValueError):
                clean_recipients(empty)

    def test_rejects_a_shape_that_is_not_an_address(self):
        for bad in ["nope", "a@b", "@b.com", "a@.com", "a b@c.com"]:
            with self.assertRaises(ValueError, msg=bad):
                clean_recipients([bad])

    def test_rejects_the_two_header_injection_routes(self):
        """CR/LF in a recipient would add headers to the outgoing message."""
        for bad in ["a@b.com\nBcc: evil@x.com", "a@b.com\rBcc: evil@x.com"]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                clean_recipients([bad])

    def test_rejects_other_control_characters_too(self):
        """NUL passed the whitespace-only exclusion and reached the To header.

        An MTA that truncates at NUL then delivers to an address the portal never
        recorded, while the UI shows the full string the operator approved.
        """
        for bad in ["a@b.com\x00", "a@b.com\x00evil@x.com", "a\x07@b.com", "a@b.com\x1b"]:
            with self.assertRaises(ValueError, msg=repr(bad)):
                clean_recipients([bad])

    def test_a_trailing_newline_alone_is_stripped_not_rejected(self):
        """`$` matches before a trailing newline in Python, so this one relies on the
        strip() rather than on the pattern. Pinned because it is not obvious."""
        self.assertEqual(clean_recipients(["a@b.com\n"]), ["a@b.com"])


class RecipientDomainPolicyTests(unittest.TestCase):
    """M6: shape validation alone lets a cadence mail CSVs anywhere."""

    def test_no_policy_configured_changes_nothing(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("PORTAL_ALLOWED_RECIPIENT_DOMAINS", None)
            self.assertEqual(clean_recipients(["anyone@external.example"]),
                             ["anyone@external.example"])

    def test_a_configured_allow_list_admits_its_own_domains(self):
        with mock.patch.dict(os.environ,
                             {"PORTAL_ALLOWED_RECIPIENT_DOMAINS": "origin.local, city.gov"}):
            self.assertEqual(clean_recipients(["a@origin.local", "b@CITY.GOV"]),
                             ["a@origin.local", "b@city.gov"])

    def test_a_configured_allow_list_refuses_anything_else(self):
        with mock.patch.dict(os.environ,
                             {"PORTAL_ALLOWED_RECIPIENT_DOMAINS": "origin.local"}):
            with self.assertRaises(ValueError):
                clean_recipients(["exfil@attacker.example"])

    def test_a_subdomain_is_not_the_domain(self):
        """origin.local must not admit origin.local.attacker.example."""
        with mock.patch.dict(os.environ,
                             {"PORTAL_ALLOWED_RECIPIENT_DOMAINS": "origin.local"}):
            with self.assertRaises(ValueError):
                clean_recipients(["a@origin.local.attacker.example"])


class BuildMessageTests(unittest.TestCase):
    def test_carries_subject_recipients_and_body(self):
        msg = build_message("Weekly report", ["a@b.com", "c@d.com"], "the body")
        self.assertEqual(msg["Subject"], "Weekly report")
        self.assertEqual(msg["To"], "a@b.com, c@d.com")
        self.assertIn("the body", msg.get_content())

    def test_from_defaults_but_is_configurable(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SMTP_FROM", None)
            self.assertEqual(build_message("s", ["a@b.com"], "b")["From"],
                             "reports@originba.local")
        with mock.patch.dict(os.environ, {"SMTP_FROM": " reports@city.gov "}):
            self.assertEqual(build_message("s", ["a@b.com"], "b")["From"],
                             "reports@city.gov")

    def test_a_newline_in_the_subject_cannot_add_a_header(self):
        """Python's header policy enforces this; pinned so a policy change is caught."""
        with self.assertRaises(ValueError):
            build_message("Report\nBcc: evil@x.com", ["a@b.com"], "body")


class SmtpConfiguredTests(unittest.TestCase):
    def test_reflects_smtp_host_only(self):
        with mock.patch.dict(os.environ, {"SMTP_HOST": "smtp.example"}):
            self.assertTrue(smtp_configured())
        for blank in ("", "   "):
            with mock.patch.dict(os.environ, {"SMTP_HOST": blank}):
                self.assertFalse(smtp_configured())


class SendMessageTests(unittest.TestCase):
    def test_refuses_to_send_with_no_host(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SMTP_HOST", None)
            with self.assertRaises(RuntimeError):
                send_message(EmailMessage())

    def test_starttls_is_on_unless_explicitly_disabled(self):
        """Fail-safe: only the literal "false" turns TLS off, so a typo keeps it ON."""
        for value, expect_tls in [(None, True), ("true", True), ("TRUE", True),
                                  ("0", True), ("nope", True), ("false", False),
                                  ("False", False)]:
            env = {"SMTP_HOST": "smtp.example"}
            if value is not None:
                env["SMTP_STARTTLS"] = value
            with mock.patch.dict(os.environ, env), \
                 mock.patch("smtplib.SMTP") as smtp_cls:
                os.environ.pop("SMTP_USERNAME", None)
                if value is None:
                    os.environ.pop("SMTP_STARTTLS", None)
                send_message(EmailMessage())
                client = smtp_cls.return_value.__enter__.return_value
                self.assertEqual(client.starttls.called, expect_tls, f"SMTP_STARTTLS={value!r}")

    def test_a_nonnumeric_port_does_not_crash_the_sender(self):
        """int(os.environ[...]) raised ValueError, which surfaces as a 500 on a route
        and as an unhandled exception in the hourly schedule runner."""
        with mock.patch.dict(os.environ, {"SMTP_HOST": "smtp.example", "SMTP_PORT": "not-a-port"}), \
             mock.patch("smtplib.SMTP") as smtp_cls:
            send_message(EmailMessage())
            self.assertEqual(smtp_cls.call_args[0][1], 587)

    def test_logs_in_only_when_a_username_is_set(self):
        for user, expect_login in [("", False), ("mailer", True)]:
            env = {"SMTP_HOST": "smtp.example", "SMTP_PASSWORD": "pw"}
            if user:
                env["SMTP_USERNAME"] = user
            with mock.patch.dict(os.environ, env), mock.patch("smtplib.SMTP") as smtp_cls:
                if not user:
                    os.environ.pop("SMTP_USERNAME", None)
                send_message(EmailMessage())
                client = smtp_cls.return_value.__enter__.return_value
                self.assertEqual(client.login.called, expect_login)


if __name__ == "__main__":
    unittest.main()
