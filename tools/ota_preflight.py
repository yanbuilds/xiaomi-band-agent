#!/usr/bin/env python3
"""Run a no-write OTA preflight for an n67cn candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from validate_n67cn_package import validate as validate_package
from verify_n67cn_outer_signature import verify as verify_outer_signature


def version_tuple(value: str) -> tuple[int, ...]:
    match = re.fullmatch(r"(\d+(?:\.\d+){2,3})", value)
    if not match:
        raise ValueError(f"invalid firmware version: {value}")
    return tuple(int(x) for x in match.group(1).split("."))


def preflight(path: Path, current_version: str, public_key: Path | None = None) -> dict:
    package = validate_package(path)
    data = path.read_bytes()
    candidate_version = package["version"]
    checks = {
        "package_valid": package["valid"],
        "md5": hashlib.md5(data).hexdigest(),
        "sha256": hashlib.sha256(data).hexdigest(),
        "same_version_warning": version_tuple(candidate_version) == version_tuple(current_version),
        "version_is_newer": version_tuple(candidate_version) > version_tuple(current_version),
    }
    signature = None
    if public_key is not None:
        try:
            signature = verify_outer_signature(path, public_key)
        except Exception as exc:
            signature = {
                "signature_verified": False,
                "error": type(exc).__name__,
            }
    signature_ok = public_key is None or bool(signature and signature.get("signature_verified"))
    return {
        "image": str(path),
        "current_version": current_version,
        "candidate_version": candidate_version,
        "checks": checks,
        "signature": signature,
        "send_allowed_by_preflight": bool(package["valid"] and not checks["same_version_warning"] and signature_ok),
        "warning": "Without --public-key this tool cannot establish device signature acceptance; with it, the local RSA trailer must verify.",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--current-version", required=True)
    ap.add_argument("--public-key", type=Path,
                    help="n67cn PEM public key; require and verify the outer RSA trailer")
    args = ap.parse_args()
    result = preflight(args.image, args.current_version, args.public_key)
    print(json.dumps(result, indent=2))
    if not result["send_allowed_by_preflight"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
