#!/usr/bin/env python3
"""Build a shareable macOS installer for AI Judge."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.6.1"
ARCH = "arm64"
APP_NAME = "AI Judge"
SHARED_ROOT = Path("/Users/Shared/AI Judge")
RUNTIME_INSTALL_ROOT = SHARED_ROOT / "runtime"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = DIST_DIR / "installer-build"
INSTALLERS_DIR = DIST_DIR / "installers"
PAYLOAD_ROOT = BUILD_DIR / "payload"
SCRIPTS_DIR = BUILD_DIR / "scripts"
DMG_ROOT = BUILD_DIR / "dmg-root"
PKG_PATH = INSTALLERS_DIR / f"AI-Judge-v{VERSION}-macOS-{ARCH}.pkg"
DMG_PATH = INSTALLERS_DIR / f"AI-Judge-v{VERSION}-macOS-{ARCH}.dmg"

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
    env["AI_JUDGE_DESKTOP_PROJECT_ROOT"] = str(RUNTIME_INSTALL_ROOT)
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
    if source.exists():
        data = json.loads(source.read_text(encoding="utf-8"))
    else:
        data = {}
    data["profile_root"] = str(RUNTIME_INSTALL_ROOT / "data" / "web_profiles")
    data.setdefault("automation_driver", "chrome_apple_events")
    data.setdefault("auto_open_missing_tabs", True)
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
    data_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "web_profiles").mkdir(parents=True, exist_ok=True)
    (data_dir / "desktop-server.log").write_text("", encoding="utf-8")
    (data_dir / "web_seats.json").write_text(json.dumps(sanitized_web_seats(), ensure_ascii=False, indent=2), encoding="utf-8")


def write_scripts() -> None:
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    preinstall = """#!/bin/zsh
set -euo pipefail

osascript -e 'tell application id "local.ai-judge.desktop" to quit' >/dev/null 2>&1 || true
pkill -f '/Users/Shared/AI Judge/runtime/product/api_server.py' >/dev/null 2>&1 || true
exit 0
"""
    postinstall = """#!/bin/zsh
set -euo pipefail

RUNTIME="/Users/Shared/AI Judge/runtime"
SHARED="/Users/Shared/AI Judge"

mkdir -p "$RUNTIME/data" "$RUNTIME/runs" "$RUNTIME/data/web_profiles"

CONSOLE_USER="$(stat -f %Su /dev/console 2>/dev/null || true)"
if [[ -n "$CONSOLE_USER" && "$CONSOLE_USER" != "root" ]]; then
  chown -R "$CONSOLE_USER":staff "$SHARED" >/dev/null 2>&1 || true
fi

chmod -R u+rwX,g+rwX,o+rX "$SHARED" >/dev/null 2>&1 || true
chmod -R a+rwX "$RUNTIME/data" "$RUNTIME/runs" >/dev/null 2>&1 || true

exit 0
"""
    for name, content in {"preinstall": preinstall, "postinstall": postinstall}.items():
        path = SCRIPTS_DIR / name
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)


def write_readme(target: Path) -> None:
    text = f"""AI Judge v{VERSION} for macOS arm64

安装：
1. 双击 AI-Judge-v{VERSION}-macOS-{ARCH}.pkg
2. 安装完成后从 /Applications 打开 AI Judge

说明：
- 应用安装到 /Applications/AI Judge.app
- 本地运行时安装到 /Users/Shared/AI Judge/runtime
- 不包含打包者本机的 tasks.db、runs 历史记录或网页登录数据
- 网页席位仍需要同事自己的 Chrome/网页账号登录状态
- 首次打开如 macOS 提示未知开发者，请右键 AI Judge 选择打开
"""
    target.write_text(text, encoding="utf-8")


def build_pkg() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    INSTALLERS_DIR.mkdir(parents=True, exist_ok=True)
    payload_runtime = PAYLOAD_ROOT / str(RUNTIME_INSTALL_ROOT).lstrip("/")
    payload_apps = PAYLOAD_ROOT / "Applications"
    payload_apps.mkdir(parents=True, exist_ok=True)

    app = build_app()
    copytree_clean(app, payload_apps / f"{APP_NAME}.app")
    prepare_runtime(payload_runtime)
    write_scripts()

    if PKG_PATH.exists():
        PKG_PATH.unlink()
    run(["xattr", "-cr", str(PAYLOAD_ROOT)])
    pkg_env = os.environ.copy()
    pkg_env["COPYFILE_DISABLE"] = "1"
    run([
        "pkgbuild",
        "--root",
        str(PAYLOAD_ROOT),
        "--filter",
        r"(^|/)\._.*",
        "--filter",
        r"(^|/)\.DS_Store$",
        "--filter",
        r"(^|/)CVS(/|$)",
        "--filter",
        r"(^|/)\.svn(/|$)",
        "--identifier",
        "local.ai-judge.desktop.pkg",
        "--version",
        VERSION,
        "--scripts",
        str(SCRIPTS_DIR),
        "--install-location",
        "/",
        str(PKG_PATH),
    ], env=pkg_env)


def build_dmg() -> None:
    if DMG_ROOT.exists():
        shutil.rmtree(DMG_ROOT)
    DMG_ROOT.mkdir(parents=True, exist_ok=True)
    shutil.copy(PKG_PATH, DMG_ROOT / PKG_PATH.name)
    write_readme(DMG_ROOT / "README-安装说明.txt")
    if DMG_PATH.exists():
        DMG_PATH.unlink()
    dmg_env = os.environ.copy()
    dmg_env["COPYFILE_DISABLE"] = "1"
    run([
        "hdiutil",
        "create",
        "-volname",
        f"AI Judge v{VERSION}",
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
    parser = argparse.ArgumentParser(description="Build a shareable macOS AI Judge installer.")
    parser.add_argument("--no-dmg", action="store_true", help="Only build the .pkg file.")
    args = parser.parse_args()

    build_pkg()
    if not args.no_dmg:
        build_dmg()

    print(f"PKG: {PKG_PATH}")
    if not args.no_dmg:
        print(f"DMG: {DMG_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
