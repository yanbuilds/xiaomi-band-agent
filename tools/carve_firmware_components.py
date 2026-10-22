#!/usr/bin/env python3
"""Carve valid ZIP members embedded in a Xiaomi Vela firmware image.

The public firmware archive is a concatenation of vendor ZIP blocks.  A
normal ``zipfile.ZipFile`` call is misleading here because it searches for the
last EOCD in the whole 50 MB file.  This tool walks local headers, validates
the deflate stream and CRC, and writes the selected members to disk.
"""

from __future__ import annotations

import argparse
import binascii
import json
import struct
import zlib
from pathlib import Path

LOCAL = struct.Struct("<IHHHHHIIIHH")


def carve(data: bytes):
    pos = 0
    while True:
        pos = data.find(b"PK\x03\x04", pos)
        if pos < 0:
            return
        try:
            (sig, version, flags, method, _tm, _dt, crc, csize, usize,
             name_len, extra_len) = LOCAL.unpack_from(data, pos)
        except struct.error:
            return
        name_start = pos + LOCAL.size
        name_end = name_start + name_len
        payload_start = name_end + extra_len
        payload_end = payload_start + csize
        name_bytes = data[name_start:name_end]
        # False PK signatures are common in ARM code.  Require a normal ZIP
        # version, deflate/store method, printable short name and bounds.
        try:
            name = name_bytes.decode("utf-8")
        except UnicodeDecodeError:
            name = ""
        valid = (
            version in (10, 20, 45)
            and flags & 0x01 == 0  # not encrypted
            and method in (0, 8)
            and 0 < name_len < 256
            and all(32 <= x < 127 for x in name_bytes)
            and payload_end <= len(data)
            and csize < 200_000_000
            and usize < 400_000_000
        )
        if valid:
            compressed = data[payload_start:payload_end]
            try:
                decoded = (compressed if method == 0 else
                           zlib.decompress(compressed, -zlib.MAX_WBITS))
                valid = len(decoded) == usize and (binascii.crc32(decoded) & 0xffffffff) == crc
            except zlib.error:
                valid = False
        if valid:
            yield {
                "offset": pos,
                "name": name,
                "compressed_size": csize,
                "size": usize,
                "crc32": f"{crc:08x}",
                "data": decoded,
            }
        pos += 4


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("firmware", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--name", action="append", help="only extract this member name")
    args = ap.parse_args()
    data = args.firmware.read_bytes()
    args.output.mkdir(parents=True, exist_ok=True)
    manifest = []
    counters: dict[str, int] = {}
    for item in carve(data):
        if args.name and item["name"] not in args.name:
            continue
        n = counters.get(item["name"], 0)
        counters[item["name"]] = n + 1
        safe = item["name"].replace("/", "_")
        suffix = "" if n == 0 else f".{n:03d}"
        out = args.output / f"{safe}{suffix}"
        out.write_bytes(item.pop("data"))
        item["path"] = str(out)
        manifest.append(item)
    (args.output / "manifest.json").write_text(
        json.dumps({"firmware": str(args.firmware), "members": manifest}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"firmware": str(args.firmware), "count": len(manifest),
                      "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
