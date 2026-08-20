"""Exception hierarchy for steam_cookies."""

from steam_cookies.eresult import eresult_name


class SteamCookiesError(Exception):
    """Base class for every error this library raises."""


class SteamConnectionError(SteamCookiesError):
    """Steam (a WebAPI endpoint or a CM server) could not be reached."""


class SteamProtocolError(SteamCookiesError):
    """Steam responded, but not in a way this client understands."""


class InvalidTokenError(SteamCookiesError, ValueError):
    """The provided string isn't a well-formed Steam refresh/access token."""


class SteamLogonError(SteamCookiesError):
    """Steam rejected a logon or RPC call with a specific EResult.

    Raised for both the REST path (from the ``x-eresult`` response header)
    and the CM path (from a message's ``eresult`` field), so callers only
    need to handle one exception type and inspect ``.eresult_name`` for the
    specific reason (e.g. ``"InvalidPassword"``, ``"AccessDenied"``).
    """

    def __init__(self, eresult: int, action: str) -> None:
        self.eresult = eresult
        self.eresult_name = eresult_name(eresult)
        super().__init__(f"{action} failed: {self.eresult_name} ({eresult})")
