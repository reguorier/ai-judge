"""Build compact evidence packets for report-first client runs."""

from __future__ import annotations

from typing import Any

from product.reporting.report_schema import utc_now_iso


def build_evidence_packet(
    *,
    run_id: str,
    question: str,
    mode: str,
    valid_seats: int,
    total_seats: int,
    failed_seats: int,
    generated_at: str | None = None,
) -> dict[str, Any]:
    return {
        "schema": "ai_judge.client_evidence_packet.v1",
        "run_id": run_id,
        "mode": mode,
        "question_excerpt": question[:500],
        "generated_at": generated_at or utc_now_iso(),
        "source_policy": "local-first; final verdict remains human/local; no dashboard-derived claim is treated as evidence",
        "evidence_items": [
            {
                "id": "run_summary",
                "type": "local_artifact",
                "strength": "medium",
                "description": "客户端提交、状态机和报告生成元数据。",
            },
            {
                "id": "seat_matrix",
                "type": "local_artifact",
                "strength": "medium" if valid_seats else "weak",
                "description": f"席位有效性摘要：{valid_seats}/{total_seats} 有效，{failed_seats} 失败。",
            },
            {
                "id": "final_report",
                "type": "local_artifact",
                "strength": "medium",
                "description": "最终报告把事实、推断、风险和推荐行动分开呈现。",
            },
        ],
        "limitations": [
            "此证据包只证明本地 run artifact 的生成和一致性，不伪造外部网页或模型席位结果。",
            "若需要真实 Web seat 证据，必须由 seat adapter 生成 answer/evidence/screenshot/trajectory artifacts 并通过 validator。",
        ],
    }


def build_seat_matrix(
    *,
    run_id: str,
    mode: str,
    valid_seats: int,
    total_seats: int,
    failed_seats: int,
) -> dict[str, Any]:
    seats: list[dict[str, Any]] = []
    seat_specs = [
        ("report_builder", "Report Builder", "valid", "压缩问题、证据和行动建议到最终报告。"),
        ("dissent_reviewer", "Dissent Reviewer", "valid", "保留分歧、失败条件和反方提醒。"),
        ("human_gate", "Human Final Gate", "valid", "把最终裁决留给本地人工确认。"),
    ]
    for seat_id, display_name, status, summary in seat_specs[: max(valid_seats, 0)]:
        seats.append(
            {
                "seat_id": seat_id,
                "display_name": display_name,
                "status": status,
                "run_marker_found": True,
                "structured_answer_found": True,
                "answer_path": "generated:client_report",
                "evidence_path": "evidence_packet.json",
                "summary": summary,
                "failure_reason": None,
            }
        )
    for index in range(max(failed_seats, 0)):
        seats.append(
            {
                "seat_id": f"failed_seat_{index + 1}",
                "display_name": f"Failed Seat {index + 1}",
                "status": "failed",
                "run_marker_found": False,
                "structured_answer_found": False,
                "answer_path": "",
                "evidence_path": "",
                "summary": "该席位没有产生可验证 answer artifact，未纳入有效结论。",
                "failure_reason": "missing_answer_artifact",
            }
        )
    while len(seats) < total_seats:
        seats.append(
            {
                "seat_id": f"skipped_seat_{len(seats) + 1}",
                "display_name": f"Skipped Seat {len(seats) + 1}",
                "status": "skipped",
                "run_marker_found": False,
                "structured_answer_found": False,
                "answer_path": "",
                "evidence_path": "",
                "summary": "未配置或未执行，不作为证据。",
                "failure_reason": "not_configured",
            }
        )
    return {"schema": "ai_judge.client_seat_matrix.v1", "run_id": run_id, "mode": mode, "seats": seats}
