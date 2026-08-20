"""Wire framing for the CM TCP protocol.

Two layers:

- Connection framing: every message on the wire is prefixed with
  ``length (u32 LE) + magic (4 bytes, b"VT01")``.
- App-message framing: a protobuf message's payload (after the connection-level
  prefix is stripped, and after decryption once the channel is secured) is
  ``emsg_with_proto_bit (u32 LE) + header_len (u32 LE) + CMsgProtoBufHeader + body``.
"""

import struct

from steam_cookies import emsg as emsg_mod
from steam_cookies.exceptions import SteamProtocolError
from steam_cookies.proto import CMsgProtoBufHeader

MAGIC = b"VT01"
_CONN_HEADER_FMT = "<I4s"
CONN_HEADER_SIZE = struct.calcsize(_CONN_HEADER_FMT)

_PROTO_HDR_PREFIX_FMT = "<II"
_PROTO_HDR_PREFIX_SIZE = struct.calcsize(_PROTO_HDR_PREFIX_FMT)


def wrap_connection_frame(message: bytes) -> bytes:
    return struct.pack(_CONN_HEADER_FMT, len(message), MAGIC) + message


def parse_connection_header(data: bytes) -> tuple[int, bytes]:
    length, magic = struct.unpack_from(_CONN_HEADER_FMT, data)
    return length, magic


def serialize_proto_message(emsg: int, header: CMsgProtoBufHeader, body: bytes) -> bytes:
    header_bytes = header.SerializeToString()
    return (
        struct.pack(_PROTO_HDR_PREFIX_FMT, emsg_mod.set_proto_bit(emsg), len(header_bytes))
        + header_bytes
        + body
    )


def parse_proto_message(data: bytes) -> tuple[int, CMsgProtoBufHeader, bytes]:
    """:raises SteamProtocolError: ``data`` isn't a well-formed protobuf app
    message (proto bit not set, or the declared header length doesn't fit
    the buffer) - happens for non-proto legacy messages, which this
    client doesn't otherwise handle; callers should skip it.
    """
    if len(data) < _PROTO_HDR_PREFIX_SIZE:
        raise SteamProtocolError(f"Message too short for a proto header prefix: {len(data)} bytes")

    raw_emsg, header_len = struct.unpack_from(_PROTO_HDR_PREFIX_FMT, data)

    if not emsg_mod.is_proto(raw_emsg):
        raise SteamProtocolError(f"Message emsg={raw_emsg} has no proto bit set")

    emsg = emsg_mod.clear_proto_bit(raw_emsg)

    header_start = _PROTO_HDR_PREFIX_SIZE
    header_end = header_start + header_len
    if header_len < 0 or header_end > len(data):
        raise SteamProtocolError(
            f"Declared header_len={header_len} doesn't fit in {len(data) - header_start} "
            "remaining bytes"
        )

    header = CMsgProtoBufHeader()
    header.ParseFromString(data[header_start:header_end])

    body = data[header_end:]
    return emsg, header, body
