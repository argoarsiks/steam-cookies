import hashlib

from steam_cookies.machine_id import build_machine_id


def _expected(bb3: str, ff2: str, three_b3: str) -> bytes:
    def sha1_hex(value: str) -> bytes:
        return hashlib.sha1(value.encode("utf-8")).hexdigest().encode("ascii") + b"\x00"

    buf = bytearray()
    buf += b"\x00" + b"MessageObject\x00"
    buf += b"\x01" + b"BB3\x00" + sha1_hex(bb3)
    buf += b"\x01" + b"FF2\x00" + sha1_hex(ff2)
    buf += b"\x01" + b"3B3\x00" + sha1_hex(three_b3)
    buf += b"\x08\x08"
    return bytes(buf)


def test_build_machine_id_matches_the_expected_binary_kv_layout() -> None:
    blob = build_machine_id("bb3-seed", "ff2-seed", "3b3-seed")

    assert blob == _expected("bb3-seed", "ff2-seed", "3b3-seed")


def test_build_machine_id_is_deterministic() -> None:
    assert build_machine_id("a", "b", "c") == build_machine_id("a", "b", "c")


def test_build_machine_id_differs_for_different_input() -> None:
    assert build_machine_id("a", "b", "c") != build_machine_id("a", "b", "d")


def test_build_machine_id_embeds_hex_sha1_digests() -> None:
    blob = build_machine_id("seed-bb3", "seed-ff2", "seed-3b3")

    assert hashlib.sha1(b"seed-bb3").hexdigest().encode("ascii") in blob
    assert hashlib.sha1(b"seed-ff2").hexdigest().encode("ascii") in blob
    assert hashlib.sha1(b"seed-3b3").hexdigest().encode("ascii") in blob
