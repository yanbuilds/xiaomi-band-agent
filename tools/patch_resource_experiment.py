#!/usr/bin/env python3
"""Create a size-preserving resource-only experiment (never a flash command).

The output is useful for testing container/CRC handling. It intentionally does
not attempt to update firmware signatures or provide a device flashing path.
"""

from __future__ import annotations

import argparse
import struct
import zlib
import zipfile
from pathlib import Path


def patch_font(src: Path, dst: Path) -> dict:
    data = bytearray(src.read_bytes())
    with zipfile.ZipFile(src) as archive:
        info = archive.infolist()[0]
        if info.filename.lower().endswith(".bin"):
            raise ValueError("refusing to modify a firmware binary entry")
        original = archive.read(info)
        local = info.header_offset
        name_len, extra_len = struct.unpack_from("<HH", data, local + 26)
        comp_start = local + 30 + name_len + extra_len
        old_comp = bytes(data[comp_start : comp_start + info.compress_size])
        central = archive.start_dir

    for index in range(min(len(original), 4096)):
        candidate = bytearray(original)
        candidate[index] ^= 1
        for level in range(10):
            co = zlib.compressobj(level, zlib.DEFLATED, -15)
            compressed = co.compress(bytes(candidate)) + co.flush()
            if len(compressed) == len(old_comp):
                crc = zlib.crc32(candidate) & 0xFFFFFFFF
                data[comp_start : comp_start + len(compressed)] = compressed
                struct.pack_into("<I", data, local + 14, crc)
                struct.pack_into("<I", data, central + 16, crc)
                dst.write_bytes(data)
                return {"entry": info.filename, "byte_offset": index, "compression_level": level,
                        "old_crc32": f"{info.CRC:08x}", "new_crc32": f"{crc:08x}",
                        "compressed_size": len(compressed)}
    raise RuntimeError("no equal-size deflate variant found in first 4096 bytes")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(patch_font(args.source, args.output))


if __name__ == "__main__":
    main()
