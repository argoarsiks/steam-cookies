"""Unit tests for CMConnection's framing behaviour.

These inject fake/in-memory reader and writer objects directly (rather than
opening a real socket) so the tests exercise the connection-framing logic
without touching the network.
"""

import asyncio
import struct

import pytest

from steam_cookies import framing
from steam_cookies.connection import CMConnection
from steam_cookies.exceptions import SteamConnectionError


class _FakeWriter:
    def __init__(self) -> None:
        self.buffer = bytearray()
        self.closed = False

    def write(self, data: bytes) -> None:
        self.buffer += data

    async def drain(self) -> None:
        pass

    def close(self) -> None:
        self.closed = True

    async def wait_closed(self) -> None:
        pass


async def test_send_without_a_connection_raises() -> None:
    conn = CMConnection()

    with pytest.raises(SteamConnectionError, match="Not connected"):
        await conn.send(b"hi")


async def test_recv_without_a_connection_raises() -> None:
    conn = CMConnection()

    with pytest.raises(SteamConnectionError, match="Not connected"):
        await conn.recv()


async def test_send_wraps_the_message_in_a_connection_frame() -> None:
    conn = CMConnection()
    writer = _FakeWriter()
    conn._writer = writer  # type: ignore[assignment]

    await conn.send(b"payload")

    assert bytes(writer.buffer) == framing.wrap_connection_frame(b"payload")


async def test_recv_returns_the_framed_payload() -> None:
    conn = CMConnection()
    reader = asyncio.StreamReader()
    reader.feed_data(framing.wrap_connection_frame(b"hello"))
    reader.feed_eof()
    conn._reader = reader  # type: ignore[assignment]

    assert await conn.recv() == b"hello"


async def test_recv_rejects_a_bad_magic() -> None:
    conn = CMConnection()
    reader = asyncio.StreamReader()
    reader.feed_data(struct.pack("<I4s", 5, b"XXXX") + b"hello")
    reader.feed_eof()
    conn._reader = reader  # type: ignore[assignment]

    with pytest.raises(SteamConnectionError, match="Bad frame magic"):
        await conn.recv()


async def test_recv_raises_on_connection_closed_mid_header() -> None:
    conn = CMConnection()
    reader = asyncio.StreamReader()
    reader.feed_data(b"\x01\x02")  # shorter than the connection header
    reader.feed_eof()
    conn._reader = reader  # type: ignore[assignment]

    with pytest.raises(SteamConnectionError, match="closed while reading header"):
        await conn.recv()


async def test_recv_raises_on_connection_closed_mid_body() -> None:
    conn = CMConnection()
    reader = asyncio.StreamReader()
    header = struct.pack("<I4s", 10, framing.MAGIC)
    reader.feed_data(header + b"short")  # declares 10 bytes, only 5 follow
    reader.feed_eof()
    conn._reader = reader  # type: ignore[assignment]

    with pytest.raises(SteamConnectionError, match="closed while reading body"):
        await conn.recv()


async def test_close_resets_reader_and_writer() -> None:
    conn = CMConnection()
    conn._writer = _FakeWriter()  # type: ignore[assignment]
    conn._reader = asyncio.StreamReader()  # type: ignore[assignment]

    await conn.close()

    with pytest.raises(SteamConnectionError):
        await conn.send(b"x")
    with pytest.raises(SteamConnectionError):
        await conn.recv()
