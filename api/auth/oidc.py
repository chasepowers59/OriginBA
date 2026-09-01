"""OIDC single sign-on — the enterprise gate (Azure AD / Entra is the utility default).

Generic authorization-code flow, config entirely from env:

    OIDC_ISSUER                 https://login.microsoftonline.com/<tenant>/v2.0
    OIDC_CLIENT_ID              app registration's client id
    OIDC_CLIENT_SECRET          client secret
    OIDC_REDIRECT_URI           this API's /auth/oidc/callback URL (registered at the IdP)
    OIDC_DEFAULT_ORGANIZATION   org for just-in-time provisioned users
    OIDC_POST_LOGIN_URL         the SPA login page; receives #sso_token=<our JWT>

No new dependencies: stdlib urllib for the two IdP calls, PyJWT (+cryptography, already
shipped) for RS256 id_token verification via the IdP's JWKS. Users are JIT-provisioned
on first login as role `user` in the default org — an admin promotes from there; SSO
never mints admins. The SPA receives OUR access token (same shape as password login) in
the URL fragment, which never reaches server logs.
"""
from __future__ import annotations

import json
import os
import secrets
import time
import urllib.parse
import urllib.request
from typing import Any

import jwt

from api.auth.config import jwt_secret

_DISCOVERY_CACHE: dict[str, dict[str, Any]] = {}
_STATE_TTL_SECONDS = 600


def oidc_config() -> dict[str, str] | None:
    keys = ("OIDC_ISSUER", "OIDC_CLIENT_ID", "OIDC_CLIENT_SECRET", "OIDC_REDIRECT_URI")
    values = {k: (os.environ.get(k) or "").strip() for k in keys}
    if not all(values.values()):
        return None
    values["OIDC_DEFAULT_ORGANIZATION"] = (os.environ.get("OIDC_DEFAULT_ORGANIZATION") or "").strip()
    values["OIDC_POST_LOGIN_URL"] = (os.environ.get("OIDC_POST_LOGIN_URL") or "").strip()
    return values


def oidc_enabled() -> bool:
    return oidc_config() is not None


def fetch_discovery(issuer: str) -> dict[str, Any]:
    """The issuer's OpenID configuration, cached for the process lifetime."""
    if issuer not in _DISCOVERY_CACHE:
        url = issuer.rstrip("/") + "/.well-known/openid-configuration"
        with urllib.request.urlopen(url, timeout=10) as resp:  # noqa: S310 — env-configured issuer
            _DISCOVERY_CACHE[issuer] = json.loads(resp.read())
    return _DISCOVERY_CACHE[issuer]


def exchange_code(token_endpoint: str, code: str, cfg: dict[str, str]) -> dict[str, Any]:
    """Authorization code -> tokens, via the IdP's token endpoint."""
    body = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "code": code,
        "client_id": cfg["OIDC_CLIENT_ID"],
        "client_secret": cfg["OIDC_CLIENT_SECRET"],
        "redirect_uri": cfg["OIDC_REDIRECT_URI"],
    }).encode()
    req = urllib.request.Request(
        token_endpoint, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        return json.loads(resp.read())


def verify_id_token(id_token: str, jwks_uri: str, client_id: str, issuer: str) -> dict[str, Any]:
    """RS256 verification against the IdP's JWKS; audience and issuer enforced."""
    signing_key = jwt.PyJWKClient(jwks_uri).get_signing_key_from_jwt(id_token)
    return jwt.decode(
        id_token, signing_key.key, algorithms=["RS256"],
        audience=client_id, issuer=issuer)


# --- signed state (CSRF binding between /login and /callback) ----------------------

def make_state() -> str:
    return jwt.encode(
        {"nonce": secrets.token_urlsafe(16), "exp": int(time.time()) + _STATE_TTL_SECONDS,
         "purpose": "oidc-state"},
        jwt_secret(), algorithm="HS256")


def verify_state(state: str) -> bool:
    try:
        claims = jwt.decode(state, jwt_secret(), algorithms=["HS256"])
        return claims.get("purpose") == "oidc-state"
    except jwt.PyJWTError:
        return False


def claims_email(claims: dict[str, Any]) -> str | None:
    """Azure puts the address in `email` or `preferred_username` depending on setup."""
    for key in ("email", "preferred_username", "upn"):
        value = (claims.get(key) or "").strip().lower()
        if "@" in value:
            return value
    return None
