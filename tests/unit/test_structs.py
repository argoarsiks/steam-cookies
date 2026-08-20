import struct

from steam_cookies.structs import (
    ChannelEncryptRequest,
    ChannelEncryptResponse,
    ChannelEncryptResult,
    RawMsgHeader,
)


def test_raw_msg_header_round_trips_through_serialize_and_load() -> None:
    header = RawMsgHeader(msg=1303, target_job_id=11, source_job_id=22)

    loaded = RawMsgHeader.load(header.serialize())

    assert loaded == header


def test_raw_msg_header_defaults_job_ids_to_minus_one() -> None:
    header = RawMsgHeader(msg=1303)

    assert header.target_job_id == -1
    assert header.source_job_id == -1


def test_raw_msg_header_size_matches_the_wire_layout() -> None:
    assert RawMsgHeader.SIZE == struct.calcsize("<Iqq")
    assert len(RawMsgHeader(msg=1).serialize()) == RawMsgHeader.SIZE


def test_channel_encrypt_request_load_parses_version_universe_and_challenge() -> None:
    data = struct.pack("<II", 1, 0) + b"challenge-bytes"

    request = ChannelEncryptRequest.load(data)

    assert request.protocol_version == 1
    assert request.universe == 0
    assert request.challenge == b"challenge-bytes"


def test_channel_encrypt_request_load_handles_no_challenge() -> None:
    data = struct.pack("<II", 1, 0)

    request = ChannelEncryptRequest.load(data)

    assert request.challenge == b""


def test_channel_encrypt_response_serialize_packs_key_and_crc() -> None:
    key = bytes(range(128))

    data = ChannelEncryptResponse(key=key, crc=0xDEADBEEF).serialize()
    protocol_version, key_size, packed_key, crc, _trailer = struct.unpack("<II128sII", data)

    assert protocol_version == 1
    assert key_size == 128
    assert packed_key == key
    assert crc == 0xDEADBEEF


def test_channel_encrypt_result_load_parses_eresult() -> None:
    data = struct.pack("<I", 1)

    assert ChannelEncryptResult.load(data).eresult == 1
