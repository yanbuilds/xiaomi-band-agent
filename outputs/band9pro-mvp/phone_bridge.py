"""Poll local notifications and hand them to the Gadgetbridge RPK bridge.

The bridge is deliberately a small process: Gadgetbridge remains the only
Bluetooth owner. A notification is marked submitted only after ``adb``
returns success, so a temporary Bluetooth failure leaves it retryable.
"""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import time
from typing import Any, Sequence

import httpx

ACTION = "nodomain.freeyourgadget.gadgetbridge.ACTION_SEND_APP_MESSAGE"
GADGETBRIDGE = "nodomain.freeyourgadget.gadgetbridge"


def _message(item: dict[str, Any]) -> str:
    options = item.get("options", [])
    if not isinstance(options, list) or not 1 <= len(options) <= 3:
        raise ValueError("notification must contain one to three options")
    return json.dumps({
        "type": "question",
        "request_id": item["notification_id"],
        "title": item["title"],
        "text": item["text"],
        "options": options,
        "expires_at": item["expires_at"],
    }, ensure_ascii=False, separators=(",", ":"))


def send(adb: str, serial: str, package: str, item: dict[str, Any]) -> None:
    message = _message(item)
    command = [adb, "-s", serial, "shell", "am", "broadcast", "-a", ACTION,
               "-p", GADGETBRIDGE, "--es", "package", package,
               "--es", "message", shlex.quote(message)]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode:
        raise RuntimeError(completed.stderr.strip() or "adb broadcast failed")


def run_once(client: httpx.Client, api: str, token: str, adb: str,
             serial: str, package: str) -> dict[str, int]:
    headers = {"Authorization": "Bearer " + token}
    response = client.get(api.rstrip("/") + "/v1/notifications", headers=headers)
    response.raise_for_status()
    seen = sent = failed = 0
    for item in response.json():
        seen += 1
        try:
            send(adb, serial, package, item)
            ack = client.post(api.rstrip("/") + "/v1/notifications/" + item["notification_id"] + "/submitted", headers=headers)
            ack.raise_for_status()
            sent += 1
        except (httpx.HTTPError, KeyError, TypeError, ValueError, RuntimeError):
            failed += 1
    return {"seen": seen, "sent": sent, "failed": failed}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api", default=os.environ.get("BAND_LOCAL_API", "http://127.0.0.1:8000"))
    parser.add_argument("--phone-token", default=os.environ.get("PHONE_TOKEN", ""))
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--serial", default=os.environ.get("BAND_PHONE_SERIAL", ""))
    parser.add_argument("--package", default="dev.xiaomi.bandagent")
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args(argv)
    if len(args.phone_token) < 24 or not args.serial:
        parser.error("--phone-token (24+ chars) and --serial are required")
    with httpx.Client(timeout=15) as client:
        while True:
            print(json.dumps(run_once(client, args.api, args.phone_token, args.adb,
                                      args.serial, args.package), ensure_ascii=False), flush=True)
            if args.once:
                return 0
            time.sleep(max(1, args.interval))


if __name__ == "__main__":
    raise SystemExit(main())
