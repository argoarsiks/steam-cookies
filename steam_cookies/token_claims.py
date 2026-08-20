"""Unverified decoding of a Steam refresh/access token's JWT payload.

We don't have Steam's signing key, and don't need it - we only read claims
(steamid, expiry) out of a token we already trust the source of.
"""

import base64
import json
import time
from typing import Any

from steam_cookies.exceptions import InvalidTokenError


def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def decode_token_payload(token: str) -> dict[str, Any]:
    """Decode the (unverified) payload segment of a JWT.

    :raises InvalidTokenError: ``token`` isn't a well-formed JWT.
    """
    parts = token.split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Not a JWT: expected 3 dot-separated segments")

    try:
        payload: dict[str, Any] = json.loads(_b64url_decode(parts[1]))
    except Exception as exc:
        raise InvalidTokenError(f"Could not decode JWT payload: {exc}") from exc

    return payload


def get_steamid_from_token(token: str) -> int:
    """Extract the SteamID64 from a refresh/access token's ``sub`` claim.

    :raises InvalidTokenError: the token is malformed or has no ``sub`` claim.
    """
    payload = decode_token_payload(token)
    sub = payload.get("sub")
    if sub is None:
        raise InvalidTokenError("Token payload has no 'sub' claim")

    try:
        return int(sub)
    except (TypeError, ValueError) as exc:
        raise InvalidTokenError(f"Token 'sub' claim is not a valid SteamID: {sub!r}") from exc


def is_token_expired(token: str) -> bool:
    """Check the token's ``exp`` claim against the current time."""
    payload = decode_token_payload(token)
    exp = payload.get("exp")
    if exp is None:
        return False
    return time.time() >= float(exp)
