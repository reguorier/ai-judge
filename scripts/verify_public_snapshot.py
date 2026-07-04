#!/usr/bin/env python3
"""Validate the public AI Judge showcase snapshot.

This script intentionally uses only the Python standard library so GitHub
Actions and local contributors can run it without installing the private
runtime.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_PATHS = [
    "README.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "product/landing.html",
    "docs/PUBLIC_PRIVATE_BOUNDARY.md",
    "docs/PUBLIC_EXPORT_MANIFEST.md",
    "docs/TRY_AI_JUDGE_IN_3_MINUTES.md",
    "docs/ARC_AGENT_TRACE_AUDIT.md",
    "docs/CLAIM_SPAN_ROADMAP.md",
    "docs/UNVERIFIABLE_IS_NOT_FALSE.md",
    "docs/GITHUB_CONVERSION_CHECKLIST.md",
    "assets/ai-judge-public-flow.svg",
    "assets/citation-audit-space-output.png",
    "citation-bench/citation-bench-100.jsonl",
    "citation-bench/citation-bench-hard-11.jsonl",
    "reports/citation-batch/index.html",
    "reports/citation-batch/manifest.json",
    ".github/ISSUE_TEMPLATE/benchmark_case.yml",
    ".github/ISSUE_TEMPLATE/boundary_case.yml",
    ".github/ISSUE_TEMPLATE/workflow_request.yml",
    ".github/PULL_REQUEST_TEMPLATE.md",
    ".github/workflows/public-snapshot.yml",
]

PRIVATE_PATHS = [
    "core",
    "bridges",
    "client",
    "tools",
    "harness",
    "desktop",
    "growth",
    "papers",
    "backups",
    "runtime",
    "artifacts",
]

EXPECTED_JSONL_COUNTS = {
    "citation-bench/citation-bench-100.jsonl": 100,
    "citation-bench/citation-bench-hard-11.jsonl": 13,
}

LOCAL_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)|(?:href|src)=[\"']([^\"']+)[\"']")
SECRET_RE = re.compile(
    r"(ghp_[A-Za-z0-9_]{20,}|gho_[A-Za-z0-9_]{20,}|sk-[A-Za-z0-9]{20,}|"
    r"AKIA[0-9A-Z]{16}|BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY)"
)


class CheckFailure(Exception):
    pass


def fail(message: str) -> None:
    raise CheckFailure(message)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def require_paths() -> None:
    for item in REQUIRED_PATHS:
        if not (ROOT / item).exists():
            fail(f"missing required public file: {item}")


def reject_private_paths() -> None:
    for item in PRIVATE_PATHS:
        if (ROOT / item).exists():
            fail(f"private/runtime path must not be in public snapshot: {item}")


def parse_jsonl(path: Path) -> int:
    count = 0
    required = {"id", "question", "answer", "expected_status"}
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        count += 1
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"{rel(path)}:{number} is not valid JSON: {exc}")
        missing = required - set(data)
        if missing:
            fail(f"{rel(path)}:{number} missing keys: {sorted(missing)}")
    return count


def validate_benchmarks() -> None:
    for item, expected_count in EXPECTED_JSONL_COUNTS.items():
        count = parse_jsonl(ROOT / item)
        if count != expected_count:
            fail(f"{item} expected {expected_count} cases, found {count}")


def validate_report_manifest() -> None:
    manifest_path = ROOT / "reports/citation-batch/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results = manifest.get("results")
    if not isinstance(results, list) or not results:
        fail("reports/citation-batch/manifest.json has no results")
    if manifest.get("input_count") != len(results):
        fail("manifest input_count does not match results length")
    for result in results:
        for key in ("input", "html", "json", "overall_status"):
            if key not in result:
                fail(f"manifest result missing {key}: {result}")
        for artifact_key in ("input", "html", "json"):
            artifact = ROOT / result[artifact_key]
            if not artifact.exists():
                fail(f"manifest references missing {artifact_key}: {result[artifact_key]}")
        json.loads((ROOT / result["json"]).read_text(encoding="utf-8"))


def is_external_link(target: str) -> bool:
    parsed = urlparse(target)
    return parsed.scheme in {"http", "https", "mailto"}


def normalize_local_link(source: Path, target: str) -> Path | None:
    target = target.strip()
    if not target or target.startswith("#") or is_external_link(target):
        return None
    target = target.split("#", 1)[0]
    if not target:
        return None
    parsed = urlparse(target)
    if parsed.scheme:
        return None
    clean = unquote(parsed.path)
    return (source.parent / clean).resolve()


def validate_links() -> None:
    scanned = [
        ROOT / "README.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / "docs/TRY_AI_JUDGE_IN_3_MINUTES.md",
        ROOT / "docs/PUBLIC_EXPORT_MANIFEST.md",
        ROOT / "docs/PUBLIC_PRIVATE_BOUNDARY.md",
        ROOT / "product/landing.html",
    ]
    for source in scanned:
        text = source.read_text(encoding="utf-8")
        for match in LOCAL_LINK_RE.finditer(text):
            target = match.group(1) or match.group(2)
            local = normalize_local_link(source, target)
            if local is None:
                continue
            try:
                local.relative_to(ROOT)
            except ValueError:
                fail(f"{rel(source)} links outside repository: {target}")
            if not local.exists():
                fail(f"{rel(source)} has broken local link: {target}")


def scan_for_secrets() -> None:
    extensions = {".md", ".html", ".json", ".jsonl", ".yml", ".yaml", ".svg", ".py", ".txt"}
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file() or path.suffix not in extensions:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if SECRET_RE.search(text):
            fail(f"possible secret pattern in public file: {rel(path)}")


def main() -> int:
    checks = [
        require_paths,
        reject_private_paths,
        validate_benchmarks,
        validate_report_manifest,
        validate_links,
        scan_for_secrets,
    ]
    for check in checks:
        check()
    print("public snapshot verified")
    print("benchmarks: 100 citation cases, 13 hard claim-support cases")
    print("reports: citation batch manifest and artifacts linked")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailure as exc:
        print(f"public snapshot check failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
