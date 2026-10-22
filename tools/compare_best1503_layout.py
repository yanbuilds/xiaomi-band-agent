"""Compare a Band 9 Pro extracted image with the public BEST1503 flasher.

This is deliberately read-only. It reports structural compatibility signals
without attempting UART access or producing a flashable image.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    return {
        "path": str(path),
        "size": len(data),
        "sha256": sha256(path),
        "prefix14": data[:14].hex(" "),
        "vela_header": data[:12] == bytes.fromhex("ff ff ff ff 00 00 05 00 00 00 00 00"),
        "thumb_reset_stub": data[12:24].hex(" "),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--component", action="append", type=Path, required=True)
    ap.add_argument("--programmer", type=Path, required=True)
    args = ap.parse_args()
    result = {
        "components": [inspect(p) for p in args.component],
        "programmer": inspect(args.programmer),
        "public_flasher_signals": {
            "flash_base": "0x28000000",
            "flash_size": "0x400000",
            "baud": 921600,
            "protocol": "BESLink 0x50/0x53/0x54/0x55/0x60/0x61/0x62",
            "warning": "Signals are not proof that this board accepts a custom image.",
        },
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
