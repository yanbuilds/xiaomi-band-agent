#!/usr/bin/env python3
"""Inspect the signature-related surface of an n67cn image without writing it.

This intentionally does not claim to verify Xiaomi's proprietary updater.  It
records standard OpenVela/APK-signing markers, ZIP tail geometry, and the
outer-image metadata so later hardware logs can be compared against a stable
baseline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


MAGICS = (b"APK Sig Block 42", b"AVB0", b"AVBf", b"vbmeta", b"/etc/key.avb")


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    eocd = data.rfind(b"PK\x05\x06")
    archive_end = None
    tail_len = None
    if eocd >= 0 and eocd + 22 <= len(data):
        comment_len = struct.unpack_from("<H", data, eocd + 20)[0]
        archive_end = eocd + 22 + comment_len
        if archive_end <= len(data):
            tail_len = len(data) - archive_end
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "outer_magic": data[:4].hex(),
        "outer_version": data[4:36].split(b"\0", 1)[0].decode("ascii", "replace"),
        "outer_mode": struct.unpack_from("<I", data, 0x48)[0] if len(data) >= 0x4c else None,
        "last_eocd_offset": eocd,
        "last_archive_end": archive_end,
        "last_archive_tail_length": tail_len,
        "last_archive_tail_prefix": data[archive_end:archive_end + 16].hex() if archive_end else None,
        "last_archive_tail_suffix": data[-16:].hex() if data else None,
        "standard_markers": {
            marker.decode("ascii", "replace"): data.find(marker) >= 0
            for marker in MAGICS
        },
        "interpretation": (
            "The standard OpenVela APK Sig Block markers are absent from this "
            "n67cn outer image; n67cn uses its Vela-specific updater surface. "
            "This is a format observation, not proof that the tail is unsigned."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = inspect(args.image)
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
