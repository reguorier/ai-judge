"""Graceful CDP seat adapter wrapper.

This module does not fake answered seats. It reports adapter availability and
lets existing bridge code remain the source of real browser artifacts.
"""

from __future__ import annotations

from product.seat_adapters.base import SeatRunResult


class CDPSeatRunner:
    def __init__(self, seat_id: str = "cdp") -> None:
        self.seat_id = seat_id

    def collect(self, *_args, **_kwargs) -> SeatRunResult:
        try:
            import bridges.chrome_cdp_bridge  # noqa: F401
        except Exception as exc:
            return SeatRunResult(self.seat_id, "failed", failure_reason=f"cdp_unavailable:{exc}")
        return SeatRunResult(self.seat_id, "submitted_no_answer", failure_reason="adapter wrapper requires existing bridge artifacts")
