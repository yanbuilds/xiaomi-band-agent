#!/usr/bin/env python3
"""Build a size-preserving n67cn resource experiment.

The full image contains many independent ZIP archives concatenated after the
outer Vela header.  This tool patches one non-firmware member inside one
archive, keeps the raw-deflate length unchanged, updates both ZIP CRC fields,
and replaces exactly that archive in a copy of the image.  It is deliberately
not a signer or a flashing tool.
"""

from __future__ import annotations

import argparse
import io
import struct
import zlib
import zipfile
from pathlib import Path


def patch(image: Path, output: Path, archive_start: int, member: str | None,
          byte_offset: int | None = None) -> dict:
    original = image.read_bytes()
    if archive_start < 0 or archive_start >= len(original):
        raise ValueError("archive start is outside image")
    eocd = original.find(b"PK\x05\x06", archive_start)
    if eocd < 0:
        raise ValueError("archive has no EOCD")
    comment_len = struct.unpack_from("<H", original, eocd + 20)[0]
    archive_end = eocd + 22 + comment_len
    archive_bytes = original[archive_start:archive_end]
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
        items = archive.infolist()
        if not items:
            raise ValueError("archive is empty")
        info = next((x for x in items if x.filename == member), items[0]) if member else items[0]
        if info.filename.lower().endswith(".bin"):
            raise ValueError(f"refusing firmware binary entry: {info.filename}")
        decoded = archive.read(info)
        central = archive.start_dir
        local = info.header_offset
    if info.compress_type != zipfile.ZIP_DEFLATED:
        raise ValueError("only raw-deflate members are supported")
    local_name_len, local_extra_len = struct.unpack_from("<HH", archive_bytes, local + 26)
    comp_start = local + 30 + local_name_len + local_extra_len
    old_comp = archive_bytes[comp_start : comp_start + info.compress_size]

    offsets = [byte_offset] if byte_offset is not None else range(min(len(decoded), 4096))
    for index in offsets:
        if index < 0 or index >= len(decoded):
            raise ValueError("byte offset is outside member")
        candidate = bytearray(decoded)
        candidate[index] ^= 1
        for level in range(10):
            co = zlib.compressobj(level, zlib.DEFLATED, -15)
            compressed = co.compress(bytes(candidate)) + co.flush()
            if len(compressed) != len(old_comp):
                continue
            crc = zlib.crc32(candidate) & 0xFFFFFFFF
            rebuilt = bytearray(archive_bytes)
            rebuilt[comp_start : comp_start + len(compressed)] = compressed
            struct.pack_into("<I", rebuilt, local + 14, crc)
            struct.pack_into("<I", rebuilt, central + 16, crc)
            result = bytearray(original)
            result[archive_start:archive_end] = rebuilt
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(result)
            return {
                "archive_start": archive_start,
                "archive_end": archive_end,
                "archive_size": archive_end - archive_start,
                "member": info.filename,
                "member_offset": index,
                "compressed_size": len(compressed),
                "old_crc32": f"{info.CRC:08x}",
                "new_crc32": f"{crc:08x}",
                "output_size": len(result),
            }
    raise RuntimeError("no equal-size compressed variant found")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("output", type=Path)
    ap.add_argument("--archive-start", type=lambda x: int(x, 0), required=True)
    ap.add_argument("--member")
    ap.add_argument("--byte-offset", type=int,
                    help="exact uncompressed byte to flip; avoids a large search")
    args = ap.parse_args()
    print(patch(args.image, args.output, args.archive_start, args.member, args.byte_offset))


if __name__ == "__main__":
    main()
