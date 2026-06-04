"""Small deterministic reliability scoring for client report summaries."""

from __future__ import annotations


def score_reliability(valid_seats: int, total_seats: int, failed_seats: int = 0) -> str:
    if total_seats <= 0:
        return "low"
    ratio = max(valid_seats, 0) / total_seats
    if ratio >= 0.75 and failed_seats <= max(1, total_seats // 4):
        return "high"
    if ratio >= 0.45:
        return "medium"
    return "low"


def reliability_sentence(reliability: str, valid_seats: int, total_seats: int, failed_seats: int) -> str:
    if reliability == "high":
        return f"本次 {valid_seats}/{total_seats} 个席位有效，失败席位 {failed_seats} 个，结论可作为行动依据，但仍需保留人工最终判断。"
    if reliability == "medium":
        return f"本次 {valid_seats}/{total_seats} 个席位有效，失败席位 {failed_seats} 个，结论可用于下一步筛选，但不应直接视为最终事实。"
    return f"本次有效席位不足或失败较多：{valid_seats}/{total_seats} 个席位有效，失败席位 {failed_seats} 个，应先补证或补跑。"
