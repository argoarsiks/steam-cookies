import base64
import json
import time

import pytest

from steam_cookies.exceptions import InvalidTokenError
from steam_cookies.token_claims import (
    decode_token_payload,
    get_steamid_from_token,
    is_token_expired,
)


def _make_token(payload: dict, header: dict | None = None) -> str:
    def b64url(obj: dict) -> str:
        raw = json.dumps(obj).encode("utf-8")
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    return f"{b64url(header or {'alg': 'none'})}.{b64url(payload)}.unsigned"


def test_decode_token_payload_reads_the_middle_segment() -> None:
    token = _make_token({"sub": "76561198000000000", "exp": 123})

    assert decode_token_payload(token) == {"sub": "76561198000000000", "exp": 123}


def test_decode_token_payload_rejects_non_jwt_strings() -> None:
    with pytest.raises(InvalidTokenError, match="Not a JWT"):
        decode_token_payload("not-a-jwt")


def test_decode_token_payload_rejects_unparsable_payload_segment() -> None:
    with pytest.raises(InvalidTokenError):
        decode_token_payload("header.%%%not-base64%%%.sig")


def test_get_steamid_from_token_reads_the_sub_claim() -> None:
    token = _make_token({"sub": "76561198000000000"})

    assert get_steamid_from_token(token) == 76561198000000000


def test_get_steamid_from_token_requires_a_sub_claim() -> None:
    token = _make_token({"exp": 123})

    with pytest.raises(InvalidTokenError, match="no 'sub' claim"):
        get_steamid_from_token(token)


def test_get_steamid_from_token_requires_a_numeric_sub_claim() -> None:
    token = _make_token({"sub": "not-a-number"})

    with pytest.raises(InvalidTokenError, match="not a valid SteamID"):
        get_steamid_from_token(token)


def test_is_token_expired_true_when_exp_in_the_past() -> None:
    token = _make_token({"sub": "1", "exp": time.time() - 3600})

    assert is_token_expired(token) is True


def test_is_token_expired_false_when_exp_in_the_future() -> None:
    token = _make_token({"sub": "1", "exp": time.time() + 3600})

    assert is_token_expired(token) is False


def test_is_token_expired_false_when_no_exp_claim() -> None:
    token = _make_token({"sub": "1"})

    assert is_token_expired(token) is False
