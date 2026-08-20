from steam_cookies.emsg import (
    PROTO_MASK,
    clear_proto_bit,
    is_proto,
    set_proto_bit,
)


def test_set_proto_bit_sets_the_high_bit() -> None:
    assert set_proto_bit(751) == 751 | PROTO_MASK


def test_is_proto_reflects_the_high_bit() -> None:
    assert is_proto(set_proto_bit(751)) is True
    assert is_proto(751) is False


def test_clear_proto_bit_undoes_set_proto_bit() -> None:
    emsg = 751
    assert clear_proto_bit(set_proto_bit(emsg)) == emsg


def test_clear_proto_bit_is_a_no_op_without_the_bit() -> None:
    assert clear_proto_bit(751) == 751
