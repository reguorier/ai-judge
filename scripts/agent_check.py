#!/usr/bin/env python3
"""Check AI Judge project-level agent context infrastructure."""

from __future__ import annotations

from pathlib import Path
import json
import sys


ROOT = Path(__file__).resolve().parents[1]


def exists(relative_path: str) -> bool:
    return (ROOT / relative_path).exists()


def file_contains(relative_path: str, required_text: str) -> bool:
    path = ROOT / relative_path
    if not path.exists() or not path.is_file():
        return False
    return required_text in path.read_text(encoding="utf-8")


def package_has_scripts() -> bool:
    path = ROOT / "frontend" / "package.json"
    if not path.exists():
        return False
    data = json.loads(path.read_text(encoding="utf-8"))
    scripts = data.get("scripts", {})
    return all(name in scripts for name in ("dev", "build", "lint", "typecheck"))


def main() -> int:
    checks = [
        ("AGENTS.md exists", exists("AGENTS.md")),
        ("docs/agent_memory.md exists", exists("docs/agent_memory.md")),
        ("docs/runbook.md exists", exists("docs/runbook.md")),
        ("docs/page_context_ingest.md exists", exists("docs/page_context_ingest.md")),
        ("artifacts README or index exists", exists("artifacts/README.md") or exists("artifacts/index.md")),
        ("README.md references AGENTS.md", file_contains("README.md", "AGENTS.md")),
        ("README.md references docs/runbook.md", file_contains("README.md", "docs/runbook.md")),
        ("pyproject.toml exists", exists("pyproject.toml")),
        ("frontend/package.json has expected scripts", package_has_scripts()),
        ("tests/run_harness.py exists", exists("tests/run_harness.py")),
        ("citation audit workflow exists", exists(".github/workflows/citation-audit.yml")),
        ("publish workflow exists", exists(".github/workflows/publish.yml")),
    ]

    failed = False
    for label, ok in checks:
        status = "PASS" if ok else "FAIL"
        print(f"{status} {label}")
        failed = failed or not ok

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
