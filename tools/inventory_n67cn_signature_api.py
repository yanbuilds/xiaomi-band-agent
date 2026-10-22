#!/usr/bin/env python3
"""Record public signature-verifier markers from an n67cn AP image.

This is a string-level inventory only.  It does not patch code, bypass a
signature, or infer that a debug/unlock path exists.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


TERMS = (
    "app_verify.c",
    "app_verify_info",
    "mbedtls_pk_parse_public_key",
    "mbedtls_pk_verify",
    "verify_block_signature",
    "rsaEncryption",
    "RSASSA-PSS",
    "signature_block",
    "central_directory_offset",
    "sign verify failed",
    "verify ok!",
)


def inventory(path: Path) -> dict:
    data = path.read_bytes()
    text = data.decode("latin1", "ignore")
    printable = re.findall(r"[ -~]{4,}", text)
    return {
        "path": str(path),
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "markers": {term: text.count(term) for term in TERMS},
        "interpretation": (
            "The AP contains an application/package signature-verification "
            "surface. This inventory cannot recover a private key or prove "
            "that any host-side flash command is exposed."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("image", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(inventory(args.image), indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
