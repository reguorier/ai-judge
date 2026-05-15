#!/usr/bin/env python3
"""AI Judge Evidence Trace — COUNCIL-004 Phase 1.

Lightweight cross-model citation tracing without Zep Cloud dependency.
Extracts reference patterns from claim text and detects shared contamination sources.

Three levels:
  L1: Explicit citation (URL, paper title, dataset name) — directly traceable
  L2: Implied citation ("according to X report") — marked for human review
  L3: No citation — pure training-data-based reasoning
"""

from __future__ import annotations

import re
from typing import Any


# ── L1: Explicit Citation Detection ──

URL_PATTERN = re.compile(r'https?://[^\s<>"]+|www\.[^\s<>"]+')
DOI_PATTERN = re.compile(r'\b10\.\d{4,}/[^\s]+\b')
ARXIV_PATTERN = re.compile(r'ar[xX]iv:\d{4}\.\d{4,}(v\d+)?')
PAPER_PATTERN = re.compile(
    r'("[^"]{10,80}"\s*(?:\(|,).*?(?:20\d{2}|Nature|Science|Cell|NEJM|The Lancet|JAMA))|'
    r'((?:Nature|Science|Cell|NEJM|The Lancet|JAMA|arXiv)[^,.]*)'
)


def extract_explicit_refs(text: str) -> list[dict[str, str]]:
    """Extract L1 explicit citations from claim text."""
    refs = []
    for m in URL_PATTERN.finditer(text):
        refs.append({"type": "url", "value": m.group()})
    for m in DOI_PATTERN.finditer(text):
        refs.append({"type": "doi", "value": m.group()})
    for m in ARXIV_PATTERN.finditer(text):
        refs.append({"type": "arxiv", "value": m.group()})
    for m in PAPER_PATTERN.finditer(text):
        refs.append({"type": "paper", "value": m.group().strip()})
    return refs


# ── L2: Implied Citation Detection ──

IMPLIED_PATTERNS = [
    re.compile(r'根据(.{2,20}?)(?:报告|研究|数据|统计|调查)'),
    re.compile(r'according\s+to\s+(.{2,30}?)(?:\s+report|\s+study|\s+research|\s+data)', re.IGNORECASE),
    re.compile(r'(.{2,20}?)(?:的)?(?:数据显示|研究表明|报告指出)'),
]


def _source_key(source: str) -> str:
    """Normalize source labels enough to catch shared citations across seats."""
    return re.sub(r"\s+", " ", source.strip().strip(".,;:，。；：")).lower()


def extract_implied_refs(text: str) -> list[dict[str, str]]:
    """Extract L2 implied citations from claim text."""
    refs = []
    for pattern in IMPLIED_PATTERNS:
        for m in pattern.finditer(text):
            source = m.group(1).strip()
            if len(source) > 2 and source not in ("相关", "有关", "一些", "部分"):
                refs.append({"type": "implied", "source": source})
    return refs


# ── L3: No-citation detection ──

def has_no_citations(text: str) -> bool:
    """Check if a claim has zero citations (L3)."""
    return not extract_explicit_refs(text) and not extract_implied_refs(text)


# ── Cross-Model Contamination Detection ──

def detect_shared_sources(
    claims: dict[str, list[str]],  # {seat_name: [claim_texts]}
) -> dict[str, Any]:
    """Detect if multiple seats share the same citation sources.

    Returns a contamination report showing which sources are shared by >2 seats.
    """
    source_seats: dict[str, list[str]] = {}  # {source_value: [seat_names]}

    for seat, claim_texts in claims.items():
        for text in claim_texts:
            for ref in extract_explicit_refs(text):
                key = ref["value"]
                if key not in source_seats:
                    source_seats[key] = []
                if seat not in source_seats[key]:
                    source_seats[key].append(seat)
            for ref in extract_implied_refs(text):
                key = _source_key(ref["source"])
                if key not in source_seats:
                    source_seats[key] = []
                if seat not in source_seats[key]:
                    source_seats[key].append(seat)

    # Find contaminated sources (shared by 3+ seats)
    contaminated = []
    for source, seats in source_seats.items():
        if len(seats) >= 3:
            contaminated.append({
                "source": source,
                "shared_by": sorted(seats),
                "seat_count": len(seats),
                "risk_level": "critical" if len(seats) >= 5 else "warning",
                "message": (
                    f"⚠️ {len(seats)} seats ({', '.join(seats[:3])}...)"
                    f" share this citation source. Consensus may be pseudo-independent."
                ),
            })

    contaminated.sort(key=lambda x: x["seat_count"], reverse=True)

    return {
        "total_shared_sources": len(source_seats),
        "contaminated_sources": len(contaminated),
        "contamination_details": contaminated[:10],
        "verdict_advisory": (
            f"Found {len(contaminated)} potentially contaminated sources "
            f"(shared by 3+ seats). These may indicate pseudo-consensus."
        ),
    }


# ── Trace Report for a Single Claim ──

def trace_claim(claim_text: str, claim_id: str = "") -> dict[str, Any]:
    """Generate a trace report for a single claim."""
    explicit = extract_explicit_refs(claim_text)
    implied = extract_implied_refs(claim_text)
    no_cite = has_no_citations(claim_text)

    level = "L1"
    if not explicit and not implied:
        level = "L3"
    elif not explicit:
        level = "L2"

    return {
        "claim_id": claim_id,
        "trace_level": level,
        "explicit_refs": len(explicit),
        "implied_refs": len(implied),
        "explicit_details": explicit[:5],
        "implied_details": implied[:5],
        "advisory": (
            "No citation support found. Claim reliability cannot be verified."
            if no_cite else
            "Implied citations detected. Consider human review for source verification."
            if level == "L2" else
            "Explicit citations found. Traceable."
        ),
    }
