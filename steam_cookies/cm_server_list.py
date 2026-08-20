"""Bootstrap the list of CM (Connection Manager) TCP servers to connect to.

Same public, unauthenticated WebAPI call the official client makes
(``ISteamDirectory/GetCMListForConnect``), filtered to plain TCP
(``netfilter``) servers in the public realm.
"""

import random
from typing import Any

import httpx

from steam_cookies.exceptions import SteamConnectionError

_GET_CM_LIST_URL = "https://api.steampowered.com/ISteamDirectory/GetCMListForConnect/v1/"


async def fetch_cm_servers(cell_id: int = 0, timeout: float = 10.0) -> list[tuple[str, int]]:
    """Return a shuffled list of ``(host, port)`` TCP CM server candidates."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            response = await client.get(
                _GET_CM_LIST_URL,
                params={"cellid": cell_id, "cmtype": "netfilter", "format": "json"},
            )
            response.raise_for_status()
        except Exception as exc:
            # Some httpx/network exceptions stringify to "" on Windows - always
            # include the exception type so the error stays diagnosable.
            detail = str(exc) or repr(exc)
            raise SteamConnectionError(
                f"GetCMListForConnect request failed: {type(exc).__name__}: {detail}"
            ) from exc

        data: dict[str, Any] = response.json()

    servers: list[dict[str, Any]] = data.get("response", {}).get("serverlist", [])
    candidates = [
        server["endpoint"]
        for server in servers
        if server.get("realm") == "steamglobal" and server.get("type") == "netfilter"
    ]

    if not candidates:
        raise SteamConnectionError("GetCMListForConnect returned no usable TCP (netfilter) servers")

    random.shuffle(candidates)

    result: list[tuple[str, int]] = []
    for endpoint in candidates:
        host, _, port = endpoint.rpartition(":")
        result.append((host, int(port)))

    return result
