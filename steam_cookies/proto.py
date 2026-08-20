"""Loads the protoc-generated message classes.

``pb2/`` is generated from the .proto files in ``protobufs/`` via::

    python -m grpc_tools.protoc -I protobufs --python_out=steam_cookies/pb2 \\
        protobufs/steammessages_base.proto \\
        protobufs/steammessages_unified_base.steamclient.proto \\
        protobufs/enums.proto \\
        protobufs/steammessages_clientserver_login.proto \\
        protobufs/steammessages_clientserver_2.proto \\
        protobufs/steammessages_auth.steamclient.proto

protoc emits flat, non-package-relative imports between the generated files
(``import steammessages_base_pb2``, not ``from . import ...``), so ``pb2/``
has to sit on ``sys.path`` for them to resolve each other. This module does
that once and re-exports only the message classes the client actually uses.
"""

import os
import sys

_PB2_DIR = os.path.join(os.path.dirname(__file__), "pb2")
if _PB2_DIR not in sys.path:
    sys.path.insert(0, _PB2_DIR)

from steammessages_auth.steamclient_pb2 import (  # noqa: E402
    CAuthentication_AccessToken_GenerateForApp_Request,
    CAuthentication_AccessToken_GenerateForApp_Response,
)
from steammessages_base_pb2 import CMsgMulti, CMsgProtoBufHeader  # noqa: E402
from steammessages_clientserver_login_pb2 import (  # noqa: E402
    CMsgClientLogOff,
    CMsgClientLogon,
    CMsgClientLogonResponse,
)

__all__ = [
    "CAuthentication_AccessToken_GenerateForApp_Request",
    "CAuthentication_AccessToken_GenerateForApp_Response",
    "CMsgClientLogOff",
    "CMsgClientLogon",
    "CMsgClientLogonResponse",
    "CMsgMulti",
    "CMsgProtoBufHeader",
]
