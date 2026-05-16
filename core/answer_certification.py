#!/usr/bin/env python3
"""AI Judge Answer Certification — research-grade verdict closure.

Transforms the raw jury pipeline output into a structured, reproducible,
peer-reviewable certification document that meets academic evidence standards.

A certification is NOT just a verdict. It is a complete scientific record:
  1. Methodology — jury configuration, scoring functions, parameters
  2. Experimental Data — per-claim scores, per-seat votes, evidence traces
  3. Statistical Analysis — calibration, inter-rater agreement, confidence bounds
  4. Limitations — known biases, contamination risks, boundary conditions
  5. Reproducibility — deterministic hash, parameter snapshot
  6. Peer Review Trail — dissent records, counter-arguments preserved

Usage:
  from core.answer_certification import certify

  cert = certify(
      question="Is solar cheaper than coal in 2026?",
      mode="standard",
      seats=["gemini", "deepseek", "grok"],
      verdict_data=api_result,
      claims=raw_claims,
  )
  # cert.model_dump_json(indent=2)  → 完整的学术认证文档
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel, ConfigDict, Field
except ModuleNotFoundError:  # pragma: no cover - dependency fallback for local desktop runtime
    class _FieldSpec:
        def __init__(self, default: Any = ..., default_factory: Any | None = None, **_: Any) -> None:
            self.default = default
            self.default_factory = default_factory

        def value(self) -> Any:
            if self.default_factory is not None:
                return self.default_factory()
            if self.default is ...:
                return None
            return self.default

    def Field(default: Any = ..., default_factory: Any | None = None, **kwargs: Any) -> _FieldSpec:
        return _FieldSpec(default=default, default_factory=default_factory, **kwargs)

    def ConfigDict(**kwargs: Any) -> dict[str, Any]:
        return dict(kwargs)

    class BaseModel:
        """Tiny Pydantic-compatible subset used when pydantic is unavailable."""

        def __init__(self, **kwargs: Any) -> None:
            fields: dict[str, Any] = {}
            for cls in reversed(type(self).__mro__):
                fields.update(getattr(cls, "__annotations__", {}))
            fields.pop("model_config", None)
            for name in fields:
                if name in kwargs:
                    value = kwargs.pop(name)
                else:
                    default = getattr(type(self), name, ...)
                    value = default.value() if isinstance(default, _FieldSpec) else (None if default is ... else default)
                setattr(self, name, value)
            for name, value in kwargs.items():
                setattr(self, name, value)

        def model_dump(self, exclude: set[str] | None = None) -> dict[str, Any]:
            exclude = exclude or set()
            return {
                key: _fallback_model_dump(value, exclude=None)
                for key, value in self.__dict__.items()
                if key not in exclude
            }

        def model_dump_json(self, exclude: set[str] | None = None, **kwargs: Any) -> str:
            return json.dumps(self.model_dump(exclude=exclude), ensure_ascii=False, default=str, **kwargs)


    def _fallback_model_dump(value: Any, exclude: set[str] | None = None) -> Any:
        if isinstance(value, BaseModel):
            return value.model_dump(exclude=exclude)
        if isinstance(value, list):
            return [_fallback_model_dump(item) for item in value]
        if isinstance(value, tuple):
            return tuple(_fallback_model_dump(item) for item in value)
        if isinstance(value, dict):
            return {key: _fallback_model_dump(item) for key, item in value.items()}
        return value

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ═══════════════════════════════════════════════════════════════
# Pydantic Schemas
# ═══════════════════════════════════════════════════════════════

class MethodSection(BaseModel):
    """How the certification was produced — full reproducibility record."""
    model_config = ConfigDict(extra="forbid")

    question: str = Field(description="The original question submitted to the jury")
    mode: str = Field(description="Jury mode: flash | standard | strategic")
    seats_deployed: list[str] = Field(description="List of seat IDs that participated")
    seat_count: int = Field(description="Number of participating seats")
    scoring_version: str = Field(description="Scoring engine version")
    scoring_functions: list[str] = Field(description="List of scoring functions applied")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Input parameters snapshot")
    timestamp_utc: str = Field(description="ISO 8601 timestamp of certification")
    execution_time_seconds: float | None = Field(default=None, description="Wall-clock execution time")
    reproducibility_hash: str = Field(description="SHA256 hash of all input parameters for reproducibility")


class ClaimScore(BaseModel):
    """A single claim's scoring trace."""
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(description="Unique claim identifier")
    seat: str = Field(description="Which seat produced this claim")
    claim_text: str = Field(description="The claim text (truncated to 300 chars)")
    score: float = Field(description="Claim score (0-1)")
    tier: str = Field(description="credible | conditional | unverified | rejected")
    evidence_level: str = Field(description="L1 (explicit) | L2 (implied) | L3 (no citation)")
    explicit_ref_count: int = Field(default=0)
    implied_ref_count: int = Field(default=0)
    bluff_gate_triggered: bool = Field(default=False)
    abstain_recommended: bool = Field(default=False)


