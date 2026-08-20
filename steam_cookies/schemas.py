from pydantic import BaseModel


class GenerateAccessTokenForAppResponse(BaseModel):
    """``CAuthentication_AccessToken_GenerateForApp_Response``."""

    access_token: str | None = None
    refresh_token: str | None = None


class SteamWebCookies(BaseModel):
    """Cookies ready to drop into a ``requests``/``httpx`` session for
    ``steamcommunity.com`` / ``store.steampowered.com`` / ``help.steampowered.com``.
    """

    steamid: int
    steam_login_secure: str
    session_id: str

    def as_dict(self) -> dict[str, str]:
        return {
            "steamLoginSecure": self.steam_login_secure,
            "sessionid": self.session_id,
        }
