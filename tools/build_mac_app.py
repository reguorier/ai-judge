#!/usr/bin/env python3
"""Build a local clickable macOS AI Judge.app wrapper."""

from __future__ import annotations

import json
import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_NAME = "AI Judge"
APP_DIR = PROJECT_ROOT / "dist" / "mac" / f"{APP_NAME}.app"
CONTENTS = APP_DIR / "Contents"
MACOS = CONTENTS / "MacOS"
RESOURCES = CONTENTS / "Resources"
EXECUTABLE = "AIJudgeDesktop"
DEFAULT_ARCH = "arm64"
DEFAULT_DEPLOYMENT_TARGET = "13.0"


def main() -> int:
    swift = shutil.which("swiftc")
    if not swift:
        print("swiftc not found. Install Xcode Command Line Tools first.", file=sys.stderr)
        return 1

    MACOS.mkdir(parents=True, exist_ok=True)
    RESOURCES.mkdir(parents=True, exist_ok=True)
    cache_dir = PROJECT_ROOT / ".cache"
    clang_cache = cache_dir / "clang"
    swift_cache = cache_dir / "swift"
    clang_cache.mkdir(parents=True, exist_ok=True)
    swift_cache.mkdir(parents=True, exist_ok=True)

    executable_path = MACOS / EXECUTABLE
    swift_source = PROJECT_ROOT / "desktop" / "AIJudgeDesktop.swift"
    arch = os.environ.get("AI_JUDGE_DESKTOP_ARCH", DEFAULT_ARCH)
    deployment_target = os.environ.get("AI_JUDGE_MACOS_DEPLOYMENT_TARGET", DEFAULT_DEPLOYMENT_TARGET)
    env = os.environ.copy()
    env["CLANG_MODULE_CACHE_PATH"] = str(clang_cache)
    env["SWIFT_MODULE_CACHE_PATH"] = str(swift_cache)
    env["MACOSX_DEPLOYMENT_TARGET"] = deployment_target
    subprocess.run(
        [
            swift,
            str(swift_source),
            "-target",
            f"{arch}-apple-macos{deployment_target}",
            "-o",
            str(executable_path),
            "-framework",
            "Cocoa",
            "-framework",
            "WebKit",
        ],
        check=True,
        env=env,
    )
    executable_path.chmod(0o755)

    info = {
        "CFBundleDevelopmentRegion": "en",
        "CFBundleDisplayName": APP_NAME,
        "CFBundleExecutable": EXECUTABLE,
        "CFBundleIconFile": "AIJudgeIcon",
        "CFBundleIdentifier": "local.ai-judge.desktop",
        "CFBundleInfoDictionaryVersion": "6.0",
        "CFBundleName": APP_NAME,
        "CFBundlePackageType": "APPL",
        "CFBundleShortVersionString": "3.8.0",
        "CFBundleVersion": "3.8.0",
        "LSMinimumSystemVersion": deployment_target,
        "NSHighResolutionCapable": True,
    }
    with (CONTENTS / "Info.plist").open("wb") as fh:
        plistlib.dump(info, fh)

    icon_source = PROJECT_ROOT / "assets" / "AIJudgeIcon.icns"
    if icon_source.exists():
        shutil.copy2(icon_source, RESOURCES / "AIJudgeIcon.icns")

    config = {
        "projectRoot": os.environ.get("AI_JUDGE_DESKTOP_PROJECT_ROOT", str(PROJECT_ROOT)),
        "host": os.environ.get("AI_JUDGE_DESKTOP_HOST", "127.0.0.1"),
        "port": int(os.environ.get("AI_JUDGE_DESKTOP_PORT", "8501")),
    }
    (RESOURCES / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    subprocess.run(
        [
            "codesign",
            "--force",
            "--deep",
            "--sign",
            "-",
            str(APP_DIR),
        ],
        check=True,
    )

    print(APP_DIR)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
