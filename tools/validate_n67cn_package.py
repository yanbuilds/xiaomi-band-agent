#!/usr/bin/env python3
"""Offline structural validation for a concatenated n67cn image."""

from __future__ import annotations

import argparse
import io
import json
import struct
import zipfile
from pathlib import Path

from index_n67cn_archives import index


def validate(path: Path) -> dict:
    data = path.read_bytes()
    archives = index(path)
    errors: list[str] = []
    version = ""
    file_num = None
    file_size = None
    for item in archives:
        blob = data[item["start"] : item["end"]]
        try:
            with zipfile.ZipFile(io.BytesIO(blob)) as archive:
                for member in archive.infolist():
                    archive.read(member)
                if any(m["name"] == "version.ini" for m in item["members"]):
                    text = archive.read("version.ini").decode("ascii", "replace")
                    fields = {
                        key.strip(): value.strip()
                        for line in text.splitlines()
                        if "=" in line
                        for key, value in [line.split("=", 1)]
                    }
                    version = fields.get("version", "")
                    file_num = int(fields.get("file_num", "-1"))
                    file_size = int(fields.get("file_size", "-1"))
        except (OSError, ValueError, zipfile.BadZipFile, KeyError) as exc:
            errors.append(f"{item['start']:#x}: {exc}")
    if file_num is not None and file_num != len(archives):
        errors.append(f"version.ini file_num={file_num}, archives={len(archives)}")
    result = {
        "path": str(path),
        "size": len(data),
        "archives": len(archives),
        "version": version,
        "declared_file_num": file_num,
        "declared_uncompressed_file_size": file_size,
        "errors": errors,
        "valid": not errors,
        "device_acceptance": "not verified; structural checks do not replace OTA signature verification",
    }
    return result


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("image", type=Path)
    args = ap.parse_args()
    result = validate(args.image)
    print(json.dumps(result, indent=2))
    if not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
