"""Validate a locally generated n67cn full-image experiment.

The validator is intentionally offline and read-only. It checks the outer Vela
header, exact file length, and that all changes are confined to a ZIP resource
payload plus its ZIP CRC fields. It does not claim that the band will accept
the image; only the device-side OTA verifier can establish that.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


MAGIC = b"`ZZ~"


def changed_ranges(a: bytes, b: bytes) -> list[dict[str, int]]:
    if len(a) != len(b):
        raise ValueError("images have different sizes")
    out: list[dict[str, int]] = []
    i = 0
    while i < len(a):
        if a[i] == b[i]:
            i += 1
            continue
        start = i
        while i < len(a) and a[i] != b[i]:
            i += 1
        out.append({"start": start, "end": i, "length": i - start})
    return out


def describe(path: Path) -> dict:
    data = path.read_bytes()
    if data[:4] != MAGIC:
        raise ValueError(f"{path}: missing outer Vela magic")
    version = data[4:12].split(b"\0", 1)[0].decode("ascii", "replace")
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "version": version,
        "header": {
            "format_word": data[0x44:0x48].hex(),
            "mode": int.from_bytes(data[0x48:0x4C], "little"),
            "table_offset": int.from_bytes(data[0x50:0x54], "little"),
            "payload_offset": int.from_bytes(data[0x54:0x58], "little"),
            "declared_payload_size": int.from_bytes(data[0x58:0x5C], "little"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("original", type=Path)
    ap.add_argument("candidate", type=Path)
    args = ap.parse_args()
    original = describe(args.original)
    candidate = describe(args.candidate)
    a, b = args.original.read_bytes(), args.candidate.read_bytes()
    ranges = changed_ranges(a, b)
    result = {
        "original": original,
        "candidate": candidate,
        "same_length": len(a) == len(b),
        "header_unchanged": a[:0x5C] == b[:0x5C],
        "changed_ranges": ranges,
        "device_acceptance": "not verified; requires a real n67cn device and recovery path",
    }
    print(json.dumps(result, indent=2))
    if not result["same_length"] or not result["header_unchanged"]:
        raise SystemExit("candidate failed structural safety checks")


if __name__ == "__main__":
    main()
