"""Get Steam web session cookies (``steamLoginSecure``) from a desktop/mobile
refresh token - never via ``finalizelogin`` (web-platform tokens only) or a
paid third-party API.

Two ways to exchange the token, both producing a :class:`SteamWebCookies` from a
``get_web_cookies(refresh_token, ...)`` call on an async-context-managed client:

- :class:`SteamWebSessionClient` - a single public REST call to
  ``IAuthenticationService/GenerateAccessTokenForApp``. What the official
  client does for desktop/mobile tokens, but Steam's anti-abuse checks on
  that endpoint can reject an otherwise-valid token depending on the calling
  network.
- :class:`SteamCMClient` - a real CM (Connection Manager) session: TCP
  connect, RSA/AES channel handshake, log on with the refresh token, call the
  same RPC over the authenticated channel instead of as a bare REST call.
  :func:`get_web_cookies_via_cm` is a one-line convenience wrapper around it.
"""

from steam_cookies.client import SteamWebSessionClient
from steam_cookies.cm_client import SteamCMClient, get_web_cookies_via_cm
from steam_cookies.exceptions import (
    InvalidTokenError,
    SteamConnectionError,
    SteamCookiesError,
    SteamLogonError,
    SteamProtocolError,
)
from steam_cookies.schemas import SteamWebCookies

__all__ = [
    "InvalidTokenError",
    "SteamCMClient",
    "SteamConnectionError",
    "SteamCookiesError",
    "SteamLogonError",
    "SteamProtocolError",
    "SteamWebCookies",
    "SteamWebSessionClient",
    "get_web_cookies_via_cm",
]
