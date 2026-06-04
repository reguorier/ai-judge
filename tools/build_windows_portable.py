#!/usr/bin/env python3
"""Build a Windows x64 portable installer zip for AI Judge."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VERSION = "3.8.0"
PYTHON_VERSION = "3.13.13"
PYTHON_TAG = "313"
ARCH = "x64"
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = DIST_DIR / "windows-portable-build"
CACHE_DIR = PROJECT_ROOT / ".cache" / "windows"
INSTALLERS_DIR = DIST_DIR / "installers"
PACKAGE_NAME = f"AI-Judge-v{VERSION}-Windows-{ARCH}"
PACKAGE_ROOT = BUILD_DIR / PACKAGE_NAME
RUNTIME_ROOT = PACKAGE_ROOT / "runtime"
PYTHON_EMBED_URL = f"https://www.python.org/ftp/python/{PYTHON_VERSION}/python-{PYTHON_VERSION}-embed-amd64.zip"
PYTHON_EMBED_ZIP = CACHE_DIR / f"python-{PYTHON_VERSION}-embed-amd64.zip"
WHEELHOUSE = BUILD_DIR / "wheelhouse"
ZIP_PATH = INSTALLERS_DIR / f"{PACKAGE_NAME}-portable.zip"

RUNTIME_DIRS = ["assets", "bridges", "cli", "core", "product", "prompts", "schemas"]
RUNTIME_FILES = ["pyproject.toml", "LICENSE"]
PYTHON_DEPS = ["flask", "flask-cors", "requests", "httpx", "pydantic", "playwright"]


def run(args: list[str], **kwargs: object) -> None:
    subprocess.run(args, check=True, **kwargs)


def copytree_clean(source: Path, target: Path) -> None:
    ignore = shutil.ignore_patterns(
        "__pycache__",
        "*.pyc",
        ".DS_Store",
        "._*",
        ".pytest_cache",
        ".ruff_cache",
        "*.tar.gz",
        "*.backup*",
        "*.bak.*",
        "*.bak-*",
    )
    shutil.copytree(source, target, ignore=ignore, symlinks=False, copy_function=shutil.copy)


def download(url: str, target: Path) -> None:
    if target.exists() and target.stat().st_size > 0:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_suffix(target.suffix + ".tmp")
    with urllib.request.urlopen(url, timeout=120) as response, temp.open("wb") as fh:
        shutil.copyfileobj(response, fh)
    temp.replace(target)


def prepare_python() -> None:
    python_dir = RUNTIME_ROOT / "python"
    python_dir.mkdir(parents=True, exist_ok=True)
    download(PYTHON_EMBED_URL, PYTHON_EMBED_ZIP)
    with zipfile.ZipFile(PYTHON_EMBED_ZIP) as zf:
        zf.extractall(python_dir)

    pth = python_dir / f"python{PYTHON_TAG}._pth"
    if pth.exists():
        lines = [
            f"python{PYTHON_TAG}.zip",
            ".",
            "Lib\\site-packages",
            "import site",
        ]
        pth.write_text("\n".join(lines) + "\n", encoding="utf-8")

    site_packages = python_dir / "Lib" / "site-packages"
    site_packages.mkdir(parents=True, exist_ok=True)
    download_windows_wheels()
    for wheel in sorted(WHEELHOUSE.glob("*.whl")):
        with zipfile.ZipFile(wheel) as zf:
            zf.extractall(site_packages)


def download_windows_wheels() -> None:
    WHEELHOUSE.mkdir(parents=True, exist_ok=True)
    run([
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--platform",
        "win_amd64",
        "--implementation",
        "cp",
        "--python-version",
        PYTHON_TAG,
        "--abi",
        f"cp{PYTHON_TAG}",
        "--dest",
        str(WHEELHOUSE),
        *PYTHON_DEPS,
    ])


def sanitized_web_seats() -> dict[str, object]:
    source = PROJECT_ROOT / "data" / "web_seats.json"
    data = json.loads(source.read_text(encoding="utf-8")) if source.exists() else {}
    data["automation_driver"] = "playwright"
    data["auto_open_missing_tabs"] = False
    data["auto_wake_cdp"] = False
    data["auto_wake_open_tabs"] = False
    data["strict_chrome_profile_guard"] = False
    data["chrome_profile_marker_required"] = False
    data["profile_root"] = "data/web_profiles"
    data["chrome_cdp_profile_dir"] = "data/chrome-profile"
    data["chrome_cdp_state_path"] = "data/chrome_cdp_bridge_state.json"
    data["login_state_path"] = "data/seat_login_state.json"
    seats = data.get("seats") or {}
    for seat_config in seats.values():
        if isinstance(seat_config, dict):
            seat_config["enabled"] = False
            seat_config["headless"] = True
    data["seats"] = seats
    return data


def prepare_runtime() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    prepare_python()
    for dirname in RUNTIME_DIRS:
        copytree_clean(PROJECT_ROOT / dirname, RUNTIME_ROOT / dirname)
    for filename in RUNTIME_FILES:
        source = PROJECT_ROOT / filename
        if source.exists():
            shutil.copy(source, RUNTIME_ROOT / filename)
    patch_windows_runtime_sources()

    data_dir = RUNTIME_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "web_profiles").mkdir(parents=True, exist_ok=True)
    (data_dir / "chrome-profile").mkdir(parents=True, exist_ok=True)
    (RUNTIME_ROOT / "runs").mkdir(parents=True, exist_ok=True)
    (data_dir / "desktop-server.log").write_text("", encoding="utf-8")
    (data_dir / "web_seats.json").write_text(json.dumps(sanitized_web_seats(), ensure_ascii=False, indent=2), encoding="utf-8")


def patch_windows_runtime_sources() -> None:
    bridge = RUNTIME_ROOT / "bridges" / "web_seat_bridge.py"
    if not bridge.exists():
        return
    text = bridge.read_text(encoding="utf-8")
    text = text.replace(
        'str(Path.home() / "Documents/Playground/.omx/ai-judge/chrome-profile")',
        'str(DATA_DIR / "chrome-profile")',
    )
    text = text.replace(
        'str(Path.home() / "Documents/Playground/.omx/ai-judge/chrome-profile/AI_JUDGE_DEDICATED_PROFILE.txt")',
        'str(DATA_DIR / "chrome-profile/AI_JUDGE_DEDICATED_PROFILE.txt")',
    )
    bridge.write_text(text, encoding="utf-8", newline="\n")


def write_scripts() -> None:
    (PACKAGE_ROOT / "Start-AI-Judge.cmd").write_text(start_script(), encoding="utf-8", newline="\r\n")
    (PACKAGE_ROOT / "Install-AI-Judge-Windows.cmd").write_text(install_script(), encoding="utf-8", newline="\r\n")
    (PACKAGE_ROOT / "Uninstall-AI-Judge-Windows.cmd").write_text(uninstall_script(), encoding="utf-8", newline="\r\n")
    (PACKAGE_ROOT / "README-Windows.txt").write_text(readme_text(), encoding="utf-8")


def start_script() -> str:
    return r"""@echo off
