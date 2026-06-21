"""
Test Demo Replay Pack
public-demo-readiness-v1.0.0
"""

import json
import os
import pytest


@pytest.fixture
def demo_dir():
    return os.path.expanduser("/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo")


@pytest.fixture
def manifest(demo_dir):
    path = os.path.join(demo_dir, "demo_replay_manifest.json")
    with open(path) as f:
        return json.load(f)


@pytest.fixture
def replays(manifest):
    return manifest["replays"]


def test_at_least_three_replays(replays):
    assert len(replays) >= 3


def test_replay_directories_exist(demo_dir, replays):
    for r in replays:
        rpath = os.path.join(demo_dir, r["path"])
        assert os.path.isdir(rpath), f"Missing replay directory: {r['path']}"


def test_each_replay_has_all_files(demo_dir, replays):
    required = [
        "input.json", "final_report.html", "final_report_contract.json",
        "evidence_pack.json", "run_metadata.json", "validation_result.json", "README.md",
    ]
    for r in replays:
        rdir = os.path.join(demo_dir, r["path"])
        for fname in required:
            fpath = os.path.join(rdir, fname)
            assert os.path.isfile(fpath), f"Missing: {r['path']}/{fname}"


def test_html_files_not_empty(demo_dir, replays):
    for r in replays:
        html_path = os.path.join(demo_dir, r["path"], "final_report.html")
        size = os.path.getsize(html_path)
        assert size > 1000, f"{r['path']}/final_report.html too small ({size} bytes)"


def test_readme_has_disclaimer(demo_dir, replays):
    for r in replays:
        readme_path = os.path.join(demo_dir, r["path"], "README.md")
        with open(readme_path) as f:
            content = f.read()
        assert "合成" in content or "synthetic" in content.lower(), f"{r['path']}/README.md missing synthetic note"


def test_validation_all_pass(demo_dir, replays):
    for r in replays:
        val_path = os.path.join(demo_dir, r["path"], "validation_result.json")
        with open(val_path) as f:
            val = json.load(f)
        assert val["validation_passed"] is True, f"{r['id']} validation not passed"