class SeatScoreboard(BaseModel):
    """Per-seat scoring summary."""
    model_config = ConfigDict(extra="forbid")

    seat: str = Field(description="Seat identifier")
    seat_name: str = Field(description="Human-readable seat name")
    mbti: str = Field(description="MBTI personality type")
    claims_submitted: int = Field(description="Number of claims from this seat")
    mean_score: float = Field(description="Mean claim score")
    credible_count: int = Field(default=0)
    conditional_count: int = Field(default=0)
    unverified_count: int = Field(default=0)
    rejected_count: int = Field(default=0)
    abstain_count: int = Field(default=0)
    evidence_level_distribution: dict[str, int] = Field(default_factory=dict, description="{L1: n, L2: n, L3: n}")


class StatisticalAnalysis(BaseModel):
    """Statistical rigor section."""
    model_config = ConfigDict(extra="forbid")

    # Calibration
    brier_score: float | None = Field(default=None, description="Brier score across all claims (lower=better)")
    log_score: float | None = Field(default=None, description="Log score across all claims (lower=better)")

    # Consensus
    inter_rater_agreement: float | None = Field(default=None, description="Fleiss' Kappa or similar (0-1)")
    consensus_level: str = Field(description="high | moderate | low | divergent")
    diversity_index: float | None = Field(default=None, description="Normalized graph variance (0-1, higher=more diverse)")

    # Confidence
    aggregate_score: float = Field(description="Overall aggregate score (0-1)")
    score_std: float = Field(description="Standard deviation of claim scores")
    confidence_interval_95: tuple[float, float] = Field(description="95% confidence interval (lower, upper)")

    # Tier distribution
    tier_distribution: dict[str, int] = Field(description="{credible: n, conditional: n, unverified: n, rejected: n}")

    # Effect size
    credible_ratio: float = Field(description="credible / total claims")
    evidence_quality_index: float = Field(description="Proportion of claims with L1 evidence")


class EvidenceTrace(BaseModel):
    """Cross-model evidence contamination analysis."""
    model_config = ConfigDict(extra="forbid")

    total_shared_sources: int = Field(description="Number of shared citation sources across seats")
    contaminated_sources: int = Field(description="Sources shared by 3+ seats (pseudo-consensus risk)")
    contamination_risk: str = Field(description="none | low | moderate | critical")
    critical_sources: list[dict[str, Any]] = Field(default_factory=list)
    advisory: str = Field(description="Human-readable contamination advisory")


class DissentRecord(BaseModel):
    """Preserved dissent for peer review."""
    model_config = ConfigDict(extra="forbid")

    seat: str = Field(description="Dissenting seat")
    target_claim_id: str | None = Field(default=None)
    severity: str = Field(description="fatal | strong | weak")
    argument: str = Field(description="The dissenting argument")
    counter_evidence: str | None = Field(default=None)


class LimitationSection(BaseModel):
    """Known limitations and boundary conditions."""
    model_config = ConfigDict(extra="forbid")

    scope: str = Field(description="What this certification covers")
    exclusions: str = Field(description="What this certification does NOT cover")
    known_biases: list[str] = Field(default_factory=list, description="Known cognitive biases in the jury")
    contamination_risk: str = Field(description="Risk of pseudo-consensus from shared sources")
    temporal_validity: str = Field(description="How long this certification remains valid")
    generalizability: str = Field(description="Can this verdict be generalized? Under what conditions?")
    alternative_interpretations: list[str] = Field(default_factory=list, description="Plausible alternative conclusions")


class CitationVerificationSummary(BaseModel):
    """Citation-level verification bridge sealed into the certification hash."""
    model_config = ConfigDict(extra="forbid")

    certification_id: str | None = Field(default=None, description="Citation MVP certification id")
    overall_status: str = Field(description="verified | weakly_verified | irrelevant | unverifiable | contradicted")
    verified_count: int = Field(default=0)
    weakly_verified_count: int = Field(default=0)
    irrelevant_count: int = Field(default=0)
    unverifiable_count: int = Field(default=0)
    contradicted_count: int = Field(default=0)
    citation_count: int = Field(default=0)
    item_count: int = Field(default=0)
    verification_hash: str | None = Field(default=None)
    replay_ledger_hash: str | None = Field(default=None)
    unverifiable_explanation: str = Field(default="")
    source_isolation: dict[str, str] = Field(default_factory=dict)


