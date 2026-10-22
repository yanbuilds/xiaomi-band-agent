#!/usr/bin/env python3
"""Append one resource archive to an official n67cn mode-2 package.

This keeps every official archive byte-for-byte identical and only adds a
four-byte separator plus one resource ZIP.  The result is useful when a host
client applies a minimum firmware-size check to incremental packages.
"""

from __future__ import annotations

import argparse
import struct
from pathlib import Path


PAYLOAD_OFFSET = 0x8C9A4
DECLARED_BIAS = 0x108


def slice_archive(image: bytes, start: int) -> bytes:
    eocd = image.find(b"PK\x05\x06", start)
    if eocd < 0:
        raise ValueError("archive EOCD not found")
    comment_len = struct.unpack_from("<H", image, eocd + 20)[0]
    return image[start:eocd + 22 + comment_len]


def build(base: Path, source_full: Path, source_start: int, output: Path) -> dict:
    data = bytearray(base.read_bytes())
    if len(data) < PAYLOAD_OFFSET or data[0x48] != 2:
        raise ValueError("base is not an n67cn incremental package")
    extra = slice_archive(source_full.read_bytes(), source_start)
    data.extend(b"\x00\x00\x00\x00")
    data.extend(extra)
    declared = len(data) - PAYLOAD_OFFSET - DECLARED_BIAS
    struct.pack_into("<I", data, 0x58, declared)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)
    return {"base": str(base), "source": str(source_full),
            "output": str(output), "mode": data[0x48],
            "length": len(data), "appended_archive_size": len(extra),
            "declared_payload_size": declared}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", type=Path)
    ap.add_argument("source_full", type=Path)
    ap.add_argument("--source-start", type=lambda x: int(x, 0), required=True)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    import json
    print(json.dumps(build(args.base, args.source_full, args.source_start,
                           args.output), indent=2))


if __name__ == "__main__":
    main()
