#!/usr/bin/env python3
"""Analyze a raw GD5F2GM7 dump without writing to the device.

The default layout assumes internal ECC is enabled: 2048 data bytes followed
by 64 OOB bytes per page, 64 pages per erase block.  This tool only reports
geometry and bad-block markers; it never attempts ECC correction or NAND I/O.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


PAGE_DATA = 2048
OOB_ECC_ON = 64
PAGES_PER_BLOCK = 64


def analyze(path: Path, oob: int) -> dict:
    raw = path.read_bytes()
    record = PAGE_DATA + oob
    complete_pages, remainder = divmod(len(raw), record)
    complete_blocks, partial_pages = divmod(complete_pages, PAGES_PER_BLOCK)
    bad_blocks: list[int] = []
    # Standard GigaDevice SPI-NAND bad-block marker is in OOB byte 0 of the
    # first or second page; report candidates, without declaring them bad when
    # the dump was data-only or the vendor layout differs.
    if oob:
        for block in range(complete_blocks):
            first = block * PAGES_PER_BLOCK * record
            second = first + record
            markers = (raw[first + PAGE_DATA], raw[second + PAGE_DATA])
            if any(value != 0xFF for value in markers):
                bad_blocks.append(block)
    return {
        "path": str(path),
        "size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "page_data_bytes": PAGE_DATA,
        "oob_bytes": oob,
        "page_record_bytes": record,
        "complete_pages": complete_pages,
        "complete_blocks": complete_blocks,
        "partial_pages": partial_pages,
        "remainder_bytes": remainder,
        "bad_block_marker_candidates": bad_blocks,
        "warning": "marker interpretation must be confirmed against the n67cn driver",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("dump", type=Path)
    ap.add_argument("--oob", type=int, default=OOB_ECC_ON,
                    choices=(0, 64, 128),
                    help="0 for data-only, 64 for ECC-on, 128 for ECC-off")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    result = analyze(args.dump, args.oob)
    print(json.dumps(result, indent=2))
    if args.report:
        args.report.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
