#!/usr/bin/env python3
"""Index concatenated ZIP archives embedded in an n67cn full image.

Xiaomi's full image is a Vela container followed by independent ZIP packages
(AP, boot, factory and resource payloads).  This tool finds only structurally
valid EOCD records, reconstructs each archive boundary from the central
directory fields, and emits offsets/member metadata.  It never extracts or
modifies firmware bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import zipfile
from pathlib import Path


EOCD = b"PK\x05\x06"
EOCD_SIZE = 22


def index(path: Path) -> list[dict]:
    data = path.read_bytes()
    found: dict[int, dict] = {}
    pos = 0
    while True:
        pos = data.find(EOCD, pos)
        if pos < 0:
            break
        if pos + EOCD_SIZE > len(data):
            break
        disk, cd_disk, disk_entries, entries, cd_size, cd_offset, comment_len = struct.unpack_from(
            "<HHHHIIH", data, pos + 4
        )
        end = pos + EOCD_SIZE + comment_len
        start = pos - cd_size - cd_offset
        pos += 1
        if disk or cd_disk or disk_entries != entries or end > len(data) or start < 0:
            continue
        if not data[start : start + 4] == b"PK\x03\x04":
            continue
        blob = data[start:end]
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                members = [
                    {
                        "name": item.filename,
                        "compressed_size": item.compress_size,
                        "size": item.file_size,
                        "crc32": f"{item.CRC:08x}",
                        "header_offset": item.header_offset,
                    }
                    for item in archive.infolist()
                ]
        except (OSError, ValueError, zipfile.BadZipFile):
            continue
        found[start] = {
            "start": start,
            "end": end,
            "size": end - start,
            "sha256": hashlib.sha256(blob).hexdigest(),
            "members": members,
        }
    return [found[key] for key in sorted(found)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--json", type=Path, required=True)
    args = ap.parse_args()
    archives = index(args.image)
    result = {
        "image": str(args.image),
        "image_size": args.image.stat().st_size,
        "archives": archives,
    }
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"image": str(args.image), "archives": len(archives), "output": str(args.json)}, indent=2))


if __name__ == "__main__":
    main()
