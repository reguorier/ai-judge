#!/usr/bin/env python3
"""test_reader_type_profiles.py — 验证 reader_type_profiles.json。

最低要求：
- 4 个 profile 均存在
- 每个有 label/tone/max_sentence_chars
- ordinary_user 必须禁止技术术语
- professional/legal 不得删除证据与不确定性
"""

import json
import os
import pytest

PROFILES_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "Library",
    "Application Support",
    "AI Judge",
    "runtime",
    "product",
    "readability",
    "reader_type_profiles.json",
)


def _load():
    # 尝试多个路径
    paths = [
        PROFILES_PATH,
        os.path.expanduser(
            "~/Library/Application Support/AI Judge/runtime/product/readability/reader_type_profiles.json"
        ),
    ]
    for p in paths:
        if os.path.exists(p):
            with open(p, "r") as f:
                return json.load(f)
    raise FileNotFoundError(f"profiles not found in {paths}")


class TestReaderTypeProfiles:
    """reader_type_profiles.json 结构验证"""

    def test_all_four_profiles_exist(self):
        data = _load()
        rts = data["reader_types"]
        for rt in ["ordinary_user", "pm_founder", "professional_user", "legal_compliance_user"]:
            assert rt in rts, f"Missing reader_type: {rt}"
        assert len(rts) == 4, f"Expected 4 profiles, got {len(rts)}"

    def test_each_profile_has_required_fields(self):
        data = _load()
        rts = data["reader_types"]
        required_fields = ["label", "tone", "max_sentence_chars"]
        for rt_name, rt in rts.items():
            for field in required_fields:
                assert field in rt, f"{rt_name} missing field: {field}"
            assert isinstance(rt["label"], str), f"{rt_name} label not string"
            assert isinstance(rt["tone"], str), f"{rt_name} tone not string"
            assert isinstance(rt["max_sentence_chars"], int), f"{rt_name} max_sentence_chars not int"
            assert rt["max_sentence_chars"] > 0, f"{rt_name} max_sentence_chars <= 0"

    def test_ordinary_user_has_avoid_terms(self):
        data = _load()
        ou = data["reader_types"]["ordinary_user"]
        assert "avoid_terms" in ou, "ordinary_user missing avoid_terms"
        assert len(ou["avoid_terms"]) > 0, "ordinary_user avoid_terms is empty"
        assert "hard gate" in ou["avoid_terms"] or any(
            "schema" in t.lower() for t in ou["avoid_terms"]
        ), "ordinary_user must avoid technical terms"

    def test_professional_preserves_evidence_uncertainty(self):
        data = _load()
        pro = data["reader_types"]["professional_user"]
        assert pro.get("must_have_evidence_strength"), "professional must have evidence_strength"
        assert pro.get("must_have_uncertainty"), "professional must have uncertainty"

    def test_legal_preserves_legal_basis_risk_boundary(self):
        data = _load()
        leg = data["reader_types"]["legal_compliance_user"]
        assert leg.get("must_have_legal_basis"), "legal must have legal_basis"
        assert leg.get("must_have_risk_boundary"), "legal must have risk_boundary"

    def test_default_reader_type_exists(self):
        data = _load()
        default = data.get("default_reader_type")
        assert default is not None, "missing default_reader_type"
        assert default in data["reader_types"], f"default {default} not in reader_types"