# steam-cookies

Get Steam web session cookies (`steamLoginSecure`) from a desktop/mobile refresh token —
either via a public REST call, or via a real CM (Connection Manager) session as a fallback
if the REST call gets rejected.

## Install

```bash
pip install steam-cookies
# Windows-only, only needed for `extract-token`:
pip install "steam-cookies[local-client]"
```

## CLI

```bash
steam-cookies rest <refresh_token>
steam-cookies cm <refresh_token> <account_name>
steam-cookies extract-token <account_name>   # Windows only, reads the local Steam client's storage
```

`account_name` is the account's login name, not its persona/display name.

## Library

```python
from steam_cookies import SteamCMClient, SteamWebSessionClient

async with SteamWebSessionClient() as client:
    cookies = await client.get_web_cookies(refresh_token)

# or, when the REST path gets rejected for the calling network:
async with SteamCMClient() as client:
    cookies = await client.get_web_cookies(refresh_token, account_name)

cookies.as_dict()  # {"steamLoginSecure": ..., "sessionid": ...}
```