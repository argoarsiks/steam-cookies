from steam_cookies.schemas import GenerateAccessTokenForAppResponse, SteamWebCookies


def test_generate_access_token_response_defaults_to_none() -> None:
    response = GenerateAccessTokenForAppResponse.model_validate({})

    assert response.access_token is None
    assert response.refresh_token is None


def test_generate_access_token_response_reads_the_access_token() -> None:
    response = GenerateAccessTokenForAppResponse.model_validate({"access_token": "abc123"})

    assert response.access_token == "abc123"


def test_steam_web_cookies_as_dict_maps_to_the_cookie_names() -> None:
    cookies = SteamWebCookies(
        steamid=76561198000000000,
        steam_login_secure="76561198000000000||token",
        session_id="deadbeef",
    )

    assert cookies.as_dict() == {
        "steamLoginSecure": "76561198000000000||token",
        "sessionid": "deadbeef",
    }
