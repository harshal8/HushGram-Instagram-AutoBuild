#!/usr/bin/env python3

import os
import re
import json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from naming import extract_arch, extract_version


def get_hushgram_version(info):
    """Get the patch-source release tag, e.g. v0.0.6."""
    changelog = (info.get("changelog") or "").strip()

    if changelog:
        url = changelog.split()[0]

        if "/tag/" in url:
            tag = url.split("/tag/")[-1].strip("/")
            if tag:
                return tag if tag.startswith("v") else f"v{tag}"

        if "/releases/" in url:
            tag = url.split("/releases/")[-1].strip("/")
            if tag:
                return tag if tag.startswith("v") else f"v{tag}"

    # Fallback to the resolved patch bundle filename/reference.
    patches_ref = (info.get("patches") or "").strip()

    if patches_ref:
        match = re.search(
            r"v?\d+(?:\.\d+)+",
            patches_ref
        )
        if match:
            tag = match.group(0)
            return tag if tag.startswith("v") else f"v{tag}"

    return "unknown"


def get_applied_patches(info, raw_arch):
    """
    Get the actual patches applied to this architecture.
    Prefer per-architecture metadata because different architectures
    can theoretically have different patch sets.
    """

    arch_applied = info.get("archApplied") or {}

    # Exact raw architecture, e.g. arm64-v8a
    patches = arch_applied.get(raw_arch)

    if patches is None:
        # Normalized architecture fallback, e.g. arm64
        normalized = (
            "arm64"
            if "arm64" in raw_arch or "aarch64" in raw_arch
            else raw_arch
        )
        patches = arch_applied.get(normalized)

    # Final fallback to the normal applied_patches field.
    if patches is None:
        patches = info.get("applied_patches") or []

    if not isinstance(patches, list):
        return []

    # Remove duplicates while preserving order.
    return list(dict.fromkeys(patches))


def main():
    build_dir = Path("build")
    build_json_file = Path("build.json")

    if not build_json_file.exists():
        raise SystemExit("build.json not found")

    with open(build_json_file, "r", encoding="utf-8") as f:
        build_info = json.load(f)

    if not build_info:
        raise SystemExit("build.json is empty")

    if not build_dir.exists():
        raise SystemExit("build/ directory not found")

    # Find APKs actually produced by this build.
    apk_files = sorted(
        f for f in build_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".apk"
    )

    if not apk_files:
        raise SystemExit("No APK found in build/")

    # This builder currently has one HushGram Instagram target.
    # Find the build-info entry corresponding to the APK.
    selected = None
    selected_apk = None

    for apk in apk_files:
        apk_name = apk.name

        for target_key, info in build_info.items():
            file_prefix = info.get("name") or target_key

            if apk_name.lower().startswith(
                file_prefix.lower() + "-v"
            ):
                selected = info
                selected_apk = apk_name
                break

        if selected:
            break

    if selected is None:
        raise SystemExit(
            f"Could not match APK to build.json: {apk_files[0].name}"
        )

    # Actual Instagram version from APK filename.
    configured_version = selected.get("version", "")
    instagram_version = extract_version(
        selected_apk,
        configured_version
    )

    # Actual architecture from APK filename.
    architecture = extract_arch(
        selected_apk,
        configured_version
    )

    # HushGram release version.
    hushgram_version = get_hushgram_version(selected)

    # Actual number of patches applied to this APK.
    applied_patches = get_applied_patches(
        selected,
        architecture
    )

    patch_count = len(applied_patches)

    # India Standard Time.
    now_ist = datetime.now(
        ZoneInfo("Asia/Kolkata")
    )

    date_text = now_ist.strftime("%-d %B %Y")
    time_text = now_ist.strftime("%-I:%M %p")

    # Exact release-note format requested.
    lines = [
        f"HushGram: {hushgram_version}",
        f"Patches: {patch_count}",
        f"Instagram: v{instagram_version}",
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