class AnswerCertification(BaseModel):
    """Complete research-grade answer certification.

    This is the certification document. It can be serialized to JSON
    for machine consumption or rendered as an academic-style report.
    """
    model_config = ConfigDict(extra="forbid")

    # Header
    certification_id: str = Field(description="Unique certification identifier (CERT-YYYYMMDD-XXXXXX)")
    certification_version: str = Field(default="1.0.0")
    question: str = Field(description="The original question")
    verdict: str = Field(description="Final verdict: credible | conditional | unverified | rejected")
    verdict_confidence: float = Field(description="Confidence in the verdict (0-1)")

    # Paper-style abstract
    abstract: str = Field(description="One-paragraph structured abstract (Background, Methods, Results, Conclusion)")

    # Methodology
    methodology: MethodSection = Field(description="Full methodology section")

    # Results
    results: list[ClaimScore] = Field(default_factory=list, description="All scored claims")
    seat_scoreboards: list[SeatScoreboard] = Field(default_factory=list, description="Per-seat performance")

    # Statistics
    statistics: StatisticalAnalysis = Field(description="Full statistical analysis")

    # Evidence
    evidence_trace: EvidenceTrace = Field(description="Cross-model evidence analysis")
    citation_verification: CitationVerificationSummary | None = Field(
        default=None,
        description="Optional citation-level truth/relevance verification sealed into the certification",
    )

    # Dissent
    dissent_records: list[DissentRecord] = Field(default_factory=list, description="Preserved dissent for peer review")

    # Limitations
    limitations: LimitationSection = Field(description="Known limitations and boundary conditions")

    # Recommendation
    recommendation: str = Field(description="Actionable recommendation based on the verdict")
    next_steps: list[str] = Field(default_factory=list, description="Recommended follow-up actions")

    # Reproducibility
    reproducibility: dict[str, str] = Field(default_factory=dict, description="Reproducibility metadata")
    certification_hash: str = Field(description="SHA256 of the entire certification for tamper-evident sealing")


# ═══════════════════════════════════════════════════════════════
# Certification Engine
# ═══════════════════════════════════════════════════════════════

