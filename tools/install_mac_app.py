#!/usr/bin/env python3
"""Install AI Judge.app into the user's Applications folder with progress."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILT_APP = PROJECT_ROOT / "dist" / "mac" / "AI Judge.app"
RUNTIME_ROOT = Path.home() / "Library" / "Application Support" / "AI Judge" / "runtime"
LAUNCH_AGENT_LABEL = "local.ai-judge.desktop.server"
LAUNCH_AGENT = Path.home() / "Library" / "LaunchAgents" / f"{LAUNCH_AGENT_LABEL}.plist"

RUNTIME_ITEMS = [
    ".venv",
    "assets",
    "bridges",
    "cli",
    "core",
    "data",
    "product",
    "prompts",
    "runs",
    "schemas",
    "pyproject.toml",
]


def sync_runtime() -> None:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    for name in RUNTIME_ITEMS:
        source = PROJECT_ROOT / name
        target = RUNTIME_ROOT / name
        if not source.exists():
            continue
        if target.exists() or target.is_symlink():
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()
        if source.is_dir():
            shutil.copytree(source, target, symlinks=True)
        else:
            shutil.copy2(source, target)
    (RUNTIME_ROOT / "data").mkdir(parents=True, exist_ok=True)
    (RUNTIME_ROOT / "runs").mkdir(parents=True, exist_ok=True)


def stop_legacy_launch_agent() -> None:
    domain = f"gui/{os.getuid()}"
    subprocess.run(
        ["launchctl", "bootout", domain, LAUNCH_AGENT_LABEL],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if LAUNCH_AGENT.exists():
        LAUNCH_AGENT.unlink()


def start_local_service() -> None:
    if wait_for_health(timeout_seconds=1.0):
        return

    log_path = RUNTIME_ROOT / "data" / "desktop-server.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    python = next(
        candidate
        for candidate in [
            RUNTIME_ROOT / "python" / "bin" / "python3.12",
            RUNTIME_ROOT / "python" / "bin" / "python3",
            RUNTIME_ROOT / "python" / "bin" / "python",
            RUNTIME_ROOT / ".venv" / "bin" / "python",
        ]
        if candidate.exists()
    )
    server = RUNTIME_ROOT / "product" / "api_server.py"

    env = os.environ.copy()
    env.update(
        {
            "AI_JUDGE_APP_URL": "http://127.0.0.1:8501",
            "AI_JUDGE_DESKTOP_CLIENT": "1",
            "PYTHONUNBUFFERED": "1",
            "PYTHONPATH": str(RUNTIME_ROOT / ".venv" / "lib" / "python3.14" / "site-packages"),
            "PATH": f"{RUNTIME_ROOT / '.venv' / 'bin'}:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        }
    )
    env.pop("__PYVENV_LAUNCHER__", None)

    log_fh = log_path.open("ab")
    try:
        subprocess.Popen(
            [
                str(python),
                str(server),
                "--host",
                "127.0.0.1",
                "--port",
                "8501",
            ],
            cwd=str(RUNTIME_ROOT),
            env=env,
            stdout=log_fh,
            stderr=log_fh,
            start_new_session=True,
            close_fds=True,
        )
    finally:
        log_fh.close()


def service_command() -> str:
    python = next(
        (
            candidate
            for candidate in [
                RUNTIME_ROOT / "python" / "bin" / "python3.12",
                RUNTIME_ROOT / "python" / "bin" / "python3",
                RUNTIME_ROOT / "python" / "bin" / "python",
                RUNTIME_ROOT / ".venv" / "bin" / "python",
            ]
            if candidate.exists()
        ),
        RUNTIME_ROOT / ".venv" / "bin" / "python",
    )
    server = RUNTIME_ROOT / "product" / "api_server.py"
    return " ".join(
        [
            str(python),
            str(server),
            "--host",
            "127.0.0.1",
            "--port",
            "8501",
        ]
    )


def wait_for_health(timeout_seconds: float = 12.0) -> bool:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8501/api/health", timeout=1.0) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.35)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the local AI Judge macOS app.")
    parser.add_argument(
        "--target",
        default=str(Path.home() / "Applications"),
        help="Install folder. Defaults to ~/Applications so admin permission is not required.",
    )
    parser.add_argument("--no-open", action="store_true", help="Do not open AI Judge after installing.")
    args = parser.parse_args()

    target_dir = Path(args.target).expanduser()
    target_app = target_dir / "AI Judge.app"

    print("[1/6] Syncing runtime")
    sync_runtime()

    print("[2/6] Building AI Judge.app")
    env = os.environ.copy()
    env["AI_JUDGE_DESKTOP_PROJECT_ROOT"] = str(RUNTIME_ROOT)
    subprocess.run([sys.executable, str(PROJECT_ROOT / "tools" / "build_mac_app.py")], check=True, env=env)

    print(f"[3/6] Installing to {target_app}")
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_app.exists():
        if target_app.name != "AI Judge.app":
            raise RuntimeError(f"Refusing to replace unexpected path: {target_app}")
        shutil.rmtree(target_app)
    shutil.copytree(BUILT_APP, target_app, symlinks=True)

    print("[4/6] Validating installed app")
    subprocess.run(["plutil", "-lint", str(target_app / "Contents" / "Info.plist")], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(target_app)], check=True)

    print("[5/6] Starting local service")
    stop_legacy_launch_agent()
    start_local_service()
    if not wait_for_health():
        raise RuntimeError(
            "AI Judge local service did not become ready.\n"
            f"Command: {service_command()}\n"
            f"Log: {RUNTIME_ROOT / 'data' / 'desktop-server.log'}"
        )

    if args.no_open:
        print("[6/6] Installed")
    else:
        print("[6/6] Opening AI Judge")
        subprocess.run(["open", "-n", str(target_app)], check=True)

    print(f"Installed: {target_app}")
    print(f"Runtime: {RUNTIME_ROOT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
