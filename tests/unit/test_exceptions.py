from steam_cookies.exceptions import (
    InvalidTokenError,
    SteamConnectionError,
    SteamCookiesError,
    SteamLogonError,
    SteamProtocolError,
)


def test_all_errors_derive_from_steam_cookies_error() -> None:
    assert issubclass(SteamConnectionError, SteamCookiesError)
    assert issubclass(SteamProtocolError, SteamCookiesError)
    assert issubclass(InvalidTokenError, SteamCookiesError)
    assert issubclass(SteamLogonError, SteamCookiesError)


def test_invalid_token_error_is_also_a_value_error() -> None:
    # so callers doing `except ValueError` (e.g. around int()-like parsing)
    # catch malformed tokens too.
    assert issubclass(InvalidTokenError, ValueError)


def test_steam_logon_error_resolves_the_eresult_name() -> None:
    exc = SteamLogonError(5, "Logon")

    assert exc.eresult == 5
    assert exc.eresult_name == "InvalidPassword"
    assert str(exc) == "Logon failed: InvalidPassword (5)"


def test_steam_logon_error_falls_back_for_unknown_eresult() -> None:
    exc = SteamLogonError(424242, "GenerateAccessTokenForApp")

    assert exc.eresult_name == "Unknown(424242)"
    assert "424242" in str(exc)
