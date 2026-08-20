"""Public, unauthenticated REST path: a single call to
``IAuthenticationService/GenerateAccessTokenForApp``. What the official Steam
client does for desktop/mobile refresh tokens - no CM connection, no
``finalizelogin`` (that endpoint is only for web-platform tokens).

Steam's anti-abuse checks on this endpoint can reject an otherwise-valid
token depending on the calling network; ``cm_client.py`` provides a CM-native
fallback for that case.
"""

import secrets
from typing import Any

from httpx import AsyncClient, HTTPStatusError, Response, Timeout

from steam_cookies.exceptions import SteamConnectionError, SteamLogonError, SteamProtocolError
from steam_cookies.schemas import GenerateAccessTokenForAppResponse, SteamWebCookies
from steam_cookies.token_claims import get_steamid_from_token


class SteamWebSessionClient:
    """Turns a Steam desktop/mobile refresh token into web session cookies via
    the public REST endpoint.
    """

    BASE_URL: str = "https://api.steampowered.com"

    def __init__(self, timeout: float = 10.0) -> None:
        self._client: AsyncClient = AsyncClient(
            base_url=self.BASE_URL,
            timeout=Timeout(timeout),
            headers={"Referer": "https://steamcommunity.com"},
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "SteamWebSessionClient":
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.close()

    async def generate_access_token(self, refresh_token: str, steamid: int) -> str:
        """Call ``IAuthenticationService/GenerateAccessTokenForApp/v1``.

        :raises SteamLogonError: Steam rejected the token (an empty response
            body with an ``x-eresult`` header - HTTP 200, not an error status).
        :raises SteamConnectionError: the request itself failed.
        """
        data: dict[str, Any] = {"refresh_token": refresh_token, "steamid": steamid}

        try:
            response: Response = await self._client.post(
                "/IAuthenticationService/GenerateAccessTokenForApp/v1/", data=data
            )
            response.raise_for_status()
        except HTTPStatusError as exc:
            raise SteamConnectionError(
                f"GenerateAccessTokenForApp failed with status {exc.response.status_code}"
            ) from exc
        except Exception as exc:
            detail = str(exc) or repr(exc)
            raise SteamConnectionError(
                f"GenerateAccessTokenForApp request failed: {type(exc).__name__}: {detail}"
            ) from exc

        body = response.json().get("response", {})
        parsed = GenerateAccessTokenForAppResponse.model_validate(body)

        if not parsed.access_token:
            eresult_header = response.headers.get("x-eresult")
            if eresult_header is not None:
                raise SteamLogonError(int(eresult_header), "GenerateAccessTokenForApp")
            raise SteamProtocolError("GenerateAccessTokenForApp returned an empty response")

        return parsed.access_token

    async def get_web_cookies(self, refresh_token: str) -> SteamWebCookies:
        """Exchange a desktop/mobile refresh token for web session cookies."""
        steamid = get_steamid_from_token(refresh_token)
        access_token = await self.generate_access_token(refresh_token, steamid)

        return SteamWebCookies(
            steamid=steamid,
            steam_login_secure=f"{steamid}||{access_token}",
            session_id=secrets.token_hex(12),
        )
