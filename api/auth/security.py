"""Password hashing and JWT helpers."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from api.auth.config import access_token_minutes, jwt_algorithm, jwt_secret
from api.auth.permissions import permissions_for_role

PBKDF2_ITERATIONS = 260_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            int(iterations),
        )
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


_DUMMY_HASH: str | None = None


def dummy_password_check(password: str) -> None:
    """The same PBKDF2 work as a real check, for an email with no active account: without it
    an unknown email answered faster than a wrong password, and timing listed the accounts."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password(secrets.token_hex(16))
    verify_password(password, _DUMMY_HASH)


def password_fingerprint(encoded_hash: str) -> str:
    """A short digest of the stored password hash, carried in every token: when the password
    changes (or an administrator resets it) the fingerprint moves and older tokens stop working."""
    return hashlib.sha256(f"pwv:{encoded_hash}".encode("utf-8")).hexdigest()[:16]


def token_password_current(payload: dict[str, Any], encoded_hash: str) -> bool:
    """Whether the token was issued under the account's current password. A token issued before
    fingerprints existed carries none and is honoured until it expires (at most a working day)."""
    pwv = payload.get("pwv")
    return pwv is None or hmac.compare_digest(str(pwv), password_fingerprint(encoded_hash))


def create_access_token(
    *,
    user_id: str,
    email: str,
    role: str,
    client_id: str,
    organization_id: str | None,
    workstreams: list[str],
    pwv: str,
) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "role": role,
        "client_id": client_id,
        "organization_id": organization_id,
        "workstreams": workstreams,
        "permissions": sorted(permissions_for_role(role)),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=access_token_minutes())).timestamp()),
        "typ": "access",
        "pwv": pwv,
    }
    return jwt.encode(payload, jwt_secret(), algorithm=jwt_algorithm())


def decode_access_token(token: str) -> dict[str, Any]:
    payload = jwt.decode(token, jwt_secret(), algorithms=[jwt_algorithm()])
    # the same secret signs embed links: only a session token opens a session
    if payload.get("typ") != "access":
        raise jwt.InvalidTokenError("not an access token")
    return payload
