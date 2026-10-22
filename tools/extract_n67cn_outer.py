#!/usr/bin/env python3
"""Extract the outer Vela OTA component from an n67cn full image.

The n67cn file begins with a 92-byte container header.  The header's payload
offset points to the end of the first component (normally ``vela_ota.bin``),
so this tool does not guess from ZIP signatures or copy a truncated range.
It only reads the image and writes an exact component plus a JSON manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MAGIC = b"`ZZ~"
HEADER_SIZE = 0x5C


def parse(path: Path) -> tuple[bytes, dict]:
    data = path.read_bytes()
    if len(data) < HEADER_SIZE or data[:4] != MAGIC:
        raise ValueError(f"{path}: not an n67cn outer Vela image")
    version = data[4:12].split(b"\0", 1)[0].decode("ascii", "replace")
    table_offset = int.from_bytes(data[0x50:0x54], "little")
    payload_offset = int.from_bytes(data[0x54:0x58], "little")
    declared_size = int.from_bytes(data[0x58:0x5C], "little")
    if table_offset < HEADER_SIZE or payload_offset < table_offset:
        raise ValueError("invalid outer offsets")
    if payload_offset > len(data):
        raise ValueError("payload offset exceeds image length")
    component = data[HEADER_SIZE:payload_offset]
    report = {
        "source": str(path),
        "source_size": len(data),
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "version": version,
        "format_word": data[0x44:0x48].hex(),
        "mode": int.from_bytes(data[0x48:0x4C], "little"),
        "header_size": HEADER_SIZE,
        "table_offset": table_offset,
        "component_start": HEADER_SIZE,
        "component_end": payload_offset,
        "component_size": len(component),
        "declared_payload_size": declared_size,
        "component_sha256": hashlib.sha256(component).hexdigest(),
        "component_prefix": component[:16].hex(),
        "component_suffix": component[-16:].hex(),
    }
    return component, report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--component", type=Path, required=True)
    ap.add_argument("--manifest", type=Path, required=True)
    args = ap.parse_args()
    component, report = parse(args.image)
    args.component.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.component.write_bytes(component)
    args.manifest.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
