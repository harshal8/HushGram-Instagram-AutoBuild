#!/usr/bin/env python3

import os
import re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from naming import extract_arch, extract_version, normalize_arch


def main():
    next_ver_code = os.environ.get("NEXT_VER_CODE", "").strip()

    build_dir = Path("build")
    build_json_file = Path("build.json")

    build_info = {}

    if build_json_file.exists():
        try:
            import json

            with open(build_json_file, "r", encoding="utf-8") as f:
                build_info = json.load(f)
        except Exception:
            build_info = {}

    # Find the first APK produced by the build.
    apk_files = []

    if build_dir.exists():
        apk_files = sorted(
            f.name
            for f in build_dir.iterdir()
            if f.is_file() and f.suffix.lower() == ".apk"
        )

    if not apk_files:
        raise SystemExit("No APK found in build/")

    apk_name = apk_files[0]

    # Find matching build information.
    version = ""
    architecture = ""

    for target_key, info in build_info.items():
        file_prefix = info.get("name", "")
        app_version = info.get("version", "")

        if file_prefix and apk_name.lower().startswith(file_prefix.lower() + "-v"):
            version = extract_version(apk_name, app_version)
            raw_arch = extract_arch(apk_name, app_version)
            architecture = normalize_arch(raw_arch)
            break

    # Fallback: extract directly from APK filename.
    if not version:
        match = re.search(r"-v(.+?)-(arm64-v8a|arm-v7a|x86_64|x86)\.apk$", apk_name)
        if match:
            version = match.group(1)

    if not architecture:
        if "-arm64-v8a.apk" in apk_name:
            architecture = "arm64-v8a"
        elif "-arm-v7a.apk" in apk_name:
            architecture = "arm-v7a"
        elif "-x86_64.apk" in apk_name:
            architecture = "x86_64"
        elif "-x86.apk" in apk_name:
            architecture = "x86"
        else:
            architecture = "unknown"

    # Current time in India.
    now_ist = datetime.now(ZoneInfo("Asia/Kolkata"))

    date_text = now_ist.strftime("%-d %B %Y")
    time_text = now_ist.strftime("%-I:%M %p")

    # Keep release notes minimal.
    lines = [
        f"Instagram: v{version}",
        f"Architecture: {architecture}",
        f"Date: {date_text}",
        f"Time: {time_text} IST",
    ]

    content = "\n".join(lines) + "\n"

    with open("build.md", "w", encoding="utf-8") as f:
        f.write(content)

    print("Generated release notes:")
    print(content)


if __name__ == "__main__":
    main()
