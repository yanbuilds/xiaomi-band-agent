#!/usr/bin/env python3
"""Extract the embedded 2048-bit RSA public key from a Vela image."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


MODULUS_RE = re.compile(rb"(?<![0-9A-F])([0-9A-F]{512})(?![0-9A-F])")


def extract(path: Path) -> dict:
    data = path.read_bytes()
    match = next(MODULUS_RE.finditer(data), None)
    if match is None:
        raise ValueError("no 2048-bit hexadecimal modulus found")
    modulus_hex = match.group(1).decode("ascii")
    exponent = 0x10001
    key = rsa.RSAPublicNumbers(exponent, int(modulus_hex, 16)).public_key()
    pem = key.public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return {
        "offset": match.start(1),
        "modulus_bits": key.key_size,
        "exponent": exponent,
        "modulus_sha256": __import__("hashlib").sha256(
            bytes.fromhex(modulus_hex)
        ).hexdigest(),
        "public_key_pem": pem,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("firmware", type=Path)
    parser.add_argument("--pem", type=Path)
    args = parser.parse_args()
    result = extract(args.firmware)
    if args.pem:
        args.pem.write_text(result["public_key_pem"], encoding="ascii")
    print(json.dumps({k: v for k, v in result.items() if k != "public_key_pem"}, indent=2))


if __name__ == "__main__":
    main()
