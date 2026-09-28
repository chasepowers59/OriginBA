"""OIDC single sign-on — the enterprise gate (Azure AD / Entra is the utility default).

Generic authorization-code flow, config entirely from env:

    OIDC_ISSUER                 https://login.microsoftonline.com/<tenant>/v2.0
    OIDC_CLIENT_ID              app registration's client id
    OIDC_CLIENT_SECRET          client secret
    OIDC_REDIRECT_URI           this API's /auth/oidc/callback URL (registered at the IdP)
    OIDC_DEFAULT_ORGANIZATION   org for just-in-time provisioned users
    OIDC_POST_LOGIN_URL         the SPA login page; receives #sso_token=<our JWT>
    OIDC_GROUP_MAP              optional JSON: IdP groups -> role, organization, access groups,
                                row rules; access then follows the groups at every sign-in
    OIDC_GROUPS_CLAIM           the claim carrying groups ("groups" by default; Entra: "roles")

No new dependencies: stdlib urllib for the two IdP calls, PyJWT (+cryptography, already
shipped) for RS256 id_token verification via the IdP's JWKS. Users are JIT-provisioned
on first login as role `user` in the default org — an admin promotes from there — unless
OIDC_GROUP_MAP says otherwise. SSO never mints admins. The SPA receives OUR access token (same shape as password login) in
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
from api.row_security import clean_rules

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


# ---------------------------------------------------------------- group mapping
# OIDC_GROUP_MAP: JSON list of {group, role, organization_id, access_groups?, row_rules?}.
# With it set, a person's portal access follows their identity-provider groups at every
# sign-in (tests/test_oidc_group_map.py). The map never grants admin.
_ROLE_RANK = {"user": 0, "editor": 1}


class SsoAccessError(Exception):
    def __init__(self, message: str, *, revoke: bool = False):
        super().__init__(message)
        self.revoke = revoke   # the person is in no mapped group: their account is switched off


def group_map() -> list[dict[str, Any]] | None:
    raw = (os.environ.get("OIDC_GROUP_MAP") or "").strip()
    if not raw:
        return None
    try:
        mapping = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SsoAccessError("OIDC_GROUP_MAP is not valid JSON") from exc
    if not isinstance(mapping, list):
        raise SsoAccessError("OIDC_GROUP_MAP must be a list of group rules")
    return mapping


def groups_claim_name() -> str:
    return (os.environ.get("OIDC_GROUPS_CLAIM") or "groups").strip()


def mapped_access(claims: dict[str, Any], mapping: list[dict[str, Any]], claim: str) -> dict[str, Any]:
    """The access a person's groups give: the highest role among matching rules (admin never
    granted), their one organization, and the union of access groups and row rules. Row rules
    are None when no matching group at that role declares any."""
    raw = claims.get(claim) or []
    if isinstance(raw, str):
        groups = {raw}
    elif isinstance(raw, list) and all(isinstance(g, str) for g in raw):
        groups = set(raw)
    else:
        raise SsoAccessError("Your sign-in carried its groups in a form the portal cannot read. "
                             "Ask your administrator to check the groups claim.")
    matched = [r for r in mapping if r.get("group") in groups and r.get("role") in _ROLE_RANK]
    if not matched:
        raise SsoAccessError("Your account is not in a group that has access to the portal. "
                             "Ask your administrator to add you to one.", revoke=True)
    orgs = {r.get("organization_id") for r in matched if r.get("organization_id")}
    if len(orgs) > 1:
        raise SsoAccessError("Your sign-in groups give access to more than one client. "
                             "Ask your administrator to keep you in one.")
    best = max(matched, key=lambda r: _ROLE_RANK[r["role"]])
    at_best = [r for r in matched if r["role"] == best["role"]]
    rules = None
    if any("row_rules" in r for r in at_best):
        try:
            rules = clean_rules([rule for r in at_best for rule in (r.get("row_rules") or [])])
        except ValueError as exc:
            raise SsoAccessError("The portal's sign-in group map has a row rule it cannot apply. "
                                 "Ask your administrator to correct it.") from exc
    return {"role": best["role"], "organization_id": next(iter(orgs), None),
            "access_groups": sorted({g for r in matched for g in (r.get("access_groups") or [])}),
            "row_rules": rules}
