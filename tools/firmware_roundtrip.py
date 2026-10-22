#!/usr/bin/env python3
"""Verify a Xiaomi firmware container without changing its bytes.

This is deliberately a no-op baseline. A future resource patcher must first
match the original payload and ZIP metadata; otherwise the result is rejected
before it can be considered for any device-side testing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--copy", type=Path, required=True)
    args = parser.parse_args()

    with zipfile.ZipFile(args.firmware) as archive:
        entries = [
            {
                "name": item.filename,
                "crc32": f"{item.CRC:08x}",
                "size": item.file_size,
                "compressed_size": item.compress_size,
                "header_offset": item.header_offset,
            }
            for item in archive.infolist()
        ]

    args.copy.write_bytes(args.firmware.read_bytes())
    before, after = digest(args.firmware), digest(args.copy)
    result = {
        "source": str(args.firmware),
        "copy": str(args.copy),
        "source_sha256": before,
        "copy_sha256": after,
        "byte_identical": before == after,
        "zip_entries": entries,
    }
    print(json.dumps(result, indent=2))
    if before != after:
        raise SystemExit("round-trip copy changed bytes")


if __name__ == "__main__":
    main()
