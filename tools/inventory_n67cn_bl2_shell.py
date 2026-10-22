#!/usr/bin/env python3
"""Inventory the observable NuttX shell surface in a n67cn BL2 image.

This is deliberately a read-only triage tool.  It does not infer that a
shell command bypasses the OTA signature check and it never writes to a
device.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


DEFAULT_KEYS = (
    "bl2>", "/dev/console", "/dev/bes_flash", "flash_bl", "flash_bl2",
    "flash_ap", "flash_config", "bes_reserved", "DRVUSB", "ESHELL",
    "SecureBoot Status", "sign verify", "ota", "reboot", "resetcause",
    "dd", "boardctl", "bootloader", "recovery", "factory",
)


def strings(path: Path):
    data = path.read_bytes()
    for m in re.finditer(rb"[\x20-\x7e]{4,}(?=\x00)", data):
        yield m.start(), m.group().decode("ascii", "replace")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    keys = tuple(k.lower() for k in DEFAULT_KEYS)
    rows = [
        {"offset": f"0x{off:x}", "text": text}
        for off, text in strings(args.image)
        if any(k in text.lower() for k in keys)
    ]
    report = {
        "image": str(args.image),
        "read_only": True,
        "interpretation": [
            "BL2 contains an NuttX NSH prompt and flash device names.",
            "These strings establish an observable bootloader shell surface only.",
            "They do not prove UART/USB access on an assembled Band 9 Pro.",
            "They do not bypass the RSA signature gate used by the OTA path.",
        ],
        "matches": rows,
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json:
        args.json.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
