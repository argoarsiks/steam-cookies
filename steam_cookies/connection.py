"""Async TCP connection to a Steam CM server with the Connection-level wire
framing (``length + b"VT01"`` prefix, see ``framing.py``).
"""

import asyncio

from steam_cookies import framing
from steam_cookies.exceptions import SteamConnectionError


class CMConnection:
    def __init__(self) -> None:
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None

    async def connect(self, host: str, port: int, timeout: float = 10.0) -> None:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout
        )

    async def close(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError:
                pass
        self._reader = None
        self._writer = None

    async def send(self, message: bytes) -> None:
        if self._writer is None:
            raise SteamConnectionError("Not connected")

        self._writer.write(framing.wrap_connection_frame(message))
        await self._writer.drain()

    async def recv(self, timeout: float = 30.0) -> bytes:
        """Read exactly one framed message and return its payload."""
        if self._reader is None:
            raise SteamConnectionError("Not connected")

        try:
            header = await asyncio.wait_for(
                self._reader.readexactly(framing.CONN_HEADER_SIZE), timeout
            )
        except asyncio.IncompleteReadError as exc:
            raise SteamConnectionError("Connection closed while reading header") from exc

        length, magic = framing.parse_connection_header(header)
        if magic != framing.MAGIC:
            raise SteamConnectionError(f"Bad frame magic: {magic!r}")

        try:
            return await asyncio.wait_for(self._reader.readexactly(length), timeout)
        except asyncio.IncompleteReadError as exc:
            raise SteamConnectionError("Connection closed while reading body") from exc
