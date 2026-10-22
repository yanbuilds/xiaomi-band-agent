#!/usr/bin/env python3
"""List embedded ZIP members in a Xiaomi Vela firmware container.

The .bin files are not flat MCU images: they contain a vendor header followed
by repeated ZIP-like resource blocks. This command only reads metadata.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=Path)
    args = parser.parse_args()
    data = args.firmware.read_bytes()
    seen = set()
    blocks = []
    cursor = 0
    while True:
        offset = data.find(b"PK\x03\x04", cursor)
        if offset < 0:
            break
        cursor = offset + 1
        if offset in seen:
            continue
        seen.add(offset)
        try:
            archive = zipfile.ZipFile(io.BytesIO(data[offset:]))
            members = [
                {
                    "name": item.filename,
                    "compressed_size": item.compress_size,
                    "size": item.file_size,
                    "crc32": f"{item.CRC:08x}",
                }
                for item in archive.infolist()
            ]
        except zipfile.BadZipFile:
            continue
        blocks.append({"offset": offset, "members": members})
    print(json.dumps({"path": str(args.firmware), "blocks": blocks}, indent=2))


if __name__ == "__main__":
    main()
