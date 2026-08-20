import struct

import pytest

from steam_cookies import emsg as emsg_mod
from steam_cookies.exceptions import SteamProtocolError
from steam_cookies.framing import (
    CONN_HEADER_SIZE,
    MAGIC,
    parse_connection_header,
    parse_proto_message,
    serialize_proto_message,
    wrap_connection_frame,
)
from steam_cookies.proto import CMsgProtoBufHeader


def test_wrap_connection_frame_prefixes_length_and_magic() -> None:
    framed = wrap_connection_frame(b"hello")

    assert framed == struct.pack("<I4s", 5, MAGIC) + b"hello"


def test_parse_connection_header_round_trips_with_wrap() -> None:
    framed = wrap_connection_frame(b"hello world")

    length, magic = parse_connection_header(framed[:CONN_HEADER_SIZE])

    assert length == len(b"hello world")
    assert magic == MAGIC


def test_serialize_and_parse_proto_message_round_trip() -> None:
    header = CMsgProtoBufHeader()
    header.steamid = 76561198000000000
    header.client_sessionid = 42

    data = serialize_proto_message(emsg_mod.EMSG_CLIENT_LOGON, header, b"body-bytes")
    emsg, parsed_header, body = parse_proto_message(data)

    assert emsg == emsg_mod.EMSG_CLIENT_LOGON
    assert parsed_header.steamid == 76561198000000000
    assert parsed_header.client_sessionid == 42
    assert body == b"body-bytes"


def test_serialize_proto_message_always_sets_the_proto_bit() -> None:
    header = CMsgProtoBufHeader()

    data = serialize_proto_message(emsg_mod.EMSG_CLIENT_LOGON, header, b"")
    (raw_emsg,) = struct.unpack_from("<I", data)

    assert emsg_mod.is_proto(raw_emsg)


def test_parse_proto_message_rejects_too_short_payload() -> None:
    with pytest.raises(SteamProtocolError):
        parse_proto_message(b"\x00\x00\x00")


def test_parse_proto_message_rejects_missing_proto_bit() -> None:
    # A well-formed prefix but with the proto bit cleared - looks like a
    # legacy, non-proto message this client doesn't handle.
    data = struct.pack("<II", emsg_mod.EMSG_CLIENT_LOGON, 0)

    with pytest.raises(SteamProtocolError):
        parse_proto_message(data)


def test_parse_proto_message_rejects_header_len_overrunning_buffer() -> None:
    data = struct.pack("<II", emsg_mod.set_proto_bit(emsg_mod.EMSG_CLIENT_LOGON), 100) + b"short"

    with pytest.raises(SteamProtocolError):
        parse_proto_message(data)
