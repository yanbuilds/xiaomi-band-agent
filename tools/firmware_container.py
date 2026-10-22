#!/usr/bin/env python3
"""Inspect Xiaomi Vela containers without modifying them."""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def inspect_container(path: Path) -> dict:
    data = path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        members = []
        for item in archive.infolist():
            members.append({
                "name": item.filename,
                "header_offset": item.header_offset,
                "compressed_size": item.compress_size,
                "size": item.file_size,
                "crc32": f"{item.CRC:08x}",
            })
        resource_start = min(
            (item.header_offset for item in archive.infolist()), default=len(data)
        )
    payload = data[:resource_start]
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "payload_size_before_zip": resource_start,
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "members": members,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--extract-payload", type=Path)
    args = parser.parse_args()
    report = inspect_container(args.firmware)
    if args.extract_payload:
        data = args.firmware.read_bytes()[: report["payload_size_before_zip"]]
        args.extract_payload.write_bytes(data)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
