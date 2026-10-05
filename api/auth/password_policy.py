"""What a NEW password must be: long, not the person's email, not a common one.

Length over composition rules (NIST 800-63B): twelve characters, no forced symbols. Applied
where a password is set (change-password, an administrator creating or resetting an account),
never at sign-in, so an existing password keeps working until its owner changes it.
"""
from __future__ import annotations

import re

MIN_LENGTH = 12

# The commonest choices that clear the length floor, compared after lower-casing. A breached-
# password service would be stronger; this keeps the obvious ones out with no network call.
_COMMON = {
    "password1234", "password12345", "password123!", "passwordpassword", "123456789012",
    "1234567890123", "qwertyuiop12", "qwertyuiop123", "qwerty123456", "1q2w3e4r5t6y",
    "iloveyou1234", "letmein12345", "welcome12345", "welcome123!!", "administrator",
    "changeme1234", "abc123456789", "abcdefghijkl", "monkey123456", "football1234",
    "baseball1234", "sunshine1234", "princess1234", "dragon123456", "trustno1trustno1",
    "passw0rd1234", "p@ssw0rd1234", "summer202612", "winter202612", "utility12345",
}


def password_problem(password: str, email: str) -> str | None:
    """The reason a new password is refused, in words for the person typing it; None if it passes."""
    if len(password) < MIN_LENGTH:
        return f"Use at least {MIN_LENGTH} characters."
    lowered = password.lower()
    local = email.split("@", 1)[0].lower()
    if len(local) >= 3 and (local in lowered or re.sub(r"[^a-z0-9]", "", local) in re.sub(r"[^a-z0-9]", "", lowered)):
        return "Don't use your email address in your password."
    if lowered in _COMMON or len(set(lowered)) <= 2:
        return "That password is too common. Choose something less guessable, such as a few unrelated words."
    return None
