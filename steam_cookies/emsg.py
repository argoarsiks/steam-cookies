"""EMsg numbers used by the CM client, and the proto-bit helpers.

Values taken from ``protobufs/enums_clientserver.proto``.
"""

PROTO_MASK = 0x80000000

EMSG_MULTI = 1
EMSG_CHANNEL_ENCRYPT_REQUEST = 1303
EMSG_CHANNEL_ENCRYPT_RESPONSE = 1304
EMSG_CHANNEL_ENCRYPT_RESULT = 1305
EMSG_CLIENT_LOGON = 5514
EMSG_CLIENT_LOGON_RESPONSE = 751
EMSG_CLIENT_LOG_OFF = 706
EMSG_SERVICE_METHOD_RESPONSE = 147
EMSG_SERVICE_METHOD_CALL_FROM_CLIENT = 151


def is_proto(emsg: int) -> bool:
    return (emsg & PROTO_MASK) != 0


def set_proto_bit(emsg: int) -> int:
    return emsg | PROTO_MASK


def clear_proto_bit(emsg: int) -> int:
    return emsg & ~PROTO_MASK
