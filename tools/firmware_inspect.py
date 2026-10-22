#!/usr/bin/env python3
"""Read-only inspection for Xiaomi Vela firmware packages.

This tool intentionally does not unpack, patch, or flash a firmware image.
It records the package header, version markers, hashes, and printable strings
so that later reverse-engineering work is reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ASCII_RE = re.compile(rb"[ -~]{4,}")
VERSION_RE = re.compile(rb"(?:v(\d+(?:\.\d+){2,4})|T(\d{4}))")


def inspect(path: Path) -> dict:
    data = path.read_bytes()
    strings = []
    for match in ASCII_RE.finditer(data):
        value = match.group().decode("ascii", "replace")
        strings.append({"offset": match.start(), "value": value[:256]})

    markers = sorted(
        {
            next(group for group in match.groups() if group is not None).decode(
                "ascii", "replace"
            )
            for match in VERSION_RE.finditer(data[:2 * 1024 * 1024])
        }
    )
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "header_hex": data[:64].hex(),
        "header_ascii": "".join(chr(b) if 32 <= b < 127 else "." for b in data[:128]),
        "version_markers": markers,
        "strings": strings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--json", type=Path, help="write a JSON report")
    args = parser.parse_args()
    report = inspect(args.firmware)
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json:
        args.json.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
