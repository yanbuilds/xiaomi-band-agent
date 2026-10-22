#!/usr/bin/env python3
"""Verify the n67cn AP contains the expected NAND factory-test markers."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


MARKERS = (
    b"NANDFLASH_INFO=OK",
    b"model:gd5f2gm7",
    b"nandflash_read_page",
    b"nandflash_write_page",
    b"nandflash_erase_block",
    b"nandflash_get_size",
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ap", type=Path)
    args = ap.parse_args()
    data = args.ap.read_bytes()
    result = {
        "path": str(args.ap),
        "size": len(data),
        "markers": {m.decode(): data.find(m) for m in MARKERS},
    }
    result["valid"] = all(v >= 0 for v in result["markers"].values())
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["valid"] else 1)


if __name__ == "__main__":
    main()
