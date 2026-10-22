#!/usr/bin/env python3
"""Extract an embedded big-endian rom1fs volume from a n67cn component."""

from __future__ import annotations

import argparse
import struct
from pathlib import Path

MAGIC = b"-rom1fs-"
ALIGN = 16


def align(value: int) -> int:
    return (value + ALIGN - 1) & ~(ALIGN - 1)


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from(">I", data, offset)[0]


def read_name(data: bytes, offset: int) -> tuple[str, int]:
    end = data.index(b"\0", offset)
    raw = data[offset:end]
    return raw.decode("utf-8", "replace"), align(end + 1)


def extract(image: Path, output: Path, offset: int | None = None) -> dict:
    data = image.read_bytes()
    start = data.find(MAGIC) if offset is None else offset
    if start < 0:
        raise ValueError("rom1fs magic not found")
    if start + 16 > len(data):
        raise ValueError("truncated rom1fs header")
    volume_size = u32(data, start + 8)
    end = start + volume_size
    if volume_size < 32 or end > len(data):
        raise ValueError(f"invalid rom1fs size 0x{volume_size:x}")
    output.mkdir(parents=True, exist_ok=True)
    visited: set[int] = set()
    files = 0

    def walk(node_rel: int, parent: Path) -> None:
        nonlocal files
        while node_rel:
            node_rel &= ~0xF
            if node_rel in visited:
                return
            visited.add(node_rel)
            node = start + node_rel
            if node + 16 > end:
                raise ValueError(f"node outside volume: 0x{node_rel:x}")
            next_word, spec, size, _checksum = struct.unpack_from(">IIII", data, node)
            name, payload = read_name(data, node + 16)
            kind = next_word & 0xF
            safe = name or "_"
            target = parent / safe
            if kind == 9:  # directory in NuttX rom1fs
                target.mkdir(parents=True, exist_ok=True)
                walk(spec, target)
            elif kind == 2:  # regular file
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data[payload : payload + size])
                files += 1
            else:
                # Keep unknown entries visible without guessing their format.
                target.parent.mkdir(parents=True, exist_ok=True)
                target.with_suffix(target.suffix + f".type{kind}").write_bytes(
                    data[payload : payload + size]
                )
            node_rel = next_word & ~0xF

    # The volume root inode follows the 16-byte superblock and volume name.
    _volume_name, root_abs = read_name(data, start + 16)
    walk(root_abs - start, output)
    return {
        "image": str(image),
        "romfs_offset": start,
        "volume_size": volume_size,
        "volume_name": _volume_name,
        "files": files,
        "output": str(output),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("image", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--offset", type=lambda value: int(value, 0))
    args = parser.parse_args()
    import json

    print(json.dumps(extract(args.image, args.output, args.offset), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
