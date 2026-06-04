"""Optional Webwright seat adapter wrapper."""

from __future__ import annotations

from product.seat_adapters.base import SeatRunResult


class WebwrightSeatRunner:
    def __init__(self, seat_id: str = "webwright") -> None:
        self.seat_id = seat_id

    def collect(self, *_args, **_kwargs) -> SeatRunResult:
        try:
            import webwright  # type: ignore  # noqa: F401
        except Exception as exc:
            return SeatRunResult(self.seat_id, "failed", failure_reason=f"webwright_unavailable:{exc}")
        return SeatRunResult(self.seat_id, "submitted_no_answer", failure_reason="adapter wrapper requires answer artifacts before validation")
