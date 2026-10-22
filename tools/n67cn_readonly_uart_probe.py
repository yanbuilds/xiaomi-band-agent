#!/usr/bin/env python3
"""Prepare or run the ATC1441 BES flasher in flash-read mode.

The upstream programmer is loaded into RAM, so this is not electrically
passive even though it never writes non-volatile flash.  The default is a
dry-run; ``--execute-read-only`` is required to send bytes.  The wrapper never
passes ``--write`` and caps the default read at 1 MiB.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path


MAGIC = bytes.fromhex("ff ff ff ff 00 00 05 00 00 00 00 00")


def classify(path: Path) -> dict:
    data = path.read_bytes()
    return {
        "size": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "vela_component_header": data[:12] == MAGIC,
        "prefix": data[:32].hex(" "),
        "warning": "read-only classification; not proof of n67cn Pro write compatibility",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True, help="UART port, for example COM3")
    ap.add_argument("--flasher", type=Path, required=True,
                    help="ATC1441 bes2700_flasher.py")
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--address", default="0x28000000")
    ap.add_argument("--size", default="0x100000",
                    help="maximum default read is 1 MiB")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--execute-read-only", action="store_true",
                    help="actually send the upstream read-only probe; omitted means dry-run")
    args = ap.parse_args()
    size = int(args.size, 0)
    if size <= 0 or size > 0x100000:
        ap.error("--size must be between 1 and 0x100000 for the probe")
    if not args.flasher.is_file():
        ap.error(f"flasher not found: {args.flasher}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(args.flasher), "--port", args.port,
           "--address", args.address, "--size", hex(size),
           "--output", str(args.output), "--no-log"]
    print("read-only UART probe:", " ".join(cmd))
    print("This wrapper never sends the upstream --write option.")
    if not args.execute_read_only:
        print("dry-run: no UART bytes were sent; pass --execute-read-only to proceed")
        return 0
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        return result.returncode
    report = classify(args.output)
    report.update({"port": args.port, "address": args.address,
                   "requested_size": size, "output": str(args.output)})
    report_path = args.report or args.output.with_suffix(args.output.suffix + ".json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
