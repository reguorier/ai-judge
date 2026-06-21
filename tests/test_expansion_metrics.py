"""Test expansion metrics — §8 thresholds."""

import json
import pytest
from pathlib import Path


METRICS_PATH = Path("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo_expansion/expansion_metrics.json")


@pytest.fixture
def metrics():
    with open(METRICS_PATH) as f:
        return json.load(f)


class TestExpansionMetricsSystemThresholds:
    """§8.1 system thresholds"""

    def test_p0_incidents_zero(self, metrics):
        assert metrics["incidents"]["p0"] == 0, f"P0 incidents: {metrics['incidents']['p0']}"

    def test_success_rate(self, metrics):
        assert metrics["runs"]["success_rate"] >= 85, f"Success rate {metrics['runs']['success_rate']}% < 85%"

    def test_avg_latency(self, metrics):
        assert metrics["runs"]["avg_latency_sec"] <= 180, f"Avg latency {metrics['runs']['avg_latency_sec']}s > 180s"

    def test_external_ratio(self, metrics):
        assert metrics["cohort"]["external_ratio"] >= 80, f"External ratio {metrics['cohort']['external_ratio']}% < 80%"


class TestExpansionMetricsUserThresholds:
    """§8.2 user thresholds"""

    def test_avg_trust(self, metrics):
        assert metrics["user_metrics"]["avg_trust"] >= 3.8, f"Trust {metrics['user_metrics']['avg_trust']} < 3.8"

    def test_avg_readability(self, metrics):
        assert metrics["user_metrics"]["avg_readability"] >= 3.8, f"Readability {metrics['user_metrics']['avg_readability']} < 3.8"

    def test_avg_actionability(self, metrics):
        assert metrics["user_metrics"]["avg_actionability"] >= 3.8, f"Actionability {metrics['user_metrics']['avg_actionability']} < 3.8"

    def test_would_use_again(self, metrics):
        assert metrics["user_metrics"]["would_use_again_pct"] >= 70, f"Would use again {metrics['user_metrics']['would_use_again_pct']}% < 70%"

    def test_would_recommend(self, metrics):
        assert metrics["user_metrics"]["would_recommend_pct"] >= 50, f"Would recommend {metrics['user_metrics']['would_recommend_pct']}% < 50%"

    def test_would_join_waitlist(self, metrics):
        assert metrics["user_metrics"]["would_join_waitlist_pct"] >= 40, f"Join waitlist {metrics['user_metrics']['would_join_waitlist_pct']}% < 40%"


class TestExpansionMetricsWaitlist:
    """Waitlist metrics"""

    def test_waitlist_total(self, metrics):
        assert metrics["waitlist"]["total"] >= 23, f"Waitlist total {metrics['waitlist']['total']} < 23"

    def test_waitlist_use_cases(self, metrics):
        use_cases = metrics["waitlist"]["use_cases"]
        assert len(use_cases) >= 4, f"Waitlist use cases {len(use_cases)} < 4"

    def test_overall_result(self, metrics):
        assert metrics["overall_result"] == "PUBLIC_DEMO_EXPANSION_V1_PASS", f"Result: {metrics['overall_result']}"