setlocal
set "APP_ROOT=%~dp0"
set "RUNTIME=%APP_ROOT%runtime"
set "PY=%RUNTIME%\python\python.exe"
set "SERVER=%RUNTIME%\product\api_server.py"
set "LOG=%RUNTIME%\data\desktop-server.log"

if not exist "%PY%" (
  echo Missing Python runtime: "%PY%"
  pause
  exit /b 1
)
if not exist "%SERVER%" (
  echo Missing AI Judge server: "%SERVER%"
  pause
  exit /b 1
)

set "PYTHONUTF8=1"
set "PYTHONUNBUFFERED=1"
set "AI_JUDGE_WINDOWS_CLIENT=1"

cd /d "%RUNTIME%"
echo AI Judge is starting at http://127.0.0.1:8501/
echo Close this window to stop AI Judge.
echo.
start "" "http://127.0.0.1:8501/"
"%PY%" "%SERVER%" --host 127.0.0.1 --port 8501
echo.
echo AI Judge stopped. Log: "%LOG%"
pause
"""


def install_script() -> str:
    return r"""@echo off
setlocal
set "SRC=%~dp0"
set "DEST=%LOCALAPPDATA%\AI Judge"

echo AI Judge Windows user installer
echo.
echo Source: "%SRC%"
echo Target: "%DEST%"
echo.

