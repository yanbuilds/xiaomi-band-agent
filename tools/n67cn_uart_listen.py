#!/usr/bin/env python3
"""Passive UART listener for n67cn BL2 bring-up.

The default mode never writes bytes, toggles reset, or enables DTR/RTS.  It is
intended for a logic-level adapter connected to a suspected test pad.
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", required=True)
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--seconds", type=float, default=15)
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    if args.seconds <= 0 or args.seconds > 300:
        ap.error("--seconds must be between 0 and 300")
    try:
        import serial  # type: ignore
    except ImportError:
        ap.error("pyserial is required: python -m pip install pyserial")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    # Explicitly disable modem-control lines and do not call write().
    with serial.Serial(None, args.baud, timeout=0.2,
                       write_timeout=0, dsrdtr=False, rtscts=False) as ser:
        ser.port = args.port
        ser.dtr = False
        ser.rts = False
        ser.open()
        end = time.monotonic() + args.seconds
        data = bytearray()
        while time.monotonic() < end:
            chunk = ser.read(4096)
            if chunk:
                data.extend(chunk)
                print(chunk.decode("utf-8", "replace"), end="", flush=True)
    args.output.write_bytes(data)
    print(f"\nread {len(data)} bytes -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
