#!/usr/bin/env python3
"""Conservative offline audit for n67cn firmware candidates.

This tool never connects to a device and never signs or transmits an image.
It reports a candidate as flashable only when the supplied n67cn public key
verifies its outer signature. Structural ZIP/CRC validity alone is rejected.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path


def _load_verifier():
    path = Path(__file__).with_name("verify_n67cn_outer_signature.py")
    spec = importlib.util.spec_from_file_location("n67cn_verifier", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load signature verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.verify


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--public-key", type=Path, required=True)
    args = ap.parse_args()
    verify = _load_verifier()
    result = verify(args.image, args.public_key)
    result["device_write_attempted"] = False
    result["flashable"] = bool(result["signature_verified"])
    result["reason"] = (
        "outer RSA signature verified"
        if result["flashable"]
        else "signature invalid; structure alone is insufficient"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["flashable"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
