"""
Tests for live demo replay pack — public-demo-live-dry-run-v1
"""
import json
import os
import pytest

DEMO_DIR = os.path.expanduser(
    "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo"
)
REPLAY_DIR = os.path.join(DEMO_DIR, "replay")


class TestLiveDemoReplayPack:
    """Test replay pack meets live demo requirements."""

    REPLAY_IDS = ["bankruptcy_demo", "homestead_demo", "civil_code_demo"]
    REQUIRED_FILES = [
        "input.json",
        "final_report.html",
        "final_report_contract.json",
        "evidence_pack.json",
        "run_metadata.json",
        "validation_result.json",
        "README.md",
    ]

    def test_manifest_exists_and_valid(self):
        """Replay manifest must exist and list 3 replays."""
        path = os.path.join(DEMO_DIR, "demo_replay_manifest.json")
        assert os.path.isfile(path), "Manifest not found"
        with open(path) as f:
            manifest = json.load(f)
        assert len(manifest.get("replays", [])) == 3
        assert manifest["total_replays"] == 3

    def test_all_replay_dirs_exist(self):
        """All replay directories must exist."""
        for replay_id in self.REPLAY_IDS:
            rp = os.path.join(REPLAY_DIR, replay_id)
            assert os.path.isdir(rp), f"Missing replay dir: {replay_id}"

    def test_all_replay_files_present(self):
        """Each replay must have all 7 required files."""
        for replay_id in self.REPLAY_IDS:
            rp = os.path.join(REPLAY_DIR, replay_id)
            for rf in self.REQUIRED_FILES:
                fp = os.path.join(rp, rf)
                assert os.path.isfile(fp), f"Missing: {replay_id}/{rf}"

    def test_final_report_html_not_empty(self):
        """final_report.html must have content."""
        for replay_id in self.REPLAY_IDS:
            html = os.path.join(REPLAY_DIR, replay_id, "final_report.html")
            size = os.path.getsize(html)
            assert size > 100, f"{replay_id}/final_report.html too small ({size} bytes)"

    def test_replays_marked_synthetic(self):
        """All replays must be marked as synthetic."""
        path = os.path.join(DEMO_DIR, "demo_replay_manifest.json")
        with open(path) as f:
            manifest = json.load(f)
        for r in manifest["replays"]:
            assert r.get("is_synthetic") is True, f"{r['id']} not marked synthetic"
            assert r.get("contains_real_pii") is False, f"{r['id']} has real PII flag"