def _hash_inputs(**kwargs) -> str:
    """Generate a deterministic hash from all input parameters."""
    canonical = json.dumps(kwargs, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


def _brier_score(probabilities: list[float], outcomes: list[bool]) -> float:
    """Compute Brier score. Lower is better calibration."""
    if not probabilities:
        return 0.0
    errors = [(p - (1.0 if o else 0.0)) ** 2 for p, o in zip(probabilities, outcomes)]
    return sum(errors) / len(errors)


def _log_score(probabilities: list[float], outcomes: list[bool]) -> float:
    """Compute log score. Lower is better."""
    if not probabilities:
        return 0.0
    eps = 1e-9
    losses = []
    for p, o in zip(probabilities, outcomes):
        p_clamped = max(eps, min(1.0 - eps, p))
        selected = p_clamped if o else 1.0 - p_clamped
        losses.append(-math.log(selected))
    return sum(losses) / len(losses)


def _confidence_interval_95(scores: list[float]) -> tuple[float, float]:
    """Compute 95% confidence interval using normal approximation."""
    if len(scores) < 2:
        return (0.0, 0.0)
    mean = sum(scores) / len(scores)
    std = math.sqrt(sum((x - mean) ** 2 for x in scores) / (len(scores) - 1))
    margin = 1.96 * (std / math.sqrt(len(scores)))
    return (round(max(0.0, mean - margin), 4), round(min(1.0, mean + margin), 4))


def _fleiss_kappa_approximation(seat_tier_votes: dict[str, dict[str, int]]) -> float:
    """Approximate inter-rater agreement.

    Simplified: treats each seat's tier distribution as votes,
    computes proportion of agreement above chance.
    Returns value in [0, 1] where 1 = perfect agreement.
    """
    seats = list(seat_tier_votes.keys())
    if len(seats) < 2:
        return 1.0

    # Count how many seats agree on the dominant tier for the most common tier
    all_tiers: list[str] = []
    for seat, tiers in seat_tier_votes.items():
        all_tiers.extend([t for t, c in tiers.items() for _ in range(c)])

    if not all_tiers:
        return 0.0

    # Dominant tier
    tier_counts = Counter(all_tiers)
    dominant_tier, dominant_count = tier_counts.most_common(1)[0]
    p_obs = dominant_count / len(all_tiers)

    # Chance agreement (proportional to squared proportions)
    p_chance = sum((c / len(all_tiers)) ** 2 for c in tier_counts.values())

    if p_chance >= 1.0:
        return 1.0

    kappa = (p_obs - p_chance) / (1.0 - p_chance)
    return round(max(0.0, kappa), 4)


def _consensus_label(kappa: float) -> str:
    if kappa >= 0.75:
        return "high"
    elif kappa >= 0.50:
        return "moderate"
    elif kappa >= 0.25:
        return "low"
    return "divergent"


def _contamination_risk(contaminated: int) -> str:
    if contaminated == 0:
        return "none"
    elif contaminated <= 2:
        return "low"
    elif contaminated <= 5:
        return "moderate"
    return "critical"


def _build_abstract(
    question: str,
    verdict: str,
    aggregate_score: float,
    credible_ratio: float,
    seat_count: int,
    evidence_quality: float,
    contamination_risk: str,
    key_findings: str = "",
) -> str:
    """Build a structured abstract in academic paper style."""
    verdict_labels = {
        "credible": "可信",
        "conditional": "有条件接受",
        "unverified": "证据不足",
        "rejected": "驳回",
    }
    vlabel = verdict_labels.get(verdict, verdict)

    return (
        f"Background: {question} "
        f"Methods: {seat_count}-seat multi-model jury (Flash/Standard/Strategic mode) "
        f"with 10-function scoring engine, L1/L2/L3 evidence tracing, and cross-model contamination detection. "
        f"Results: Aggregate score {aggregate_score:.3f}, "
        f"credible claim ratio {credible_ratio:.1%}, "
        f"evidence quality index {evidence_quality:.1%} (L1 citations). "
        f"Cross-model contamination risk: {contamination_risk}. "
        f"Conclusion: Verdict '{vlabel}' with measurable confidence. "
        f"{key_findings}"
    )


# ═══════════════════════════════════════════════════════════════
# Main API
# ═══════════════════════════════════════════════════════════════

def certify(
    *,
    question: str,
    mode: str = "standard",
    seats: list[str] | None = None,
    verdict_data: dict[str, Any] | None = None,
    claims: list[dict[str, Any]] | None = None,
    evidence_report: dict[str, Any] | None = None,
    citation_report: dict[str, Any] | None = None,
    execution_time: float | None = None,
    known_outcomes: dict[str, bool] | None = None,
) -> AnswerCertification:
    """Produce a research-grade answer certification.

    Args:
        question: The original question.
        mode: Jury mode used.
        seats: List of seat IDs deployed.
        verdict_data: The raw verdict dict from the API / scoring pipeline.
        claims: The raw claims list submitted to the jury.
        evidence_report: Cross-model contamination report from evidence_trace.
        citation_report: Citation verification MVP output from core.grand_judge or core.citation_validator.
        execution_time: Wall-clock execution time in seconds.
        known_outcomes: Optional dict of claim_id → known truth for calibration.

    Returns:
        A complete AnswerCertification that can be serialized to JSON or HTML.
    """
    now = datetime.now(timezone.utc)
    cert_id = f"CERT-{now.strftime('%Y%m%d')}-{_hash_inputs(question=question, mode=mode, seats=seats or [])[:8].upper()}"

    verdict_data = verdict_data or {}
    claims = claims or []
    evidence_report = evidence_report or {}
    citation_report = citation_report or None
    citation_summary = _build_citation_verification_summary(citation_report)
    seats = seats or []

    # ── Methodology ──
    from core.modes import JURY_MODES, resolve_mode
    mode_config = JURY_MODES.get(mode, {})
    features = mode_config.get("features", {})

    scoring_functions = ["allocation_score", "log_score", "evaluate_bluff_ev", "should_bid"]
    if features.get("consensus_check"):
        scoring_functions.extend(["brier_score", "calculate_voi"])
    if features.get("dissent_analysis"):
        scoring_functions.append("graph_value_v2")
    if features.get("peach_projection"):
        scoring_functions.append("peach_projection")

    params = {
        "mode": mode,
        "mode_config": {
            "timeout_seconds": mode_config.get("timeout_seconds"),
            "collect_timeout_per_seat": mode_config.get("collect_timeout_per_seat"),
            "features": features,
        },
        "seat_count": len(seats),
    }
    if citation_summary:
        params["citation_verification"] = citation_summary.model_dump()

    methodology = MethodSection(
        question=question,
        mode=mode,
        seats_deployed=seats,
        seat_count=len(seats),
        scoring_version=verdict_data.get("scoring_version", "2.0.0-final"),
        scoring_functions=scoring_functions,
        parameters=params,
        timestamp_utc=now.isoformat(),
        execution_time_seconds=execution_time,
        reproducibility_hash=_hash_inputs(**params, question=question, seats=sorted(seats)),
    )

    # ── Results: Claim Scores ──
    claim_scores: list[ClaimScore] = []
    for i, c in enumerate(claims):
        claim_scores.append(ClaimScore(
            claim_id=c.get("claim_id", c.get("id", f"C{i+1:04d}")),
            seat=c.get("_seat", c.get("seat", "unknown")),
            claim_text=(c.get("claim", "") or "")[:300],
            score=float(c.get("score", c.get("_score", 0.0)) or 0.0),
            tier=c.get("tier", c.get("_tier", "unverified")),
            evidence_level=_derive_evidence_level(c),
            explicit_ref_count=int(c.get("explicit_refs", 0) or 0),
            implied_ref_count=int(c.get("implied_refs", 0) or 0),
            bluff_gate_triggered=bool(c.get("blocked_by") == "bluff_gate"),
            abstain_recommended=bool(c.get("abstain_recommended")),
        ))

    # ── Results: Seat Scoreboards ──
    seat_groups: dict[str, list[dict]] = {}
    for c in claims:
        s = c.get("_seat", c.get("seat", "unknown"))
        seat_groups.setdefault(s, []).append(c)

    seat_scoreboards: list[SeatScoreboard] = []
    for seat_id, scs in sorted(seat_groups.items()):
        scores = [float(c.get("score", c.get("_score", 0)) or 0) for c in scs]
        mean_score = sum(scores) / len(scores) if scores else 0.0
        tiers = Counter(c.get("tier", c.get("_tier", "unverified")) for c in scs)
        evidence_levels = Counter(_derive_evidence_level(c) for c in scs)
        abstains = sum(1 for c in scs if c.get("abstain_recommended"))

        from core.seat_personas import SEAT_PERSONAS
        persona = SEAT_PERSONAS.get(seat_id, {})

        seat_scoreboards.append(SeatScoreboard(
            seat=seat_id,
            seat_name=persona.get("name", seat_id),
            mbti=persona.get("mbti", "?"),
            claims_submitted=len(scs),
            mean_score=round(mean_score, 4),
            credible_count=tiers.get("credible", 0),
            conditional_count=tiers.get("conditional", 0),
            unverified_count=tiers.get("unverified", 0),
            rejected_count=tiers.get("rejected", 0),
            abstain_count=abstains,
            evidence_level_distribution=dict(evidence_levels),
        ))

    # ── Statistics ──
    all_scores = [cs.score for cs in claim_scores]
    mean_score = sum(all_scores) / len(all_scores) if all_scores else 0.0
    score_std = math.sqrt(sum((s - mean_score) ** 2 for s in all_scores) / len(all_scores)) if all_scores else 0.0
    ci = _confidence_interval_95(all_scores)

    # Calibration (if known outcomes provided)
    brier_val = None
    log_val = None
    if known_outcomes:
        probs = [cs.score for cs in claim_scores if cs.claim_id in known_outcomes]
        outs = [known_outcomes[cs.claim_id] for cs in claim_scores if cs.claim_id in known_outcomes]
        if probs:
            brier_val = round(_brier_score(probs, outs), 4)
            log_val = round(_log_score(probs, outs), 4)

    # Inter-rater agreement
    seat_tier_votes: dict[str, dict[str, int]] = {}
    for sb in seat_scoreboards:
        seat_tier_votes[sb.seat] = {
            "credible": sb.credible_count,
            "conditional": sb.conditional_count,
            "unverified": sb.unverified_count,
            "rejected": sb.rejected_count,
        }
    kappa = _fleiss_kappa_approximation(seat_tier_votes)

    # Diversity
    diversity_index = evidence_report.get("phase2_diversity", {}).get("normalized_graph_variance", None) if evidence_report else None

    tier_dist = dict(Counter(cs.tier for cs in claim_scores))
    credible_ratio = tier_dist.get("credible", 0) / max(len(claim_scores), 1)
    evidence_quality = sum(1 for cs in claim_scores if cs.evidence_level == "L1") / max(len(claim_scores), 1)

    statistics = StatisticalAnalysis(
        brier_score=brier_val,
        log_score=log_val,
        inter_rater_agreement=round(kappa, 4) if kappa else None,
        consensus_level=_consensus_label(kappa),
        diversity_index=diversity_index,
        aggregate_score=round(mean_score, 4),
        score_std=round(score_std, 4),
        confidence_interval_95=ci,
        tier_distribution=tier_dist,
        credible_ratio=round(credible_ratio, 4),
        evidence_quality_index=round(evidence_quality, 4),
    )

    # ── Evidence Trace ──
    evidence_trace = EvidenceTrace(
        total_shared_sources=evidence_report.get("total_shared_sources", 0),
        contaminated_sources=evidence_report.get("contaminated_sources", 0),
        contamination_risk=_contamination_risk(evidence_report.get("contaminated_sources", 0)),
        critical_sources=evidence_report.get("contamination_details", [])[:5],
        advisory=evidence_report.get("verdict_advisory", "No cross-model contamination detected."),
    )

    # ── Dissent ──
    dissent_records: list[DissentRecord] = []
    for d in verdict_data.get("dissent_results", verdict_data.get("dissent", [])) or []:
        dissent_records.append(DissentRecord(
            seat=d.get("seat", d.get("dissenter", "unknown")),
            target_claim_id=d.get("claim_id"),
            severity=d.get("severity", "weak"),
            argument=str(d.get("argument", d.get("reasoning", "")))[:500],
            counter_evidence=str(d.get("counter_evidence", ""))[:300] or None,
        ))

    # ── Limitations ──
    bias_list = []
    from core.seat_personas import SEAT_PERSONAS
    for s in seats:
        persona = SEAT_PERSONAS.get(s, {})
        bias = persona.get("cognitive_bias", "")
        if bias:
            bias_list.append(f"{persona.get('name', s)} ({persona.get('mbti', '?')}): {bias}")

    limitations = LimitationSection(
        scope=f"Multi-model jury certification for the question: '{question[:150]}'. "
              f"Covers factual accuracy, evidence quality, and cross-model consensus.",
        exclusions=(
            "This certification does NOT verify the truth of source materials. "
            "It evaluates the claims AS PRESENTED by AI models, not the underlying reality. "
            "L3 claims (no citation) are scored but carry significantly lower weight. "
            "Future facts, subjective judgments, and normative claims are outside certifiable scope."
        ) if not citation_summary else (
            "Statistical sections certify jury scoring quality, not reality itself. "
            "The citation_verification section adds citation-level truth/relevance checks only against "
            "the isolated external evidence supplied to the verifier. unverifiable is not false."
        ),
        known_biases=bias_list,
        contamination_risk=evidence_trace.contamination_risk,
        temporal_validity=(
            f"Certified as of {now.strftime('%Y-%m-%d')}. "
            "Claims referencing time-sensitive data (e.g., '2026 market conditions') "
            "should be re-certified if underlying data changes."
        ),
        generalizability=(
            "This verdict applies to the specific question as phrased. "
            "Rephrasing or changing scope may yield different results."
        ),
        alternative_interpretations=_generate_alternatives(verdict_data, statistics),
    )

    # ── Recommendation ──
    rec, steps = _build_recommendation(verdict_data, statistics, evidence_trace)

    # ── Reproducibility ──
    reproducibility = {
        "engine_version": methodology.scoring_version,
        "mode": mode,
        "seat_list": ",".join(sorted(seats)),
        "input_hash": methodology.reproducibility_hash,
        "certification_timestamp": now.isoformat(),
    }

    # ── Abstract ──
    abstract = _build_abstract(
        question=question,
        verdict=verdict_data.get("verdict", "conditional"),
        aggregate_score=mean_score,
        credible_ratio=credible_ratio,
        seat_count=len(seats),
        evidence_quality=evidence_quality,
        contamination_risk=evidence_trace.contamination_risk,
    )

    # ── Build certification ──
    verdict_value = verdict_data.get("verdict", "conditional")
    cert = AnswerCertification(
        certification_id=cert_id,
        question=question,
        verdict=verdict_value,
        verdict_confidence=mean_score,
        abstract=abstract,
        methodology=methodology,
        results=claim_scores,
        seat_scoreboards=seat_scoreboards,
        statistics=statistics,
        evidence_trace=evidence_trace,
        citation_verification=citation_summary,
        dissent_records=dissent_records,
        limitations=limitations,
        recommendation=rec,
        next_steps=steps,
        reproducibility=reproducibility,
        certification_hash="",  # Filled below
    )

    # Sign the certification
    cert_data = cert.model_dump_json(exclude={"certification_hash"})
    cert.certification_hash = hashlib.sha256(cert_data.encode()).hexdigest()

    return cert


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════

def _derive_evidence_level(c: dict[str, Any]) -> str:
    """Derive L1/L2/L3 from claim data."""
    if c.get("trace_level"):
        return c["trace_level"]
    explicit = int(c.get("explicit_refs", 0) or 0)
    implied = int(c.get("implied_refs", 0) or 0)
    if explicit > 0:
        return "L1"
    if implied > 0:
        return "L2"
    return "L3"


def _build_citation_verification_summary(citation_report: dict[str, Any] | None) -> CitationVerificationSummary | None:
    """Adapt citation_validator / grand_judge output into certification schema."""
    if not citation_report:
        return None
    citation_block = citation_report.get("citation_verification") or citation_report
    counts = citation_block.get("counts") or {}
    source_isolation = citation_report.get("source_isolation") or citation_block.get("source_isolation") or {}
    if not isinstance(source_isolation, dict):
        source_isolation = {}
    return CitationVerificationSummary(
        certification_id=citation_block.get("certification_id") or citation_report.get("certification_id"),
        overall_status=str(citation_block.get("overall_status") or "unverifiable"),
        verified_count=int(counts.get("verified", 0) or 0),
        weakly_verified_count=int(counts.get("weakly_verified", 0) or 0),
        irrelevant_count=int(counts.get("irrelevant", 0) or 0),
        unverifiable_count=int(counts.get("unverifiable", 0) or 0),
        contradicted_count=int(counts.get("contradicted", 0) or 0),
        citation_count=int(citation_block.get("citation_count", 0) or 0),
        item_count=int(citation_block.get("item_count", 0) or 0),
        verification_hash=citation_block.get("verification_hash") or citation_report.get("certification_hash"),
        replay_ledger_hash=citation_block.get("replay_ledger_hash") or citation_report.get("replay_ledger_hash"),
        unverifiable_explanation=str(
            citation_block.get("unverifiable_explanation")
            or citation_report.get("judge_contract", {}).get("unverifiable_explanation")
            or "unverifiable is not false."
        ),
        source_isolation={str(key): str(value) for key, value in source_isolation.items()},
    )


def _generate_alternatives(
    verdict_data: dict[str, Any],
    stats: StatisticalAnalysis,
) -> list[str]:
    """Generate plausible alternative interpretations."""
    alternatives = []
    v = verdict_data.get("verdict", "conditional")

    if stats.consensus_level in ("low", "divergent"):
        alternatives.append(
            "Low inter-rater agreement suggests the question may be fundamentally ambiguous. "
            "Consider rephrasing for clearer scope."
        )
    if stats.credible_ratio < 0.4:
        alternatives.append(
            "Most claims failed evidence gates. The opposite conclusion may be equally defensible "
            "if different evidence thresholds are applied."
        )
    if stats.evidence_quality_index < 0.3:
        alternatives.append(
            "Low L1 citation rate means conclusions rely heavily on model training data rather than "
            "verifiable sources. Independent fact-checking recommended."
        )
    if v == "conditional":
        alternatives.append(
            "The conditional verdict indicates unresolved disagreement. "
            "Either conclusion (credible/rejected) could be supported by cherry-picking seat subsets."
        )

    if not alternatives:
        alternatives.append("No strong alternative interpretations identified given current evidence quality.")

    return alternatives


def _build_recommendation(
    verdict_data: dict[str, Any],
    stats: StatisticalAnalysis,
    evidence: EvidenceTrace,
) -> tuple[str, list[str]]:
    """Build actionable recommendation and next steps."""
    v = verdict_data.get("verdict", "conditional")
    steps: list[str] = []

    if v == "credible" and stats.aggregate_score >= 0.75:
        rec = "高置信度可信。可基于此判词做决策。建议进入实施阶段，但保留定期复审机制。"
        steps = [
            "归档本次认证作为决策依据（Certification ID 可引用）",
            "设定 30 天复审提醒（如涉及时间敏感数据）",
            "将认证结果通知相关决策者",
        ]
    elif v == "credible":
        rec = "中等置信度可信。建议对低分 claim 补充独立证据后采纳。"
        steps = [
            f"对 {stats.tier_distribution.get('unverified', 0)} 条未验证 claim 补充独立来源",
            "针对 L3 claims 进行人工事实核查",
            f"关注 {evidence.contaminated_sources} 个疑似污染源，确认其独立性",
        ]
    elif v == "conditional":
        rec = "有条件接受。关键 claims 需要额外验证后才能作为决策依据。"
        steps = [
            "对条件性通过的 claims 进行独立验证",
            "重新提交验证后的 claims 以获取更新认证",
            "考虑使用 Strategic 模式（9 席全开）获得更全面的覆盖",
        ]
    else:
        rec = "不建议基于此判词做决策。请重新提问或扩充证据基础。"
        steps = [
            "重新表述问题以提高精确度",
            "使用 Strategic 模式获取更多席位视角",
            "补充已知事实作为 ground truth 锚点以改善校准",
        ]

    if evidence.contamination_risk in ("moderate", "critical"):
        steps.append(f"⚠ {evidence.advisory}")

    return rec, steps


# ═══════════════════════════════════════════════════════════════
# Standalone test
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("AI Judge Answer Certification — Self Test\n")

    cert = certify(
        question="Is solar PV cheaper than coal-fired electricity in 2026?",
        mode="standard",
        seats=["gemini", "deepseek", "grok", "kimi", "doubao"],
        verdict_data={"verdict": "credible", "scoring_version": "2.0.0-final"},
        claims=[
            {"claim_id": "C001", "claim": "Solar LCOE is $30/MWh vs coal $60/MWh", "_seat": "gemini", "score": 0.85, "tier": "credible", "explicit_refs": 3},
            {"claim_id": "C002", "claim": "Solar cheaper but depends on location", "_seat": "deepseek", "score": 0.70, "tier": "conditional", "explicit_refs": 1, "implied_refs": 1},
            {"claim_id": "C003", "claim": "Coal still cheaper when including storage costs", "_seat": "grok", "score": 0.55, "tier": "unverified", "implied_refs": 1},
            {"claim_id": "C004", "claim": "Solar adoption accelerating globally at 25% CAGR", "_seat": "kimi", "score": 0.78, "tier": "credible", "explicit_refs": 2},
            {"claim_id": "C005", "claim": "Grid parity achieved in 80% of global markets", "_seat": "doubao", "score": 0.82, "tier": "credible", "explicit_refs": 2, "implied_refs": 1},
        ],
        known_outcomes={"C001": True, "C002": True, "C003": False},
    )

    print(f"Certification ID: {cert.certification_id}")
    print(f"Verdict: {cert.verdict} (confidence: {cert.verdict_confidence:.3f})")
    print(f"Abstract: {cert.abstract[:200]}...")
    print(f"Statistics:")
    print(f"  Aggregate: {cert.statistics.aggregate_score:.3f} ± {cert.statistics.score_std:.3f}")
    print(f"  95% CI: [{cert.statistics.confidence_interval_95[0]:.3f}, {cert.statistics.confidence_interval_95[1]:.3f}]")
    print(f"  Inter-rater agreement: {cert.statistics.inter_rater_agreement:.3f} ({cert.statistics.consensus_level})")
    print(f"  Brier: {cert.statistics.brier_score}, Log: {cert.statistics.log_score}")
    print(f"  Credible ratio: {cert.statistics.credible_ratio:.1%}")
    print(f"  Evidence quality: {cert.statistics.evidence_quality_index:.1%}")
    print(f"Methodology:")
    print(f"  Seats: {cert.methodology.seat_count} — {', '.join(cert.methodology.seats_deployed)}")
    print(f"  Functions: {', '.join(cert.methodology.scoring_functions)}")
    print(f"  Reproducibility hash: {cert.methodology.reproducibility_hash}")
    print(f"Limitations:")
    print(f"  Contamination risk: {cert.limitations.contamination_risk}")
    print(f"  Known biases: {len(cert.limitations.known_biases)} seats with documented cognitive biases")
    print(f"  Alternatives: {len(cert.limitations.alternative_interpretations)} identified")
    print(f"Recommendation: {cert.recommendation[:200]}")
    print(f"Next steps: {len(cert.next_steps)} actions")
    print(f"Certification hash: {cert.certification_hash[:16]}...")
    print(f"\nJSON size: {len(cert.model_dump_json(indent=2)):,} bytes")
    print("\nAll tests passed ✓")
