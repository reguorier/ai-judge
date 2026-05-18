#!/usr/bin/env python3
"""Validate the Eval4SD 2026 submission packet.

This is a lightweight pre-submit gate for the anonymous paper draft. It checks
that the paper stays anonymous, that citation keys exist in the bibliography,
and that benchmark numbers in the text match the current deterministic bench.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER_DIR = ROOT / "papers" / "eval4sd2026"
MAIN_TEX = PAPER_DIR / "main.tex"
BIB_FILE = PAPER_DIR / "references.bib"
ACL_STYLE = PAPER_DIR / "acl.sty"
ACL_BST = PAPER_DIR / "acl_natbib.bst"
PDF_FILE = PAPER_DIR / "main.pdf"
OPENREVIEW_JSON = PAPER_DIR / "openreview_submission.json"

FORBIDDEN_REVIEW_TERMS = (
    "reguorier",
    "github.com",
    "huggingface",
    "hugging face",
    "ai judge",
    "ai-judge",
)


def run_bench(args: list[str]) -> dict[str, object]:
    result = subprocess.run(
        [sys.executable, *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    if result.returncode != 0:
        raise SystemExit(result.stdout)
    return json.loads(result.stdout)


def citation_keys(tex: str) -> set[str]:
    keys: set[str] = set()
    for match in re.findall(r"\\cite\{([^}]+)\}", tex):
        keys.update(key.strip() for key in match.split(",") if key.strip())
    return keys


def bib_keys(bib: str) -> set[str]:
    return set(re.findall(r"@\w+\{([^,]+),", bib))


def require_contains(errors: list[str], text: str, needle: str, description: str) -> None:
    if needle not in text:
        errors.append(f"Missing {description}: {needle}")


def latex_texttt(value: str) -> str:
    return "\\texttt{" + value.replace("_", "\\_") + "}"


def normalized(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip().lower()


def main() -> int:
    tex = MAIN_TEX.read_text(encoding="utf-8")
    bib = BIB_FILE.read_text(encoding="utf-8")
    acl_style = ACL_STYLE.read_text(encoding="utf-8")
    acl_bst = ACL_BST.read_text(encoding="utf-8")
    openreview = json.loads(OPENREVIEW_JSON.read_text(encoding="utf-8"))
    errors: list[str] = []

    lowered = tex.lower()
    for term in FORBIDDEN_REVIEW_TERMS:
        if term in lowered:
            errors.append(f"Review-anonymity leak in main.tex: {term}")

    missing_keys = citation_keys(tex) - bib_keys(bib)
    if missing_keys:
        errors.append(f"Missing bibliography keys: {', '.join(sorted(missing_keys))}")

    require_contains(errors, tex, "\\usepackage[review]{acl}", "ACL review package")
    if "\\usepackage[margin=1in]{geometry}" in tex:
        errors.append("main.tex still overrides ACL geometry.")
    require_contains(errors, acl_style, "https://github.com/acl-org/acl-style-files/", "official ACL style source marker")
    require_contains(errors, acl_style, "\\RequirePackage{natbib}", "ACL natbib loading")
    require_contains(errors, acl_bst, "ENTRY", "ACL bibliography style body")
    if not PDF_FILE.exists() or PDF_FILE.stat().st_size <= 0:
        errors.append(f"Missing non-empty PDF: {PDF_FILE.relative_to(ROOT)}")

    if openreview.get("title") not in tex:
        errors.append("OpenReview title does not match main.tex title.")
    if openreview.get("pdf") != str(PDF_FILE.relative_to(ROOT)):
        errors.append("OpenReview JSON PDF path does not point to papers/eval4sd2026/main.pdf.")
    if openreview.get("submission_type") != "Short / Position Paper":
        errors.append("OpenReview JSON submission_type must be Short / Position Paper.")
    if openreview.get("dual_submission_statement") != "This work is not under review elsewhere.":
        errors.append("OpenReview JSON dual-submission statement is missing or changed.")
    if len(openreview.get("keywords", [])) < 5:
        errors.append("OpenReview JSON should include at least five keywords.")
    if "source-heavy outputs" not in normalized(openreview.get("abstract", "")):
        errors.append("OpenReview JSON abstract is missing the paper abstract.")
    openreview_identity_surface = normalized(json.dumps(openreview, ensure_ascii=False))
    for term in FORBIDDEN_REVIEW_TERMS:
        if term in openreview_identity_surface:
            errors.append(f"Review-anonymity leak in OpenReview packet: {term}")

    full = run_bench(["tools/run_citation_bench.py", "--fail-under", "0.95"])
    hard = run_bench(
        [
            "tools/run_citation_bench.py",
            "--bench",
            "citation-bench/citation-bench-hard-11.jsonl",
            "--fail-under",
            "0.95",
        ]
    )

    require_contains(
        errors,
        tex,
        f"\\texttt{{bench-100}} & {full['total']} & {full['passed']} & {full['failed']} & {full['accuracy']:.2f}",
        "full benchmark table row",
    )
    require_contains(
        errors,
        tex,
        f"\\texttt{{hard-11}} & {hard['total']} & {hard['passed']} & {hard['failed']} & {hard['accuracy']:.2f}",
        "hard benchmark table row",
    )

    hard_categories = hard["by_category"]
    for label, counts in sorted(hard_categories.items()):
        require_contains(
            errors,
            tex,
            f"{latex_texttt(label)} & {counts['passed']} & {counts['total']}",
            f"hard benchmark category row for {label}",
        )

    for token in (
        "\\texttt{verified}",
        "\\texttt{relevant}",
        "\\texttt{contradicted}",
        "\\texttt{overclaimed\\_causation}",
        "\\texttt{overclaimed\\_absolute}",
        "\\texttt{overclaimed\\_quantified\\_effect}",
    ):
        require_contains(errors, tex, token, "overclaimed-causation support row token")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(
        json.dumps(
            {
                "schema": "eval4sd_packet_check.v1",
                "paper": str(MAIN_TEX.relative_to(ROOT)),
                "pdf": str(PDF_FILE.relative_to(ROOT)),
                "openreview_packet": str(OPENREVIEW_JSON.relative_to(ROOT)),
                "anonymous": True,
                "citation_keys": sorted(citation_keys(tex)),
                "benchmarks": {
                    "full": {
                        "total": full["total"],
                        "passed": full["passed"],
                        "failed": full["failed"],
                        "accuracy": full["accuracy"],
                    },
                    "hard": {
                        "total": hard["total"],
                        "passed": hard["passed"],
                        "failed": hard["failed"],
                        "accuracy": hard["accuracy"],
                    },
                },
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
