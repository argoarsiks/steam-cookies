import os

import pytest

from steam_cookies import crypto


def test_generate_session_key_returns_a_32_byte_key() -> None:
    key, encrypted_key = crypto.generate_session_key()

    assert len(key) == 32
    assert isinstance(encrypted_key, bytes)
    assert len(encrypted_key) > 0


def test_generate_session_key_is_random_each_call() -> None:
    key_a, _ = crypto.generate_session_key()
    key_b, _ = crypto.generate_session_key()

    assert key_a != key_b


def test_symmetric_encrypt_decrypt_round_trip() -> None:
    key = os.urandom(32)
    message = b"the quick brown fox jumps over the lazy dog"

    ciphertext = crypto.symmetric_encrypt(message, key)

    assert crypto.symmetric_decrypt(ciphertext, key) == message


def test_symmetric_encrypt_uses_a_random_iv() -> None:
    key = os.urandom(32)
    message = b"same message, different ciphertext"

    assert crypto.symmetric_encrypt(message, key) != crypto.symmetric_encrypt(message, key)


def test_symmetric_encrypt_hmac_decrypt_hmac_round_trip() -> None:
    key = os.urandom(32)
    hmac_secret = os.urandom(16)
    message = b"channel-secured payload"

    ciphertext = crypto.symmetric_encrypt_hmac(message, key, hmac_secret)

    assert crypto.symmetric_decrypt_hmac(ciphertext, key, hmac_secret) == message


def test_symmetric_decrypt_hmac_rejects_wrong_hmac_secret() -> None:
    key = os.urandom(32)
    message = b"channel-secured payload"
    ciphertext = crypto.symmetric_encrypt_hmac(message, key, os.urandom(16))

    with pytest.raises(ValueError, match="HMAC mismatch"):
        crypto.symmetric_decrypt_hmac(ciphertext, key, os.urandom(16))


def test_symmetric_decrypt_hmac_rejects_tampered_ciphertext() -> None:
    key = os.urandom(32)
    hmac_secret = os.urandom(16)
    ciphertext = bytearray(crypto.symmetric_encrypt_hmac(b"original message", key, hmac_secret))
    ciphertext[-1] ^= 0xFF  # flip a bit in the last ciphertext block

    # Depending on which byte got flipped this surfaces either as a padding
    # error (from the CBC/PKCS7 unpad) or as our own HMAC-mismatch check -
    # either way it must not silently return tampered plaintext.
    with pytest.raises(ValueError):
        crypto.symmetric_decrypt_hmac(bytes(ciphertext), key, hmac_secret)
