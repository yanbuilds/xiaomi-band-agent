#!/usr/bin/env python3
"""Redacted, standalone helpers for Xiaomi Wear V2 authentication.

The routine mirrors the public Mi Fitness 3.59.1 implementation found in
WearAuthV2: HKDF-SHA256("miwear-auth", phone_random || device_random),
HMAC-SHA256 signatures, and AES-CCM for the encrypted device-info protobuf.

This module never logs or prints key material. It only provides byte-level
helpers for a caller that already has an authorized device secret.
"""

from __future__ import annotations

import hmac
import hashlib
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESCCM


def _hkdf_sha256(ikm: bytes, salt: bytes, info: bytes, length: int = 64) -> bytes:
    """HKDF-Extract + Expand, matching the app's sid/HmacSHA256 helper."""
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    out = bytearray()
    previous = b""
    counter = 1
    while len(out) < length:
        previous = hmac.new(prk, previous + info + bytes([counter]), hashlib.sha256).digest()
        out.extend(previous)
        counter += 1
    return bytes(out[:length])


def derive_material(secret_key: bytes, phone_random: bytes, device_random: bytes) -> "AuthMaterial":
    if len(secret_key) != 16 or len(phone_random) != 16 or len(device_random) != 16:
        raise ValueError("secret and both random values must be 16 bytes")
    material = _hkdf_sha256(secret_key, phone_random + device_random, b"miwear-auth")
    return AuthMaterial(
        device_key=material[0:16],
        app_key=material[16:32],
        device_iv=material[32:36],
        app_iv=material[36:40],
    )


@dataclass(frozen=True)
class AuthMaterial:
    device_key: bytes
    app_key: bytes
    device_iv: bytes
    app_iv: bytes

    def device_signature(self, phone_random: bytes, device_random: bytes, device_name: str = "") -> bytes:
        message = device_random + phone_random + device_name.encode()
        return hmac.new(self.device_key, message, hashlib.sha256).digest()

    def app_signature(self, phone_random: bytes, device_random: bytes) -> bytes:
        return hmac.new(self.app_key, phone_random + device_random, hashlib.sha256).digest()

    def encrypt_device_info(self, protobuf: bytes) -> bytes:
        # The app uses a 12-byte nonce: app IV || uint32_le(0) || uint32_le(0).
        nonce = self.app_iv + b"\x00" * 8
        return AESCCM(self.app_key, tag_length=4).encrypt(nonce, protobuf, None)


def verify_device_signature(material: AuthMaterial, phone_random: bytes,
                            device_random: bytes, signature: bytes,
                            device_name: str = "") -> bool:
    expected = material.device_signature(phone_random, device_random, device_name)
    return hmac.compare_digest(expected, signature)

