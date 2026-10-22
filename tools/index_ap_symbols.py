#!/usr/bin/env python3
"""Index useful symbol-like strings in an extracted Vela AP image."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("-o", "--output", type=Path, required=True)
    ap.add_argument("--load-address", type=lambda x: int(x, 0), default=0x0C100000)
    args = ap.parse_args()
    data = args.image.read_bytes()
    # Keep symbols relevant to the bridge, notification, health and updater
    # paths.  These are source/function names retained by the vendor build.
    wanted = re.compile(
        rb"(?:interconnect|notification|notify|vibrat|sleep|heartrate|heart_rate|"
        rb"oxygen|record_file|mass_data|gatt|ota|verify|signature|protobuf|voice|reply)",
        re.I,
    )
    result = []
    for m in re.finditer(rb"[ -~]{4,160}", data):
        text = m.group().decode("utf-8", "replace")
        if wanted.search(m.group()):
            result.append({"offset": m.start(), "address": hex(args.load_address + m.start()), "text": text})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({"image": str(args.image), "symbols": len(result), "output": str(args.output)}, indent=2))


if __name__ == "__main__":
    main()
