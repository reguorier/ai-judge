#!/usr/bin/env python3
"""Prepare or deploy the AI Judge Citation Audit Hugging Face Space.

Default mode clones/updates a local Space worktree, copies the tracked Space
files into it, and reports the diff. Use `--push` with `HF_TOKEN` set to deploy.
"""

from __future__ import annotations

import argparse
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPACE_SOURCE = ROOT / "spaces" / "citation-audit"
DEFAULT_REMOTE = "https://huggingface.co/spaces/reguorier/ai-judge-citation-audit"
DEFAULT_WORKTREE = Path("/private/tmp/ai-judge-hf-space-deploy")
SPACE_FILES = ("app.py", "README.md", "requirements.txt")


def run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(f"Command failed: {' '.join(cmd)}\n{result.stdout}")
    return result


def ensure_worktree(worktree: Path, remote: str) -> None:
    if (worktree / ".git").exists():
        run(["git", "fetch", "origin", "main"], cwd=worktree)
        run(["git", "checkout", "main"], cwd=worktree)
        run(["git", "pull", "--ff-only", "origin", "main"], cwd=worktree)
        return
    if worktree.exists() and any(worktree.iterdir()):
        raise SystemExit(f"Refusing to use non-empty non-git worktree: {worktree}")
    worktree.parent.mkdir(parents=True, exist_ok=True)
    run(["git", "clone", remote, str(worktree)])


def copy_space_files(worktree: Path) -> None:
    for filename in SPACE_FILES:
        source = SPACE_SOURCE / filename
        if not source.exists():
            raise SystemExit(f"Missing Space source file: {source}")
        shutil.copy2(source, worktree / filename)


def validate_space(worktree: Path) -> None:
    run([sys.executable, "-m", "py_compile", str(worktree / "app.py")])
    shutil.rmtree(worktree / "__pycache__", ignore_errors=True)
    requirements = (worktree / "requirements.txt").read_text(encoding="utf-8")
    if "git+https://github.com/reguorier/ai-judge.git@main" not in requirements:
        raise SystemExit("requirements.txt must depend on ai-judge@main for the latest claim-support logic.")
    readme = (worktree / "README.md").read_text(encoding="utf-8")
    for required in ("sdk:", "app_file: app.py", "claim-support"):
        if required not in readme:
            raise SystemExit(f"README.md is missing `{required}`.")


def changed(worktree: Path) -> bool:
    status = run(["git", "status", "--porcelain"], cwd=worktree).stdout.strip()
    return bool(status)


def show_status(worktree: Path) -> None:
    print(run(["git", "status", "--short"], cwd=worktree).stdout.strip() or "No Space changes.")
    if changed(worktree):
        print(run(["git", "diff", "--stat"], cwd=worktree).stdout.strip())


def askpass_script(token: str) -> Path:
    handle = tempfile.NamedTemporaryFile("w", delete=False, prefix="hf-askpass-", suffix=".sh")
    path = Path(handle.name)
    handle.write("#!/bin/sh\n")
    handle.write("case \"$1\" in\n")
    handle.write("  *Username*) echo hf_user ;;\n")
    handle.write(f"  *Password*) echo {sh_quote(token)} ;;\n")
    handle.write("  *) echo ;;\n")
    handle.write("esac\n")
    handle.close()
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def sh_quote(value: str) -> str:
    return "'" + value.replace("'", "'\"'\"'") + "'"


def commit_and_push(worktree: Path, message: str, token: str) -> None:
    if not changed(worktree):
        print("No Space changes to deploy.")
        return
    run(["git", "add", *SPACE_FILES], cwd=worktree)
    run(["git", "commit", "-m", message], cwd=worktree)
    script = askpass_script(token)
    env = {
        **os.environ,
        "GIT_ASKPASS": str(script),
        "GIT_TERMINAL_PROMPT": "0",
    }
    try:
        run(["git", "push", "origin", "main"], cwd=worktree, env=env)
    finally:
        script.unlink(missing_ok=True)
    print("Hugging Face Space deployed.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--remote", default=DEFAULT_REMOTE, help="Hugging Face Space git remote")
    parser.add_argument("--worktree", default=str(DEFAULT_WORKTREE), help="Local Space worktree path")
    parser.add_argument("--push", action="store_true", help="Commit and push to Hugging Face")
    parser.add_argument("--message", default="Add claim support demo switcher", help="Space commit message")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    worktree = Path(args.worktree).expanduser()
    ensure_worktree(worktree, args.remote)
    copy_space_files(worktree)
    validate_space(worktree)
    show_status(worktree)
    if args.push:
        token = os.environ.get("HF_TOKEN", "").strip()
        if not token:
            raise SystemExit("Set HF_TOKEN before using --push.")
        commit_and_push(worktree, args.message, token)
    else:
        print("Prepared only. Deploy with: HF_TOKEN=... python tools/deploy_hf_space.py --push")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
