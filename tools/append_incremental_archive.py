#!/usr/bin/env python3
"""Append one resource archive to an official n67cn mode-2 package.

This keeps every official archive byte-for-byte identical and only adds a
four-byte separator plus one resource ZIP.  The result is useful when a host
client applies a minimum firmware-size check to incremental packages.
"""

from __future__ import annotations

import argparse
import io
import struct
import zipfile
from pathlib import Path


PAYLOAD_OFFSET = 0x8C9A4
DECLARED_BIAS = 0x108
TRAILER_SIZE = 268


def slice_archive(image: bytes, start: int) -> bytes:
    eocd = image.find(b"PK\x05\x06", start)
    if eocd < 0:
        raise ValueError("archive EOCD not found")
    comment_len = struct.unpack_from("<H", image, eocd + 20)[0]
    return image[start:eocd + 22 + comment_len]


def build(base: Path, source_full: Path, source_start: int, output: Path,
          preserve_trailer: bool = False) -> dict:
    data = bytearray(base.read_bytes())
    if len(data) < PAYLOAD_OFFSET or data[0x48] != 2:
        raise ValueError("base is not an n67cn incremental package")
    trailer = b""
    if preserve_trailer:
        eocd = data.rfind(b"PK\x05\x06")
        if eocd < 0 or eocd + 22 > len(data):
            raise ValueError("base final EOCD not found")
        comment_len = struct.unpack_from("<H", data, eocd + 20)[0]
        archive_end = eocd + 22 + comment_len
        if len(data) - archive_end != TRAILER_SIZE:
            raise ValueError("base does not have a 268-byte n67cn trailer")
        trailer = bytes(data[archive_end:])
        del data[archive_end:]
    extra = slice_archive(source_full.read_bytes(), source_start)
    data.extend(b"\x00\x00\x00\x00")
    data.extend(extra)
    if trailer:
        # The first trailer word mirrors the CRC of the final ZIP member.
        # Keep the vendor metadata and RSA signature untouched; the latter
        # is expected to fail after a custom modification.
        with zipfile.ZipFile(io.BytesIO(extra)) as package:
            if not package.infolist():
                raise ValueError("appended archive has no members")
            struct.pack_into("<I", trailer := bytearray(trailer), 0,
                             package.infolist()[-1].CRC)
        data.extend(trailer)
    declared = len(data) - PAYLOAD_OFFSET - DECLARED_BIAS
    struct.pack_into("<I", data, 0x58, declared)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return {"base": str(base), "source": str(source_full),
            "output": str(output), "mode": data[0x48],
            "length": len(data), "appended_archive_size": len(extra),
            "declared_payload_size": declared,
            "preserved_trailer": bool(trailer)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path)
    ap.add_argument("source_full", type=Path)
    ap.add_argument("--source-start", type=lambda x: int(x, 0), required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--preserve-trailer", action="store_true",
                    help="retain the official 268-byte trailer shape (signature will be invalid after modification)")
    args = ap.parse_args()
    import json
    print(json.dumps(build(args.base, args.source_full, args.source_start,
                           args.output, args.preserve_trailer), indent=2))


if __name__ == "__main__":
    main()
