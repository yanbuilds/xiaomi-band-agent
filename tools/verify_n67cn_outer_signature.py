#!/usr/bin/env python3
"""Verify the RSA signature appended to an official n67cn outer image.

The discovered n67cn trailer is:

    uint32 last-member-crc32
    uint32 signature-metadata
    uint8[256] RSA-2048 PKCS#1 v1.5 SHA-256 signature
    uint32 0x805a5a7e

The signed bytes are the complete ZIP stream through the final EOCD followed
by the first eight trailer bytes.  This verifier is read-only and deliberately
does not provide signing functionality.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding


TRAILER_SIZE = 268
TRAILER_MAGIC = 0x805A5A7E


def verify(image: Path, public_key: Path) -> dict:
    data = image.read_bytes()
    eocd = data.rfind(b"PK\x05\x06")
    if eocd < 0 or eocd + 22 > len(data):
        raise ValueError("final EOCD not found")
    comment_len = struct.unpack_from("<H", data, eocd + 20)[0]
    archive_end = eocd + 22 + comment_len
    trailer = data[archive_end:]
    if len(trailer) != TRAILER_SIZE:
        raise ValueError(f"expected {TRAILER_SIZE}-byte trailer, got {len(trailer)}")
    member_crc, metadata = struct.unpack_from("<II", trailer, 0)
    signature = trailer[8:264]
    magic = struct.unpack_from(">I", trailer, 264)[0]
    # The public key is encoded as a normal PEM SubjectPublicKeyInfo.
    key = serialization.load_pem_public_key(public_key.read_bytes())
    signed = data[:archive_end] + trailer[:8]
    digest = hashlib.sha256(signed).hexdigest()
    verified = True
    error = None
    try:
        key.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
    except Exception as exc:  # cryptography intentionally uses a generic error
        verified = False
        error = type(exc).__name__
    with zipfile.ZipFile(image) as _:
        pass
    return {
        "image": str(image),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "eocd_offset": eocd,
        "archive_end": archive_end,
        "trailer_size": len(trailer),
        "member_crc32": f"{member_crc:08x}",
        "signature_metadata": f"{metadata:08x}",
        "trailer_magic": f"{magic:08x}",
        "signed_sha256": digest,
        "signature_verified": verified,
        "error": error,
        "warning": "Verification proves the supplied public key matches this image; it does not recover a private signing key.",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--public-key", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.image, args.public_key)
    print(json.dumps(result, indent=2))
    if not result["signature_verified"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
