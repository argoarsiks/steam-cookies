"""Windows-only: read the currently-active refresh token straight out of the
local Steam desktop client's storage, without spending it.

Steam stores it DPAPI-encrypted in ``%LOCALAPPDATA%\\Steam\\local.vdf`` under
``MachineUserConfigStore.Software.Valve.Steam.ConnectCache``, keyed by
``crc32(account_name)``. DPAPI decryption only works under the same Windows
user account that encrypted it, so this can't run remotely or against
another machine.

This only reads and decrypts; it never modifies ``local.vdf`` or talks to
Steam or the network.

Requires ``pywin32`` and ``vdf`` (the ``local-client`` extra) - imported lazily
so the rest of the package works without them on non-Windows platforms.
"""

import os
import zlib

from steam_cookies.exceptions import SteamCookiesError


class LocalTokenNotFoundError(SteamCookiesError):
    """No matching, decryptable ConnectCache entry was found."""


def _local_vdf_path() -> str:
    return os.path.join(os.getenv("LOCALAPPDATA", ""), "Steam", "local.vdf")


def _connect_cache_key(account_name: str) -> str:
    value = zlib.crc32(account_name.encode("utf-8"))
    hex_value = f"{value:08x}".lstrip("0") or "0"
    return f"{hex_value}1"


def read_local_refresh_token(account_name: str) -> str:
    """Read and decrypt ``account_name``'s refresh token from the local Steam
    client's ``ConnectCache``.

    :param account_name: the account's login name (not persona/display name).
    :raises LocalTokenNotFoundError: ``local.vdf``, its ``ConnectCache``
        section, or a matching entry for ``account_name`` doesn't exist.
    """
    try:
        import vdf
        import win32crypt
    except ImportError as exc:
        raise ImportError(
            "read_local_refresh_token requires the 'local-client' extra: "
            "pip install steam-cookies[local-client]"
        ) from exc

    account_name = account_name.lower()
    path = _local_vdf_path()
    if not os.path.exists(path):
        raise LocalTokenNotFoundError(f"Not found: {path}")

    with open(path, encoding="utf-8", errors="replace") as f:
        data = vdf.loads(f.read())

    try:
        connect_cache = data["MachineUserConfigStore"]["Software"]["Valve"]["Steam"]["ConnectCache"]
    except KeyError as exc:
        raise LocalTokenNotFoundError("No ConnectCache section in local.vdf") from exc

    key = _connect_cache_key(account_name)
    hex_blob = connect_cache.get(key)
    if not hex_blob:
        raise LocalTokenNotFoundError(
            f"No ConnectCache entry for account {account_name!r} (key {key!r})"
        )

    encrypted = bytes.fromhex(hex_blob)
    result = win32crypt.CryptUnprotectData(encrypted, account_name.encode("utf-8"), None, None, 0)

    # CryptUnprotectData returns (description, data) - pywin32 versions differ
    # on the order and on str vs bytes, so pick whichever part is JWT-shaped.
    for part in result:
        text = part.decode("utf-8") if isinstance(part, bytes) else part
        if isinstance(text, str) and text.count(".") == 2:
            return text

    raise LocalTokenNotFoundError(
        f"No JWT-shaped value in decrypted ConnectCache entry: {result!r}"
    )
