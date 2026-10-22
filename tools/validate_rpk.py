#!/usr/bin/env python3
"""Validate the debug RPK container used by the Band 9 Pro quick-app route."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from pathlib import Path


def validate(path: Path) -> dict:
    with zipfile.ZipFile(path) as package:
        names = set(package.namelist())
        if "META-INF/CERT" not in names:
            raise ValueError("RPK has no META-INF/CERT")
        with zipfile.ZipFile(io.BytesIO(package.read("META-INF/CERT"))) as cert:
            if "hash.json" not in cert.namelist():
                raise ValueError("CERT is not the expected hash manifest")
            manifest = json.loads(cert.read("hash.json"))
        digests = manifest.get("digests", {})
        mismatches = []
        for name, expected in digests.items():
            if name not in names:
                mismatches.append({"name": name, "error": "missing"})
                continue
            actual = hashlib.sha256(package.read(name)).hexdigest()
            if actual != expected:
                mismatches.append({"name": name, "expected": expected,
                                   "actual": actual})
        return {
            "path": str(path),
            "files": len(names),
            "cert_type": "hash.json",
            "hashed_files": len(digests),
            "mismatches": mismatches,
            "valid": not mismatches,
            "warning": "hash manifest integrity is not a firmware signature",
        }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("rpk", type=Path)
    args = ap.parse_args()
    result = validate(args.rpk)
    print(json.dumps(result, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
