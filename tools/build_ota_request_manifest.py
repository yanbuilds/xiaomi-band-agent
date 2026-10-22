#!/usr/bin/env python3
"""Create a reviewable PrepareOta request manifest for an n67cn image.

The JSON is intentionally not a BLE/protobuf packet.  It is the exact set of
values a Gadgetbridge/AstroBox sender should log and pass into its protobuf
request before the mass-data transfer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def manifest(path: Path) -> dict:
    data = path.read_bytes()
    if data[:4] != b"`ZZ~":
        raise ValueError("not an n67cn outer Vela image")
    outer_version = data[4:12].split(b"\0", 1)[0].decode("ascii", "replace")
    mode = int.from_bytes(data[0x48:0x4C], "little")
    payload_offset = int.from_bytes(data[0x54:0x58], "little")
    return {
        "path": str(path),
        "outer_version": outer_version,
        "mode": mode,
        "image_length": len(data),
        "image_md5": hashlib.md5(data).hexdigest(),
        "image_sha256": hashlib.sha256(data).hexdigest(),
        "outer_payload_offset": payload_offset,
        "prepare_ota": {
            "enabled": True,
            "type": "ALL",
            "version": outer_version if mode == 0 else "3.1.190",
            "md5_hex": hashlib.md5(data).hexdigest(),
            "change_log": "Band Agent resource experiment; offline validation passed",
        },
        "warning": "Manifest values do not bypass device signature verification.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    result = manifest(args.image)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
