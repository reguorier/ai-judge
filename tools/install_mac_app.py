#!/usr/bin/env python3
"""Install AI Judge.app into the user's Applications folder with progress."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILT_APP = PROJECT_ROOT / "dist" / "mac" / "AI Judge.app"


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

    print("[1/4] Building AI Judge.app")
    subprocess.run([sys.executable, str(PROJECT_ROOT / "tools" / "build_mac_app.py")], check=True)

    print(f"[2/4] Installing to {target_app}")
    target_dir.mkdir(parents=True, exist_ok=True)
    if target_app.exists():
        if target_app.name != "AI Judge.app":
            raise RuntimeError(f"Refusing to replace unexpected path: {target_app}")
        shutil.rmtree(target_app)
    shutil.copytree(BUILT_APP, target_app, symlinks=True)

    print("[3/4] Validating installed app")
    subprocess.run(["plutil", "-lint", str(target_app / "Contents" / "Info.plist")], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", "--verbose=2", str(target_app)], check=True)

    if args.no_open:
        print("[4/4] Installed")
    else:
        print("[4/4] Opening AI Judge")
        subprocess.run(["open", "-n", str(target_app)], check=True)

    print(f"Installed: {target_app}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
