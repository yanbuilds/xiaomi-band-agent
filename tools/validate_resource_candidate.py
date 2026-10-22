#!/usr/bin/env python3
"""Prove a candidate changes only one non-code n67cn ZIP archive."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from index_n67cn_archives import index


PROTECTED = {"vela_ap.bin", "vela_bl.bin", "vela_bl2.bin", "vela_factory.bin"}


def validate(original: Path, candidate: Path) -> dict:
    a, b = index(original), index(candidate)
    errors: list[str] = []
    if len(a) != len(b):
        errors.append(f"archive count differs: {len(a)} != {len(b)}")
    changed = []
    for left, right in zip(a, b):
        if (left["start"], left["end"]) != (right["start"], right["end"]):
            errors.append("archive boundaries changed")
        if left["sha256"] != right["sha256"]:
            changed.append({"start": left["start"], "end": left["end"],
                            "original": left, "candidate": right})
        left_names = {m["name"] for m in left["members"]}
        right_names = {m["name"] for m in right["members"]}
        if left_names != right_names:
            errors.append(f"member names changed at {left['start']:#x}")
        if PROTECTED & left_names and left["sha256"] != right["sha256"]:
            errors.append(f"protected archive changed at {left['start']:#x}")
    if len(changed) != 1:
        errors.append(f"expected one changed archive, found {len(changed)}")
    result = {
        "original": str(original),
        "candidate": str(candidate),
        "changed_archives": changed,
        "errors": errors,
        "valid": not errors,
        "device_acceptance": "not verified; this proves resource-only structure, not OTA signature acceptance",
    }
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("original", type=Path)
    ap.add_argument("candidate", type=Path)
    args = ap.parse_args()
    result = validate(args.original, args.candidate)
    print(json.dumps(result, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
