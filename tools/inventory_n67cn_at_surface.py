#!/usr/bin/env python3
"""Inventory the n67cn AP's compiled AT command names.

This is a static, read-only audit.  It does not open a serial port, send an
AT command, or imply that the command listener is reachable on a retail band.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

COMMAND_RE = re.compile(rb"AT\^(?:[A-Z0-9_]+|[A-Z0-9_]+\?)")

# Names that could alter boot, storage, or device state.  The classification is
# intentionally conservative: a string in a binary is not proof of behavior.
HIGH_RISK = {
    "AT^OTA_UPDATE", "AT^JUMP", "AT^FTYRESET", "AT^POWER_OFF",
    "AT^REBOOT", "AT^CLEAN_DIR", "AT^NEW_FILE", "AT^DELETE_DIR",
    "AT^CRASH", "AT^UART", "AT^MCU_IIC_MODE", "AT^OTA_USR",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    ap.add_argument("--json", type=Path)
    args = ap.parse_args()
    data = args.image.read_bytes()
    seen: dict[str, dict[str, object]] = {}
    for m in COMMAND_RE.finditer(data):
        raw = m.group().decode("ascii")
        # A trailing '?' is part of the query form in the string table.
        name = raw
        row = seen.setdefault(name, {"name": name, "offsets": [], "risk": "high" if name in HIGH_RISK else "unknown"})
        row["offsets"].append(f"0x{m.start():x}")
    commands = sorted(seen.values(), key=lambda row: str(row["name"]))
    report = {
        "image": str(args.image),
        "read_only": True,
        "command_count": len(commands),
        "commands": commands,
        "interpretation": [
            "The AP contains an internal AT command vocabulary.",
            "Static strings do not prove an external transport, parser reachability, or authorization state.",
            "High-risk names must not be sent without a board-level backup and recovery path.",
            "No command in this report bypasses the vendor RSA firmware signature gate.",
        ],
    }
    text = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.json:
        args.json.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
