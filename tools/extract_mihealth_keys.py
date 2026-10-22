#!/usr/bin/env python3
"""Extract Xiaomi wearable key fields from exported Mi Health logs.

The values are credentials.  By default this tool only prints masked values;
use --out to write a local, ignored file for the sync client.
"""
from __future__ import annotations

import argparse
import glob
import re
from pathlib import Path

FIELDS = ("beaconKey", "irqKey", "encryptKey", "token", "authKey", "huamiAuthKey")


def scan(paths: list[Path]) -> dict[str, list[str]]:
    found: dict[str, list[str]] = {field: [] for field in FIELDS}
    for path in paths:
        text = path.read_text(encoding="utf-8", errors="ignore")
        for field in FIELDS:
            pattern = rf'"{field}"\s*:\s*"([0-9a-fA-F]{{32}})"'
            for value in re.findall(pattern, text):
                if value not in found[field]:
                    found[field].append(value)
    return found


def masked(value: str) -> str:
    return f"{value[:4]}…{value[-4:]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("logs", nargs="+", type=Path)
    parser.add_argument("--out", type=Path, help="write local credentials (mode 0600)")
    args = parser.parse_args()
    paths = [Path(item) for pattern in args.logs for item in (glob.glob(str(pattern)) or [str(pattern)])]
    found = scan(paths)
    for field, values in found.items():
        if values:
            print(f"{field}: " + ", ".join(masked(value) for value in values))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"{field}={values[-1]}" for field, values in found.items() if values]
        args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            args.out.chmod(0o600)
        except OSError:
            pass


if __name__ == "__main__":
    main()
