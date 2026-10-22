#!/usr/bin/env python3
"""Report which n67cn components an official incremental package replaces.

This is an offline inspection tool.  It does not infer that a modified
package is signed or accepted by a device; it only compares the ZIP members
inside an official update with the archive index of a full image.
"""

from __future__ import annotations

import argparse
import io
import json
import zipfile
from pathlib import Path


PROTECTED = {"vela_bl.bin", "vela_bl2.bin", "vela_ap.bin", "vela_factory.bin"}


def load_index(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "archives" not in data:
        raise ValueError(f"not an archive index: {path}")
    return data


def report(full_index_path: Path, incremental_path: Path) -> dict:
    full = load_index(full_index_path)
    inc = load_index(incremental_path)
    image = Path(inc["image"]).read_bytes()
    archives = []
    names = []
    for entry in inc["archives"]:
        blob = image[entry["start"]:entry["end"]]
        with zipfile.ZipFile(io.BytesIO(blob)) as package:
            members = [info.filename for info in package.infolist()]
        names.extend(members)
        archives.append({
            "start": entry["start"],
            "end": entry["end"],
            "size": entry["end"] - entry["start"],
            "members": members,
            "sha256": entry["sha256"],
        })

    full_names = {
        member["name"]
        for entry in full["archives"]
        for member in entry["members"]
    }
    return {
        "full_image": full.get("image"),
        "incremental_image": inc.get("image"),
        "incremental_archive_count": len(archives),
        "incremental_archives": archives,
        "protected_components_present": sorted(PROTECTED & set(names)),
        "unknown_members": sorted(set(names) - full_names),
        "interpretation": (
            "Official 187-to-190 package replaces bootloader/AP/factory components; "
            "this is evidence of the vendor update layout, not a way to sign a custom package."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("full_index", type=Path)
    parser.add_argument("incremental_index", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = report(args.full_index, args.incremental_index)
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        args.output.write_text(payload + "\n", encoding="utf-8")
    print(payload)


if __name__ == "__main__":
    main()
