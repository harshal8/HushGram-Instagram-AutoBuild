#!/usr/bin/env python3

import json
import os
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def main():
    build_file = Path("build.json")

    if not build_file.exists():
        raise SystemExit("build.json not found")

    with open(build_file, "r", encoding="utf-8") as f:
        build_info = json.load(f)

    if not build_info:
        raise SystemExit("build.json is empty")

    # Use the first actual build entry.
    info = next(iter(build_info.values()))

    # HushGram version
    patch_text = " ".join([
        str(info.get("patches", "")),
        str(info.get("changelog", "")),
        str(info.get("patches_source", "")),
    ])

    match = re.search(r"v(\d+\.\d+\.\d+)", patch_text)
    hushgram_version = f"v{match.group(1)}" if match else "Unknown"

    # Instagram version
    instagram_version = str(info.get("version", "")).strip()
    if instagram_version and not instagram_version.startswith("v"):
        instagram_version = f"v{instagram_version}"

    # Architecture
    arch = str(info.get("arch_token", "")).strip()

    if not arch:
        arch_map = info.get("archVersion", {})
        if arch_map:
            arch = next(iter(arch_map.keys()))

    # Count distinct patches actually applied.
    applied = set()

    for entry in build_info.values():
        for patch in entry.get("applied_patches", []):
            if isinstance(patch, str) and patch.strip():
                applied.add(patch.strip())

        for patch_list in entry.get("archApplied", {}).values():
            for patch in patch_list:
                if isinstance(patch, str) and patch.strip():
                    applied.add(patch.strip())

    patch_count = len(applied)

    # Current India date/time
    now = datetime.now(ZoneInfo("Asia/Kolkata"))
    date_text = now.strftime("%-d %B %Y")
    time_text = now.strftime("%-I:%M %p IST")

    release_notes = "\n".join([
        f"HushGram: {hushgram_version}",
        f"Patches: {patch_count}",
        f"Instagram: {instagram_version}",
        f"Architecture: {arch}",
        f"Date: {date_text}",
        f"Time: {time_text}",
    ])

    with open("build.md", "w", encoding="utf-8") as f:
        f.write(release_notes + "\n")

    print("Release notes generated:")
    print(release_notes)


if __name__ == "__main__":
    main()
