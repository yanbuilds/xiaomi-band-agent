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
    if data[:4] != b"`ZZ~":
        errors.append("missing outer Vela magic")
    header = {
        "version": data[4:12].split(b"\0", 1)[0].decode("ascii", "replace")
        if len(data) >= 12 else "",
        "mode": int.from_bytes(data[0x48:0x4C], "little")
        if len(data) >= 0x4C else None,
        "table_offset": int.from_bytes(data[0x50:0x54], "little")
        if len(data) >= 0x54 else None,
        "payload_offset": int.from_bytes(data[0x54:0x58], "little")
        if len(data) >= 0x58 else None,
    }
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
    if file_num is not None:
        mode = header["mode"]
        if mode == 0 and file_num != len(archives):
            errors.append(f"full image file_num={file_num}, archives={len(archives)}")
        if mode == 2 and file_num < len(archives):
            errors.append(f"incremental file_num={file_num} smaller than archives={len(archives)}")
    result = {
        "path": str(path),
        "size": len(data),
        "archives": len(archives),
        "outer_header": header,
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
