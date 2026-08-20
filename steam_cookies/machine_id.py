"""Builds the binary-KeyValue ``machine_id`` blob Steam expects in
``CMsgClientLogon.machine_id`` for any non-anonymous logon.

Format: a root ``MessageObject`` with three string children ``BB3``/``FF2``/
``3B3``, each holding a hex SHA1 digest.
"""

import hashlib


def _sha1_hex(value: str) -> bytes:
    return hashlib.sha1(value.encode("utf-8")).hexdigest().encode("ascii") + b"\x00"  # noqa: S324


def _cstring(value: str) -> bytes:
    return value.encode("utf-8") + b"\x00"


def build_machine_id(bb3: str, ff2: str, three_b3: str) -> bytes:
    buf = bytearray()
    buf += b"\x00" + _cstring("MessageObject")  # type 0 = nested object start

    buf += b"\x01" + _cstring("BB3") + _sha1_hex(bb3)  # type 1 = string
    buf += b"\x01" + _cstring("FF2") + _sha1_hex(ff2)
    buf += b"\x01" + _cstring("3B3") + _sha1_hex(three_b3)

    buf += b"\x08\x08"  # type 8 = end of object (child, then root)

    return bytes(buf)
