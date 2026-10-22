#!/usr/bin/env python3
"""Count selected Mi Fitness protocol markers without printing log content."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

MARKERS = {
    "ota": re.compile(rb"ota", re.I),
    "verify": re.compile(rb"verif|signature|sign", re.I),
    "auth": re.compile(rb"auth|nonce|hkdf|hmac", re.I),
    "spp": re.compile(rb"spp|rfcomm|classic", re.I),
    "mass": re.compile(rb"massdata|mass", re.I),
    "prepare": re.compile(rb"prepareota|prepare", re.I),
    "error": re.compile(rb"error|fail|reject", re.I),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("log", type=Path)
    args = ap.parse_args()
    data = args.log.read_bytes()
    counts = {name: 0 for name in MARKERS}
    line_count = 0
    for line in data.splitlines():
        line_count += 1
        for name, pattern in MARKERS.items():
            if pattern.search(line):
                counts[name] += 1
    result = {
        "file_name": args.log.name,
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "line_count": line_count,
        "marker_line_counts": counts,
        "content_printed": False,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
