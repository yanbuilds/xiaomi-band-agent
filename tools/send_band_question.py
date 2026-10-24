#!/usr/bin/env python3
"""Send a Band Agent question through Gadgetbridge's RPK debug bridge."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import time
from typing import Sequence

ACTION = "nodomain.freeyourgadget.gadgetbridge.ACTION_SEND_APP_MESSAGE"
GADGETBRIDGE = "nodomain.freeyourgadget.gadgetbridge"


def build_message(args: argparse.Namespace) -> str:
    if not 1 <= len(args.option) <= 3:
        raise ValueError("Band Agent supports one to three --option values")
    return json.dumps(
        {
            "type": "question",
            "request_id": args.request_id,
            "title": args.title,
            "text": args.text,
            "options": [{"id": str(i), "text": text} for i, text in enumerate(args.option, 1)],
            "expires_at": int(time.time()) + args.ttl,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def send(adb: str, serial: str | None, package: str, message: str, *, dry_run: bool) -> int:
    command = [adb] + (["-s", serial] if serial else []) + ["shell", "am", "broadcast", "-a", ACTION, "-p", GADGETBRIDGE,
               "--es", "package", package, "--es", "message", shlex.quote(message)]
    if dry_run:
        print(json.dumps(command, ensure_ascii=False))
        return 0
    return subprocess.run(command, check=False).returncode


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", default="dev.xiaomi.bandagent")
    parser.add_argument("--request-id", default="manual-test")
    parser.add_argument("--title", default="Band Agent")
    parser.add_argument("--text", required=True)
    parser.add_argument("--option", action="append", required=True)
    parser.add_argument("--ttl", type=int, default=300)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default=None, help="ADB device serial, for example 192.168.10.189:37517")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    try:
        message = build_message(args)
    except ValueError as exc:
        parser.error(str(exc))
    return send(args.adb, args.serial, args.package, message, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
