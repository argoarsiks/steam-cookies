"""Plain (non-protobuf) struct messages used only during the pre-login channel
encryption handshake: ``ChannelEncryptRequest``/``Response``/``Result``.

These predate protobuf in the Steam protocol and are still sent as raw structs
even on modern protobuf-only connections.
"""

import struct
from dataclasses import dataclass


@dataclass
class RawMsgHeader:
    """The plain 20-byte header these struct messages carry:
    ``msg (4) + target_job_id (8) + source_job_id (8)``.
    """

    SIZE = struct.calcsize("<Iqq")

    msg: int
    target_job_id: int = -1
    source_job_id: int = -1

    def serialize(self) -> bytes:
        return struct.pack("<Iqq", self.msg, self.target_job_id, self.source_job_id)

    @classmethod
    def load(cls, data: bytes) -> "RawMsgHeader":
        msg, target_job_id, source_job_id = struct.unpack_from("<Iqq", data)
        return cls(msg=msg, target_job_id=target_job_id, source_job_id=source_job_id)


@dataclass
class ChannelEncryptRequest:
    protocol_version: int = 1
    universe: int = 0
    challenge: bytes = b""

    @classmethod
    def load(cls, data: bytes) -> "ChannelEncryptRequest":
        protocol_version, universe = struct.unpack_from("<II", data)
        challenge = data[8:] if len(data) > 8 else b""
        return cls(protocol_version=protocol_version, universe=universe, challenge=challenge)


@dataclass
class ChannelEncryptResponse:
    key: bytes
    crc: int
    protocol_version: int = 1
    key_size: int = 128

    def serialize(self) -> bytes:
        return struct.pack("<II128sII", self.protocol_version, self.key_size, self.key, self.crc, 0)


@dataclass
class ChannelEncryptResult:
    eresult: int = 2

    @classmethod
    def load(cls, data: bytes) -> "ChannelEncryptResult":
        (eresult,) = struct.unpack_from("<I", data)
        return cls(eresult=eresult)


__all__ = [
    "ChannelEncryptRequest",
    "ChannelEncryptResponse",
    "ChannelEncryptResult",
    "RawMsgHeader",
]
