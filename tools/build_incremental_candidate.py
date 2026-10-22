#!/usr/bin/env python3
"""Build a minimal n67cn incremental OTA candidate.

The official 3.1.175 -> 3.1.190 package keeps the 0x5c-byte outer header and
the exact vela_ota component, then appends selected concatenated ZIP archives
with four-byte separators.  This tool emits that same shape with version.ini
and one resource archive copied from a full-image candidate.

It does not sign firmware or bypass the watch verifier.
"""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path


HEADER_SIZE = 0x5C
PAYLOAD_OFFSET = 0x8C9A4
DECLARED_BIAS = 0x108


def archive_slice(image: bytes, start: int) -> bytes:
    eocd = image.find(b"PK\x05\x06", start)
    if eocd < 0:
        raise ValueError(f"no EOCD after archive start 0x{start:x}")
    comment_len = struct.unpack_from("<H", image, eocd + 20)[0]
    end = eocd + 22 + comment_len
    return image[start:end]


def build(base_incremental: Path, candidate_full: Path, index_json: Path,
          output: Path, version_archive_start: int,
          changed_archive_start: int) -> dict:
    base = base_incremental.read_bytes()
    full = candidate_full.read_bytes()
    if len(base) < PAYLOAD_OFFSET:
        raise ValueError("base incremental image is too short")
    if base[0x48] != 2:
        raise ValueError("base image is not incremental mode 2")

    # Keep the vendor's exact header and vela_ota component.  The candidate
    # only changes the list of following archives.
    prefix = bytearray(base[:PAYLOAD_OFFSET])
    version = archive_slice(full, version_archive_start)
    changed = archive_slice(full, changed_archive_start)
    payload = version + b"\x00\x00\x00\x00" + changed
    result = prefix + payload

    declared = len(result) - PAYLOAD_OFFSET - DECLARED_BIAS
    struct.pack_into("<I", result, 0x58, declared)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(result)

    report = {
        "base": str(base_incremental),
        "candidate_full": str(candidate_full),
        "output": str(output),
        "mode": result[0x48],
        "version": result[:0x44].split(b"\0", 1)[0].decode("ascii", "replace"),
        "length": len(result),
        "payload_offset": PAYLOAD_OFFSET,
        "declared_payload_size": declared,
        "archive_count": 2,
        "archives": [
            {"name": "version.ini", "size": len(version)},
            {"name": "changed-resource", "size": len(changed)},
        ],
    }
    if index_json.exists():
        report["index"] = str(index_json)
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("base_incremental", type=Path)
    ap.add_argument("candidate_full", type=Path)
    ap.add_argument("--index", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--version-archive-start", type=lambda x: int(x, 0), required=True)
    ap.add_argument("--changed-archive-start", type=lambda x: int(x, 0), required=True)
    args = ap.parse_args()
    print(json.dumps(build(args.base_incremental, args.candidate_full,
                           args.index, args.output,
                           args.version_archive_start,
                           args.changed_archive_start), indent=2))


if __name__ == "__main__":
    main()
