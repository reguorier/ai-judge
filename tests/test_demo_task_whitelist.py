"""
Test Demo Task Whitelist
public-demo-readiness-v1.0.0
"""

import json
import os
import pytest


@pytest.fixture
def whitelist_path():
    return os.path.expanduser(
        "/Users/audimacmini/Library/Application Support/AI Judge/runtime/product/demo/demo_task_whitelist.json"
    )


@pytest.fixture
def whitelist(whitelist_path):
    with open(whitelist_path) as f:
        return json.load(f)


@pytest.fixture
def tasks(whitelist):
    return whitelist["tasks"]


def test_minimum_six_tasks(tasks):
    assert len(tasks) >= 6, f"Need >=6 tasks, got {len(tasks)}"


def test_category_distribution(tasks):
    cats = {}
    for t in tasks:
        parts = t["id"].split("-")
        cat = parts[1] if len(parts) >= 2 else "UNKNOWN"
        cats[cat] = cats.get(cat, 0) + 1

    assert cats.get("LEGAL", 0) >= 3, f"Need >=3 legal tasks, got {cats.get('LEGAL', 0)}"
    assert cats.get("PRODUCT", 0) >= 1, f"Need >=1 product task, got {cats.get('PRODUCT', 0)}"
    assert cats.get("AUDIT", 0) >= 1, f"Need >=1 audit task, got {cats.get('AUDIT', 0)}"
    assert cats.get("DECISION", 0) >= 1, f"Need >=1 decision task, got {cats.get('DECISION', 0)}"


def test_each_task_required_fields(tasks):
    required_fields = {
        "id", "label", "question", "mode", "reader_type",
        "risk_level", "public_demo_safe", "expected_takeaway", "forbidden_inputs",
    }
    for t in tasks:
        missing = required_fields - set(t.keys())
        assert not missing, f"Task {t.get('id', '?')} missing fields: {missing}"


def test_all_tasks_deep_judge_mode(tasks):
    for t in tasks:
        assert t["mode"] == "deep_judge", f"Task {t['id']} must use deep_judge mode"


def test_all_public_demo_safe(tasks):
    for t in tasks:
        assert t["public_demo_safe"] is True, f"Task {t['id']} must be public_demo_safe"


def test_forbidden_inputs_not_empty(tasks):
    for t in tasks:
        assert len(t["forbidden_inputs"]) > 0, f"Task {t['id']} must list forbidden inputs"


def test_ids_unique(tasks):
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"