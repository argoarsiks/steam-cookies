"""A minimal Steam CM (Connection Manager) client: enough to log on with a
desktop/mobile refresh token and call
``Authentication.GenerateAccessTokenForApp`` over the authenticated,
encrypted channel.

This is the CM-native alternative to the public, unauthenticated REST call in
``client.py`` - useful when that call gets rejected (``AccessDenied`` /
``InvalidPassword``) for a token that is otherwise valid.

No heartbeat loop, no reconnect logic, no persistent session: connect, secure
the channel, log on, make one RPC, log off.
"""

import gzip
import itertools
import secrets
import socket
import struct
import time
import zlib
from dataclasses import dataclass

from steam_cookies import crypto, framing, structs
from steam_cookies import emsg as emsg_mod
from steam_cookies.cm_server_list import fetch_cm_servers
from steam_cookies.connection import CMConnection
from steam_cookies.exceptions import (
    SteamConnectionError,
    SteamCookiesError,
    SteamLogonError,
    SteamProtocolError,
)
from steam_cookies.machine_id import build_machine_id
from steam_cookies.proto import (
    CAuthentication_AccessToken_GenerateForApp_Request,
    CAuthentication_AccessToken_GenerateForApp_Response,
    CMsgClientLogOff,
    CMsgClientLogon,
    CMsgClientLogonResponse,
    CMsgMulti,
    CMsgProtoBufHeader,
)
from steam_cookies.schemas import SteamWebCookies
from steam_cookies.token_claims import get_steamid_from_token

PROTOCOL_VERSION = 65581  # SteamKit2 MsgClientLogon.CurrentProtocol
CLIENT_PACKAGE_VERSION = 1771  # SteamKit2 SteamUser.LogOn
EOS_TYPE_WIN10 = 16
TARGET_JOB_GENERATE_ACCESS_TOKEN = "Authentication.GenerateAccessTokenForApp#1"

# Placeholder SteamID for the pre-logon header (universe Public, type
# Individual, instance Desktop, accountid=0). Identity for password/token
# logon comes entirely from the credentials in the message body, not the
# header - see SteamKit2's SteamUser.LogOn.
_EUNIVERSE_PUBLIC = 1
_EACCOUNT_TYPE_INDIVIDUAL = 1
_STEAMID_INSTANCE_DESKTOP = 1
_PLACEHOLDER_HEADER_STEAMID = (
    (_EUNIVERSE_PUBLIC << 56)
    | (_EACCOUNT_TYPE_INDIVIDUAL << 52)
    | (_STEAMID_INSTANCE_DESKTOP << 32)
)

_job_id_seq = itertools.count(1)


def _next_job_id() -> int:
    return (int(time.time() * 1000) << 20) | (next(_job_id_seq) & 0xFFFFF)


@dataclass
class _ParsedMessage:
    emsg: int
    header: CMsgProtoBufHeader
    body: bytes


