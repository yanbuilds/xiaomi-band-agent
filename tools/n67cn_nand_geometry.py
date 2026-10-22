#!/usr/bin/env python3
"""Print the conservative geometry model for the n67cn GD5F2GM7 NAND.

The values are a planning model from the GD5F2GM7 datasheet and the AP
factory-test marker.  A real dump must still confirm ECC/OOB and bad-block
behavior before a writer is implemented.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


MODEL = {
    "model": "GD5F2GM7",
    "jedec_id_hex": "c882c8",
    "density_bits": 2_000_000_000,
    "capacity_bytes_nominal": 256 * 1024 * 1024,
    "page_data_bytes": 2048,
    "page_oob_bytes_ecc_on": 64,
    "page_oob_bytes_ecc_off": 128,
    "pages_per_block": 64,
    "block_bytes_data": 128 * 1024,
    "blocks_nominal": 2048,
    "status": "planning_only; confirm with n67cn hardware dump",
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ap", type=Path,
                    help="optional vela_ap.bin; verify gd5f2gm7 marker")
    args = ap.parse_args()
    result = dict(MODEL)
    if args.ap:
        data = args.ap.read_bytes()
        result["ap_path"] = str(args.ap)
        result["ap_has_model_marker"] = b"model:gd5f2gm7" in data
        result["ap_has_nand_api_markers"] = all(
            marker in data for marker in (
                b"nandflash_read_page", b"nandflash_write_page",
                b"nandflash_erase_block", b"nandflash_get_size",
            )
        )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