if not exist "%SRC%runtime\python\python.exe" (
  echo Please extract the zip first, then run this installer from the extracted folder.
  pause
  exit /b 1
)

if exist "%DEST%" (
  echo Updating existing installation...
) else (
  echo Creating installation folder...
)
mkdir "%DEST%" >nul 2>nul

robocopy "%SRC%" "%DEST%" /E /XD "__MACOSX" /XF "Install-AI-Judge-Windows.cmd" >nul
set "RC=%ERRORLEVEL%"
if %RC% GEQ 8 (
  echo Copy failed with robocopy exit code %RC%.
  pause
  exit /b %RC%
)

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$w=New-Object -ComObject WScript.Shell; " ^
  "$desktop=[Environment]::GetFolderPath('Desktop'); " ^
  "$s=$w.CreateShortcut((Join-Path $desktop 'AI Judge.lnk')); " ^
  "$s.TargetPath=(Join-Path $env:LOCALAPPDATA 'AI Judge\Start-AI-Judge.cmd'); " ^
  "$s.WorkingDirectory=(Join-Path $env:LOCALAPPDATA 'AI Judge'); " ^
  "$s.IconLocation='%SystemRoot%\System32\SHELL32.dll,220'; " ^
  "$s.Save();" >nul 2>nul

echo.
echo Installed to "%DEST%".
echo A desktop shortcut named AI Judge was created when Windows allowed it.
echo.
choice /M "Start AI Judge now"
if errorlevel 2 exit /b 0
call "%DEST%\Start-AI-Judge.cmd"
"""


def uninstall_script() -> str:
    return r"""@echo off
setlocal
set "DEST=%LOCALAPPDATA%\AI Judge"
echo This will remove "%DEST%".
choice /M "Continue"
if errorlevel 2 exit /b 0
if exist "%USERPROFILE%\Desktop\AI Judge.lnk" del "%USERPROFILE%\Desktop\AI Judge.lnk" >nul 2>nul
if exist "%DEST%" rmdir /S /Q "%DEST%"
echo AI Judge was removed from this Windows user account.
pause
"""


def readme_text() -> str:
    return f"""AI Judge v{VERSION} for Windows x64

安装方式：
1. 先解压整个 zip 文件，不要直接在压缩包里运行。
2. 双击 Install-AI-Judge-Windows.cmd。
3. 安装后会放到 %LOCALAPPDATA%\\AI Judge，并尽量创建桌面快捷方式。
4. 如果 Windows Defender SmartScreen 提示未知发布者，选择“更多信息” -> “仍要运行”。

免安装运行：
- 也可以在解压后的文件夹里直接双击 Start-AI-Judge.cmd。

运行方式：
- 启动脚本会打开 http://127.0.0.1:8501/
- 保持黑色命令行窗口打开；关闭窗口就会停止 AI Judge。

说明：
- 这是 Windows x64 浏览器客户端包，不是 macOS Swift 桌面壳。
- 不需要管理员权限。
- 内置 Python {PYTHON_VERSION} embeddable runtime 和 Flask/Playwright 等 Python 依赖。
- Web 模型席位默认关闭；同事可以先使用本地工作台，再按需配置自己的网页登录/浏览器桥。
"""


def make_zip() -> None:
    INSTALLERS_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for path in sorted(PACKAGE_ROOT.rglob("*")):
            if path.is_file():
                zf.write(path, path.relative_to(BUILD_DIR))


def build() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    PACKAGE_ROOT.mkdir(parents=True, exist_ok=True)
    prepare_runtime()
    write_scripts()
    make_zip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a Windows x64 portable installer zip for AI Judge.")
    parser.parse_args()
    build()
    print(f"ZIP: {ZIP_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