class SteamCMClient:
    """Single-use CM session: connect -> secure channel -> log on -> RPC -> close.

    Mirrors :class:`~steam_cookies.client.SteamWebSessionClient`'s shape - construct
    it, use it as an async context manager, call :meth:`get_web_cookies` - except
    entering the context here does real work (fetch CM server candidates, connect,
    complete the channel-encryption handshake), since unlike an HTTP client there's
    nothing usable before that::

        async with SteamCMClient() as client:
            cookies = await client.get_web_cookies(refresh_token, account_name)

    The lower-level primitives (:meth:`connect_any`, :meth:`logon_with_refresh_token`,
    :meth:`generate_access_token`, :meth:`logoff`) stay available directly for callers
    that want more control, e.g. supplying their own CM server candidates.
    """

    def __init__(
        self,
        connect_timeout: float = 10.0,
        message_timeout: float = 15.0,
        max_server_attempts: int = 5,
    ) -> None:
        self._connect_timeout = connect_timeout
        self._message_timeout = message_timeout
        self._max_server_attempts = max_server_attempts
        self._conn = CMConnection()
        self._channel_key: bytes | None = None
        self._channel_hmac: bytes | None = None
        self._pending: list[_ParsedMessage] = []
        self._session_id: int | None = None

    async def __aenter__(self) -> "SteamCMClient":
        candidates = await fetch_cm_servers()
        await self.connect_any(candidates[: self._max_server_attempts])
        return self

    async def __aexit__(self, *_exc_info: object) -> None:
        await self.close()

    async def connect_any(self, candidates: list[tuple[str, int]]) -> tuple[str, int]:
        """Try each ``(host, port)`` candidate until one connects and completes
        the channel-encryption handshake.

        :raises SteamConnectionError: none of the candidates worked.
        """
        last_error: Exception | None = None

        for host, port in candidates:
            try:
                await self._conn.connect(host, port, timeout=self._connect_timeout)
                await self._secure_channel()
                return host, port
            except (OSError, SteamConnectionError, TimeoutError) as exc:
                last_error = exc
                await self._conn.close()

        detail = f"{type(last_error).__name__}: {last_error}" if last_error else "no candidates"
        raise SteamConnectionError(f"Could not connect to any CM server: {detail}")

    async def close(self) -> None:
        await self._conn.close()

    # -- channel encryption handshake -----------------------------------------

    async def _secure_channel(self) -> None:
        raw = await self._conn.recv(timeout=self._connect_timeout)
        header = structs.RawMsgHeader.load(raw)
        emsg = emsg_mod.clear_proto_bit(header.msg)

        if emsg != emsg_mod.EMSG_CHANNEL_ENCRYPT_REQUEST:
            raise SteamProtocolError(f"Expected ChannelEncryptRequest, got emsg={emsg}")

        req = structs.ChannelEncryptRequest.load(raw[structs.RawMsgHeader.SIZE :])

        key, encrypted_key = crypto.generate_session_key(req.challenge)
        crc = zlib.crc32(encrypted_key) & 0xFFFFFFFF

        resp = structs.ChannelEncryptResponse(key=encrypted_key, crc=crc)
        resp_header = structs.RawMsgHeader(msg=emsg_mod.EMSG_CHANNEL_ENCRYPT_RESPONSE)
        await self._conn.send(resp_header.serialize() + resp.serialize())

        raw_result = await self._conn.recv(timeout=self._connect_timeout)
        result_header = structs.RawMsgHeader.load(raw_result)
        result_emsg = emsg_mod.clear_proto_bit(result_header.msg)

        if result_emsg != emsg_mod.EMSG_CHANNEL_ENCRYPT_RESULT:
            raise SteamProtocolError(f"Expected ChannelEncryptResult, got emsg={result_emsg}")

        result = structs.ChannelEncryptResult.load(raw_result[structs.RawMsgHeader.SIZE :])
        if result.eresult != 1:
            raise SteamLogonError(result.eresult, "Channel encryption")

        self._channel_key = key
        self._channel_hmac = key[:16] if req.challenge else None

    # -- app-level (protobuf) messaging ---------------------------------------

    async def _send_proto(self, emsg: int, header: CMsgProtoBufHeader, body: bytes) -> None:
        if self._channel_key is None:
            raise SteamProtocolError("Cannot send before the channel is secured")

        if self._session_id is not None:
            header.client_sessionid = self._session_id

        payload = framing.serialize_proto_message(emsg, header, body)

        if self._channel_hmac:
            encrypted = crypto.symmetric_encrypt_hmac(
                payload, self._channel_key, self._channel_hmac
            )
        else:
            encrypted = crypto.symmetric_encrypt(payload, self._channel_key)

        await self._conn.send(encrypted)

    async def _recv_proto(self) -> _ParsedMessage:
        if self._pending:
            return self._pending.pop(0)

        if self._channel_key is None:
            raise SteamProtocolError("Cannot receive before the channel is secured")

        while True:
            raw = await self._conn.recv(timeout=self._message_timeout)

            try:
                if self._channel_hmac:
                    decrypted = crypto.symmetric_decrypt_hmac(
                        raw, self._channel_key, self._channel_hmac
                    )
                else:
                    decrypted = crypto.symmetric_decrypt(raw, self._channel_key)
            except ValueError as exc:
                raise SteamProtocolError(f"Failed to decrypt message: {exc}") from exc

            emsg, header, body = framing.parse_proto_message(decrypted)

            if emsg == emsg_mod.EMSG_MULTI:
                self._unpack_multi(body)
                if self._pending:
                    return self._pending.pop(0)
                continue

            return _ParsedMessage(emsg=emsg, header=header, body=body)

    def _unpack_multi(self, body: bytes) -> None:
        multi = CMsgMulti()
        multi.ParseFromString(body)

        data = multi.message_body
        if multi.size_unzipped:
            data = gzip.decompress(data)

        offset = 0
        while offset + 4 <= len(data):
            (size,) = struct.unpack_from("<I", data, offset)
            offset += 4

            if size < 0 or offset + size > len(data):
                break  # truncated/misaligned framing - can't trust the rest

            chunk = data[offset : offset + size]
            offset += size

            try:
                sub_emsg, sub_header, sub_body = framing.parse_proto_message(chunk)
            except SteamProtocolError:
                continue  # skip a sub-message we don't know how to parse

            self._pending.append(_ParsedMessage(emsg=sub_emsg, header=sub_header, body=sub_body))

    # -- logon ------------------------------------------------------------------

    async def logon_with_refresh_token(
        self, refresh_token: str, steamid: int, account_name: str
    ) -> None:
        """:raises SteamLogonError: Steam rejected the logon."""
        logon = CMsgClientLogon()
        logon.protocol_version = PROTOCOL_VERSION
        logon.client_os_type = EOS_TYPE_WIN10
        logon.client_language = "english"
        logon.cell_id = 0
        logon.client_package_version = CLIENT_PACKAGE_VERSION
        logon.should_remember_password = True
        logon.supports_rate_limit_response = True
        logon.chat_mode = 2
        logon.obfuscated_private_ip.v4 = 0
        # CM requires account_name even for token-based logon - see SteamKit2's
        # Samples/002_WebCookie.
        logon.account_name = account_name
        logon.access_token = refresh_token
        logon.machine_name = socket.gethostname()
        # Deterministic per-account so repeat logons report the same device.
        seed = f"steam_cookies-{steamid}"
        logon.machine_id = build_machine_id(f"{seed}-bb3", f"{seed}-ff2", f"{seed}-3b3")

        header = CMsgProtoBufHeader()
        header.steamid = _PLACEHOLDER_HEADER_STEAMID

        await self._send_proto(emsg_mod.EMSG_CLIENT_LOGON, header, logon.SerializeToString())

        message = await self._wait_for(emsg_mod.EMSG_CLIENT_LOGON_RESPONSE)

        response = CMsgClientLogonResponse()
        response.ParseFromString(message.body)

        if response.eresult != 1:
            raise SteamLogonError(response.eresult, "Logon")

        self._session_id = message.header.client_sessionid

    async def _wait_for(self, wanted_emsg: int, max_messages: int = 20) -> _ParsedMessage:
        for _ in range(max_messages):
            message = await self._recv_proto()
            if message.emsg == wanted_emsg:
                return message
            # Anything else (out-of-order notifications etc.) is skipped - we
            # only care about a small, known set of replies in this one-shot flow.
        raise SteamProtocolError(f"Timed out waiting for emsg={wanted_emsg}")

    async def generate_access_token(self, refresh_token: str, steamid: int) -> str:
        """Call ``Authentication.GenerateAccessTokenForApp`` over the CM channel.

        :raises SteamLogonError: Steam rejected the call.
        """
        request = CAuthentication_AccessToken_GenerateForApp_Request()
        request.refresh_token = refresh_token
        request.steamid = steamid

        header = CMsgProtoBufHeader()
        header.steamid = steamid
        header.target_job_name = TARGET_JOB_GENERATE_ACCESS_TOKEN
        job_id = _next_job_id()
        header.jobid_source = job_id

        await self._send_proto(
            emsg_mod.EMSG_SERVICE_METHOD_CALL_FROM_CLIENT, header, request.SerializeToString()
        )

        message = await self._wait_for_job(job_id)

        if message.header.eresult and message.header.eresult != 1:
            raise SteamLogonError(message.header.eresult, "GenerateAccessTokenForApp")

        response = CAuthentication_AccessToken_GenerateForApp_Response()
        response.ParseFromString(message.body)

        if not response.access_token:
            raise SteamProtocolError("GenerateAccessTokenForApp returned an empty response")

        return response.access_token

    async def _wait_for_job(self, job_id: int, max_messages: int = 20) -> _ParsedMessage:
        for _ in range(max_messages):
            message = await self._recv_proto()
            if (
                message.emsg == emsg_mod.EMSG_SERVICE_METHOD_RESPONSE
                and message.header.jobid_target == job_id
            ):
                return message
        raise SteamProtocolError("Timed out waiting for GenerateAccessTokenForApp response")

    async def logoff(self) -> None:
        try:
            header = CMsgProtoBufHeader()
            if self._session_id is not None:
                header.client_sessionid = self._session_id
            await self._send_proto(
                emsg_mod.EMSG_CLIENT_LOG_OFF, header, CMsgClientLogOff().SerializeToString()
            )
        except SteamCookiesError:
            pass  # best-effort; we're closing the connection right after anyway

    # -- convenience -------------------------------------------------------

    async def get_web_cookies(self, refresh_token: str, account_name: str) -> SteamWebCookies:
        """Log on with ``refresh_token`` and exchange it for web session cookies,
        over a channel this client has already connected and secured (see
        :meth:`__aenter__`/:meth:`connect_any`).

        The CM-session counterpart to
        :meth:`~steam_cookies.client.SteamWebSessionClient.get_web_cookies` - the
        only reason it also needs ``account_name`` is that CM requires it for
        logon even with a token, whereas the REST path doesn't touch logon at all.

        :param account_name: the account's login name (not persona/display name -
            e.g. the ``AccountName`` field in Steam's own ``loginusers.vdf``).
        :raises SteamLogonError: Steam rejected the logon or the RPC call.
        :raises SteamProtocolError: an unexpected/malformed response was received.
        """
        steamid = get_steamid_from_token(refresh_token)
        await self.logon_with_refresh_token(refresh_token, steamid, account_name)
        access_token = await self.generate_access_token(refresh_token, steamid)
        await self.logoff()

        return SteamWebCookies(
            steamid=steamid,
            steam_login_secure=f"{steamid}||{access_token}",
            session_id=secrets.token_hex(12),
        )


async def get_web_cookies_via_cm(
    refresh_token: str,
    account_name: str,
    connect_timeout: float = 10.0,
    message_timeout: float = 15.0,
    max_server_attempts: int = 5,
) -> SteamWebCookies:
    """Full CM-native flow: connect to a CM server, log on with the refresh
    token, call ``Authentication.GenerateAccessTokenForApp`` over the
    authenticated channel, and build the web session cookies from the result.

    Convenience one-shot wrapper, equivalent to::

        async with SteamCMClient(connect_timeout=..., message_timeout=..., ...) as client:
            return await client.get_web_cookies(refresh_token, account_name)

    :param account_name: the account's login name (not persona/display name -
        e.g. the ``AccountName`` field in Steam's own ``loginusers.vdf``).
        Required by CM even for token-based logon.
    :raises SteamConnectionError: no CM server could be reached.
    :raises SteamLogonError: Steam rejected the logon or the RPC call.
    :raises SteamProtocolError: an unexpected/malformed response was received.
    """
    async with SteamCMClient(
        connect_timeout=connect_timeout,
        message_timeout=message_timeout,
        max_server_attempts=max_server_attempts,
    ) as client:
        return await client.get_web_cookies(refresh_token, account_name)
