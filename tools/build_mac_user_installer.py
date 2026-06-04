#!/usr/bin/env python3
"""Build a user-space macOS DMG installer for AI Judge.

This avoids unsigned .pkg installer friction by installing to:
  - ~/Applications/AI Judge.app
  - ~/Library/Application Support/AI Judge/runtime
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.8.0"
ARCH = "arm64"
MIN_MACOS = "13.0"
APP_NAME = "AI Judge"
APP_SUPPORT_RUNTIME = "~/Library/Application Support/AI Judge/runtime"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = DIST_DIR / "user-installer-build"
DMG_ROOT = BUILD_DIR / "dmg-root"
INSTALLERS_DIR = DIST_DIR / "installers"
DMG_PATH = INSTALLERS_DIR / f"AI-Judge-v{VERSION}-macOS-{ARCH}-user-install.dmg"

RUNTIME_DIRS = ["assets", "bridges", "cli", "core", "product", "prompts", "schemas"]
RUNTIME_FILES = ["pyproject.toml", "README.md", "LICENSE"]
PYTHON_DEPS = ["flask", "flask-cors", "requests", "httpx", "pydantic", "playwright"]


def run(args: list[str], **kwargs: object) -> None:
    subprocess.run(args, check=True, **kwargs)


def copytree_clean(source: Path, target: Path) -> None:
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "._*", ".pytest_cache", ".ruff_cache", "*.tar.gz")
    shutil.copytree(source, target, ignore=ignore, symlinks=True, copy_function=shutil.copy)


def python_source() -> Path:
    configured = os.environ.get("AI_JUDGE_PACKAGER_PYTHON_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.home() / ".local/share/uv/python/cpython-3.12-macos-aarch64-none").resolve()


def build_app() -> Path:
    env = os.environ.copy()
    env["AI_JUDGE_DESKTOP_PROJECT_ROOT"] = "$APP_SUPPORT/runtime"
    env["AI_JUDGE_DESKTOP_ARCH"] = ARCH
    env["AI_JUDGE_MACOS_DEPLOYMENT_TARGET"] = MIN_MACOS
    run([sys.executable, str(PROJECT_ROOT / "tools" / "build_mac_app.py")], env=env)
    return PROJECT_ROOT / "dist" / "mac" / f"{APP_NAME}.app"


def prepare_python(target: Path) -> None:
    source = python_source()
    if not (source / "bin" / "python3.12").exists():
        raise RuntimeError(
            f"Python 3.12 runtime not found at {source}. "
            "Install one with `uv python install 3.12` or set AI_JUDGE_PACKAGER_PYTHON_ROOT."
        )
    copytree_clean(source, target)
    python = target / "bin" / "python3.12"
    probe = "import flask, flask_cors, requests, httpx, pydantic, playwright"
    result = subprocess.run([str(python), "-c", probe], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode == 0:
        return
    run([
        str(python),
        "-m",
        "pip",
        "install",
        "--break-system-packages",
        "--upgrade",
        "--no-cache-dir",
        *PYTHON_DEPS,
    ])


def sanitized_web_seats() -> dict[str, object]:
    source = PROJECT_ROOT / "data" / "web_seats.json"
    data = json.loads(source.read_text(encoding="utf-8")) if source.exists() else {}
    data["profile_root"] = f"{APP_SUPPORT_RUNTIME}/data/web_profiles"
    data["chrome_cdp_profile_dir"] = f"{APP_SUPPORT_RUNTIME}/data/chrome-profile"
    data["chrome_cdp_state_path"] = f"{APP_SUPPORT_RUNTIME}/data/chrome_cdp_bridge_state.json"
    data["chrome_profile_marker_path"] = f"{APP_SUPPORT_RUNTIME}/data/chrome-profile/AI_JUDGE_DEDICATED_PROFILE.txt"
    data["login_state_path"] = f"{APP_SUPPORT_RUNTIME}/data/seat_login_state.json"
    data.setdefault("automation_driver", "chrome_apple_events")
    data.setdefault("auto_open_missing_tabs", True)
    data.setdefault("chrome_launch_strategy", "open_app")
    data.setdefault("strict_chrome_profile_guard", True)
    data.setdefault("auto_terminate_wrong_cdp_profile", True)
    data.setdefault("chrome_profile_marker_required", True)
    return data


def prepare_runtime(runtime_root: Path) -> None:
    runtime_root.mkdir(parents=True, exist_ok=True)
    prepare_python(runtime_root / "python")

    for dirname in RUNTIME_DIRS:
        copytree_clean(PROJECT_ROOT / dirname, runtime_root / dirname)
    for filename in RUNTIME_FILES:
        source = PROJECT_ROOT / filename
        if source.exists():
            shutil.copy(source, runtime_root / filename)

    data_dir = runtime_root / "data"
    runs_dir = runtime_root / "runs"
    chrome_profile_dir = data_dir / "chrome-profile"
    data_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "web_profiles").mkdir(parents=True, exist_ok=True)
    chrome_profile_dir.mkdir(parents=True, exist_ok=True)
    (chrome_profile_dir / "AI_JUDGE_DEDICATED_PROFILE.txt").write_text(
        "AI Judge bridge dedicated Chrome profile\n",
        encoding="utf-8",
    )
    (data_dir / "desktop-server.log").write_text("", encoding="utf-8")
    (data_dir / "web_seats.json").write_text(json.dumps(sanitized_web_seats(), ensure_ascii=False, indent=2), encoding="utf-8")


def write_installer_command(target: Path) -> None:
    content = f"""#!/bin/zsh
set -euo pipefail

