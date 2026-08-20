"""Steam CM channel crypto: RSA session-key handshake + AES-256-CBC with an
HMAC-derived IV for the encrypted channel afterwards.

Uses the ``cryptography`` package. The Public-universe RSA key below is the
well-known constant baked into every Steam client.
"""

import hashlib
import hmac
import os
from base64 import b64decode

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicKey
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

# Steam "Public" universe RSA public key, used to encrypt the CM channel session key.
_UNIVERSE_PUBLIC_KEY_DER = b64decode(
    b"MIGdMA0GCSqGSIb3DQEBAQUAA4GLADCBhwKBgQDf7BrWLBBmLBc1OhSwfFkRf53T"
    b"2Ct64+AVzRkeRuh7h3SiGEYxqQMUeYKO6UWiSRKpI2hzic9pobFhRr3Bvr/WARvY"
    b"gdTckPv+T1JzZsuVcNfFjrocejN1oWI0Rrtgt4Bo+hOneoo3S57G9F1fOpn5nsQ6"
    b"6WOiu4gZKODnFMBCiQIBEQ=="
)

_BLOCK_SIZE = 16


def _load_universe_public_key() -> RSAPublicKey:
    key = serialization.load_der_public_key(_UNIVERSE_PUBLIC_KEY_DER)
    assert isinstance(key, RSAPublicKey)
    return key


UNIVERSE_PUBLIC_KEY: RSAPublicKey = _load_universe_public_key()


def generate_session_key(hmac_secret: bytes = b"") -> tuple[bytes, bytes]:
    """Generate a random 32-byte session key and its RSA-OAEP(SHA1) encryption.

    :param hmac_secret: appended to the plaintext before encrypting - the CM
        handshake challenge bytes go here; empty for the WebAPI session key use.
    :return: ``(session_key, encrypted_session_key)``
    """
    session_key = os.urandom(32)
    encrypted_session_key = UNIVERSE_PUBLIC_KEY.encrypt(
        session_key + hmac_secret,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA1()),  # noqa: S303, S304
            algorithm=hashes.SHA1(),  # noqa: S303, S304
            label=None,
        ),
    )
    return session_key, encrypted_session_key


def _pad(data: bytes) -> bytes:
    padder = sym_padding.PKCS7(_BLOCK_SIZE * 8).padder()
    return padder.update(data) + padder.finalize()


def _unpad(data: bytes) -> bytes:
    unpadder = sym_padding.PKCS7(_BLOCK_SIZE * 8).unpadder()
    return unpadder.update(data) + unpadder.finalize()


def _aes_ecb_encrypt(data: bytes, key: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB())  # noqa: S305
    encryptor = cipher.encryptor()
    return encryptor.update(data) + encryptor.finalize()


def _aes_ecb_decrypt(data: bytes, key: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.ECB())  # noqa: S305
    decryptor = cipher.decryptor()
    return decryptor.update(data) + decryptor.finalize()


def _aes_cbc_encrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    return encryptor.update(_pad(data)) + encryptor.finalize()


def _aes_cbc_decrypt(data: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    return _unpad(decryptor.update(data) + decryptor.finalize())


def symmetric_encrypt(message: bytes, key: bytes) -> bytes:
    """AES-256-CBC with a random IV (no HMAC). ``encrypted_iv + ciphertext``."""
    iv = os.urandom(_BLOCK_SIZE)
    return _aes_ecb_encrypt(iv, key) + _aes_cbc_encrypt(message, key, iv)


def symmetric_decrypt(ciphertext: bytes, key: bytes) -> bytes:
    iv = _aes_ecb_decrypt(ciphertext[:_BLOCK_SIZE], key)
    return _aes_cbc_decrypt(ciphertext[_BLOCK_SIZE:], key, iv)


def _hmac_sha1(secret: bytes, data: bytes) -> bytes:
    return hmac.new(secret, data, hashlib.sha1).digest()  # noqa: S324


def symmetric_encrypt_hmac(message: bytes, key: bytes, hmac_secret: bytes) -> bytes:
    """AES-256-CBC with an HMAC-SHA1-derived IV, used for the CM channel once
    ``channel_hmac`` is set. ``encrypted_iv + ciphertext``.
    """
    prefix = os.urandom(3)
    digest = _hmac_sha1(hmac_secret, prefix + message)
    iv = digest[:13] + prefix
    return _aes_ecb_encrypt(iv, key) + _aes_cbc_encrypt(message, key, iv)


def symmetric_decrypt_hmac(ciphertext: bytes, key: bytes, hmac_secret: bytes) -> bytes:
    """:raises ValueError: the embedded HMAC doesn't match (tampered/wrong key)."""
    iv = _aes_ecb_decrypt(ciphertext[:_BLOCK_SIZE], key)
    message = _aes_cbc_decrypt(ciphertext[_BLOCK_SIZE:], key, iv)

    digest = _hmac_sha1(hmac_secret, iv[-3:] + message)
    if digest[:13] != iv[:13]:
        raise ValueError("HMAC mismatch while decrypting CM message")

    return message
