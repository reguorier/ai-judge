#!/usr/bin/env python3
"""Tests for performance_observer.py.

Validates that the performance observer correctly detects
threshold violations and sets appropriate status.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from runtime.product.observability.performance_observer import (
    PerformanceObserver,
    PerformanceRecord,
    THRESHOLDS,
)


class TestPerformanceObserver:
    """Test the performance observer module."""

    def test_observer_importable(self):
        assert PerformanceObserver is not None

    def test_observe_returns_record(self):
        record = PerformanceObserver.observe(
            run_id="test-1",
            latency_total_ms=50000,
            search_agent_latency_ms=10000,
            artifact_count=8,
        )
        assert isinstance(record, PerformanceRecord)

    def test_ok_when_all_within_thresholds(self):
        record = PerformanceObserver.observe(
            run_id="test-ok",
            latency_total_ms=100_000,  # 100s < 180s
            search_agent_latency_ms=20_000,  # 20s < 30s
            renderer_latency_ms=1000,
            validator_latency_ms=1000,  # combined 2s < 3s
            artifact_write_latency_ms=3000,  # 3s < 5s
            artifact_count=8,  # >= 6
        )
        assert record.performance_status == "ok"
        assert record.degraded_reason is None

    def test_total_latency_exceeded(self):
        record = PerformanceObserver.observe(
            run_id="test-slow",
            latency_total_ms=200_000,  # 200s > 180s
            search_agent_latency_ms=10_000,
            artifact_count=8,
        )
        assert record.performance_status == "degraded"
        assert record.degraded_reason == "latency_exceeded"
        assert len(record.threshold_violations) >= 1

    def test_search_agent_latency_exceeded(self):
        record = PerformanceObserver.observe(
            run_id="test-search-slow",
            latency_total_ms=100_000,
            search_agent_latency_ms=40_000,  # 40s > 30s
            artifact_count=8,
        )
        assert record.performance_status == "degraded"
        violation_metrics = [v["metric"] for v in record.threshold_violations]
        assert "search_agent_latency_ms" in violation_metrics

    def test_renderer_validator_combined_exceeded(self):
        record = PerformanceObserver.observe(
            run_id="test-render-slow",
            latency_total_ms=100_000,
            renderer_latency_ms=2000,
            validator_latency_ms=2000,  # combined 4s > 3s
            artifact_count=8,
        )
        assert record.performance_status == "degraded"
        violation_metrics = [v["metric"] for v in record.threshold_violations]
        assert "renderer_validator_combined_latency_ms" in violation_metrics

    def test_artifact_write_exceeded(self):
        record = PerformanceObserver.observe(
            run_id="test-write-slow",
            latency_total_ms=100_000,
            artifact_write_latency_ms=6_000,  # 6s > 5s
            artifact_count=8,
        )
        assert record.performance_status == "degraded"
        violation_metrics = [v["metric"] for v in record.threshold_violations]
        assert "artifact_write_latency_ms" in violation_metrics

    def test_artifact_count_below_min(self):
        record = PerformanceObserver.observe(
            run_id="test-few-artifacts",
            latency_total_ms=100_000,
            artifact_count=3,  # < 6
        )
        assert record.performance_status == "degraded"
        violation_metrics = [v["metric"] for v in record.threshold_violations]
        assert "artifact_count" in violation_metrics

    def test_multiple_violations(self):
        record = PerformanceObserver.observe(
            run_id="test-multi-violation",
            latency_total_ms=200_000,  # > 180s
            search_agent_latency_ms=40_000,  # > 30s
            artifact_count=3,  # < 6
        )
        assert len(record.threshold_violations) >= 3

    def test_to_dict_serializable(self):
        record = PerformanceObserver.observe(
            run_id="test-dict",
            latency_total_ms=100_000,
            artifact_count=8,
        )
        d = record.to_dict()
        import json
        json.dumps(d)  # should not raise
        assert d["run_id"] == "test-dict"

    def test_thresholds_defined(self):
        assert "latency_total_ms" in THRESHOLDS
        assert THRESHOLDS["latency_total_ms"] == 180_000
        assert THRESHOLDS["search_agent_latency_ms"] == 30_000
        assert THRESHOLDS["artifact_count_min"] == 6

    def test_validate_existing_record(self):
        record = PerformanceRecord(
            run_id="test-validate",
            latency_total_ms=200_000,
            artifact_count=8,
        )
        record = PerformanceObserver.validate(record)
        assert record.performance_status == "degraded"


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "-q"]))