VERSION="{VERSION}"
ARCH="{ARCH}"
MIN_MACOS="{MIN_MACOS}"
SCRIPT_DIR="${{0:A:h}}"
APP_SRC="$SCRIPT_DIR/{APP_NAME}.app"
RUNTIME_SRC="$SCRIPT_DIR/runtime"
APP_DEST="$HOME/Applications/{APP_NAME}.app"
SUPPORT_DIR="$HOME/Library/Application Support/{APP_NAME}"
RUNTIME_DEST="$SUPPORT_DIR/runtime"

echo "AI Judge v$VERSION user installer"
echo

if [[ "$(uname -m)" != "$ARCH" ]]; then
  osascript -e 'display dialog "AI Judge v{VERSION} 这个安装包只支持 Apple Silicon Mac（arm64）。Intel Mac 需要单独的安装包。" buttons {{"OK"}} default button "OK"' >/dev/null 2>&1 || true
  echo "This installer requires Apple Silicon Mac (arm64)."
  exit 112
fi

autoload -Uz is-at-least
OS_VERSION="$(sw_vers -productVersion)"
if ! is-at-least "$MIN_MACOS" "$OS_VERSION"; then
  osascript -e 'display dialog "AI Judge v{VERSION} 需要 macOS {MIN_MACOS} 或更高版本。当前系统是 '"$OS_VERSION"'。" buttons {{"OK"}} default button "OK"' >/dev/null 2>&1 || true
  echo "This installer requires macOS $MIN_MACOS or later. Current macOS: $OS_VERSION."
  exit 112
fi

if [[ ! -d "$APP_SRC" ]]; then
  echo "Missing $APP_SRC"
  exit 1
fi
if [[ ! -d "$RUNTIME_SRC" ]]; then
  echo "Missing $RUNTIME_SRC"
  exit 1
fi

osascript -e 'tell application id "local.ai-judge.desktop" to quit' >/dev/null 2>&1 || true
pkill -f "$RUNTIME_DEST/product/api_server.py" >/dev/null 2>&1 || true

mkdir -p "$HOME/Applications" "$SUPPORT_DIR"
if [[ -d "$APP_DEST" ]]; then
  rm -rf "$APP_DEST"
fi
/usr/bin/ditto "$APP_SRC" "$APP_DEST"

mkdir -p "$RUNTIME_DEST"
/usr/bin/ditto "$RUNTIME_SRC" "$RUNTIME_DEST"
mkdir -p "$RUNTIME_DEST/data" "$RUNTIME_DEST/runs" "$RUNTIME_DEST/data/web_profiles" "$RUNTIME_DEST/data/chrome-profile"
printf "AI Judge bridge dedicated Chrome profile\\n" > "$RUNTIME_DEST/data/chrome-profile/AI_JUDGE_DEDICATED_PROFILE.txt"

chmod -R u+rwX "$SUPPORT_DIR" "$APP_DEST" >/dev/null 2>&1 || true
xattr -dr com.apple.quarantine "$APP_DEST" "$SUPPORT_DIR" >/dev/null 2>&1 || true

echo
echo "Installed:"
echo "  $APP_DEST"
echo "  $RUNTIME_DEST"
echo
echo "Opening AI Judge..."
if [[ "${{AI_JUDGE_INSTALLER_SKIP_OPEN:-0}}" == "1" ]]; then
  echo "Skip opening AI Judge because AI_JUDGE_INSTALLER_SKIP_OPEN=1."
else
  /usr/bin/open "$APP_DEST" >/dev/null 2>&1 || true
fi
"""
    target.write_text(content, encoding="utf-8")
    target.chmod(0o755)


def write_readme(target: Path) -> None:
    text = f"""AI Judge v{VERSION} macOS arm64 user installer

安装方式：
1. 打开这个 DMG
2. 双击 Install-AI-Judge.command
3. 如果 macOS 阻止打开，请右键 Install-AI-Judge.command，选择“打开”

这个版本不使用 .pkg，因此不需要 Apple Installer 签名，也不需要管理员密码。

安装位置：
- App: ~/Applications/AI Judge.app
- Runtime: ~/Library/Application Support/AI Judge/runtime

要求：
- Apple Silicon Mac（arm64）
- macOS {MIN_MACOS} 或更高版本
"""
    target.write_text(text, encoding="utf-8")


def build_dmg() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    DMG_ROOT.mkdir(parents=True, exist_ok=True)
    INSTALLERS_DIR.mkdir(parents=True, exist_ok=True)

    app = build_app()
    copytree_clean(app, DMG_ROOT / f"{APP_NAME}.app")
    prepare_runtime(DMG_ROOT / "runtime")
    write_installer_command(DMG_ROOT / "Install-AI-Judge.command")
    write_readme(DMG_ROOT / "README-安装说明.txt")

    run(["xattr", "-cr", str(DMG_ROOT)])
    run(["codesign", "--force", "--deep", "--sign", "-", str(DMG_ROOT / f"{APP_NAME}.app")])

    if DMG_PATH.exists():
        DMG_PATH.unlink()
    dmg_env = os.environ.copy()
    dmg_env["COPYFILE_DISABLE"] = "1"
    run([
        "hdiutil",
        "create",
        "-volname",
        f"AI Judge v{VERSION} User Install",
        "-srcfolder",
        str(DMG_ROOT),
        "-ov",
        "-format",
        "UDZO",
        "-fs",
        "HFS+",
        str(DMG_PATH),
    ], env=dmg_env)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a user-space macOS AI Judge DMG installer.")
    parser.parse_args()
    build_dmg()
    print(f"DMG: {DMG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
