#!/usr/bin/env python3
"""Build/verify the AstroBox MiWear firmware mass-data envelope.

This is only the phone-to-watch transport envelope.  It does not alter the
firmware image and does not bypass the watch's OTA signature checks.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path


FIRMWARE_TYPE = 0x20


def build(image: bytes) -> bytes:
    md5 = hashlib.md5(image).digest()
    body = bytes((0x00, FIRMWARE_TYPE)) + md5 + struct.pack("<I", len(image)) + image
    return body + struct.pack("<I", zlib.crc32(body) & 0xFFFFFFFF)


def verify(envelope: bytes) -> dict:
    if len(envelope) < 26:
        raise ValueError("mass envelope is too short")
    if envelope[0] != 0 or envelope[1] != FIRMWARE_TYPE:
        raise ValueError("unexpected compression or data type")
    declared_md5 = envelope[2:18]
    declared_length = struct.unpack_from("<I", envelope, 18)[0]
    end = 22 + declared_length
    if end + 4 != len(envelope):
        raise ValueError("declared image length does not match envelope")
    image = envelope[22:end]
    declared_crc = struct.unpack_from("<I", envelope, end)[0]
    actual_crc = zlib.crc32(envelope[:end]) & 0xFFFFFFFF
    actual_md5 = hashlib.md5(image).digest()
    if declared_md5 != actual_md5:
        raise ValueError("MD5 mismatch")
    if declared_crc != actual_crc:
        raise ValueError("CRC32 mismatch")
    return {
        "data_type": FIRMWARE_TYPE,
        "image_length": declared_length,
        "image_md5": actual_md5.hex(),
        "envelope_length": len(envelope),
        "crc32": f"{actual_crc:08x}",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    image = args.image.read_bytes()
    envelope = build(image)
    report = verify(envelope)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(envelope)
    print(json.dumps({"source": str(args.image), "output": str(args.output), **report}, indent=2))


if __name__ == "__main__":
    main()
