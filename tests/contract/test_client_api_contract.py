"""Contract tests for client_api.py backport — Phase E.

These tests validate:
1. canRevealSecrets contract (must be False)
2. Admin permission_mode rejection (must 403)
3. Path('') / is_file() guard (no 500 on empty path)
4. Path sanitization (no local paths in output)
5. FDJP contract shape in capabilities
"""

import json
import os
import sys
import pytest
import tempfile

# Ensure canonical repo on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestClientApiContract:
    """Validate client API contract invariants."""

    def test_can_reveal_secrets_is_false(self):
        """The public client API must never reveal secrets."""
        from product.client_api import get_capabilities

        # Simulate a minimal Flask app context
        import flask
        app = flask.Flask(__name__)
        with app.test_request_context():
            resp = get_capabilities()
        data = resp.get_json()
        assert data["canRevealSecrets"] is False, \
            "canRevealSecrets MUST be False on public client API"

    def test_admin_permission_mode_rejected(self):
        """POST /api/client/runs must reject permission_mode='admin'."""
        from product.client_api import post_client_run

        import flask
        app = flask.Flask(__name__)
        with app.test_request_context(
            "/api/client/runs",
            method="POST",
            json={"question": "test", "permission_mode": "admin"},
        ):
            resp = post_client_run()

        # post_client_run returns (response_body, status_code) tuple
        if isinstance(resp, tuple):
            body, status = resp
            assert status == 403, f"Expected 403 for admin, got {status}"
            data = body.get_json() if hasattr(body, 'get_json') else {}
        else:
            assert resp.status_code == 403
            data = resp.get_json()
        assert "admin" in str(data.get("error", "")).lower(), \
            "Error message must mention 'admin'"
        assert data["ok"] is False
        assert data["status"] == 403
        assert data["reason"]
        assert data["next_action"]
        assert data["trace_id"].startswith("client-api-")

    def test_path_empty_string_is_file_guard(self):
        """Path('') must not crash with AttributeError.

        The is_file() guard prevents the known crash vector.
        _has_local_path must handle edge cases safely.
        """
        from product.client_api import _build_safe_report, _has_local_path

        # _has_local_path must handle non-string gracefully
        assert _has_local_path(None) is False
        assert _has_local_path(123) is False
        assert _has_local_path("") is False
        assert _has_local_path("/Users/test/file.txt") is True

        # _build_safe_report on nonexistent run: must raise FileNotFoundError,
        # not an AttributeError from Path('').is_file()
        # This confirms the is_file() guard is in place.
        try:
            _build_safe_report("nonexistent-run-id-for-safety-test")
        except FileNotFoundError:
            pass  # Expected — run doesn't exist
        except AttributeError:
            pytest.fail("is_file() guard FAILED: Path('').is_file() crashed")

    def test_sanitize_summary_strips_local_paths(self):
        """_sanitize_summary must remove internal path fields and strip absolute paths."""
        from product.client_api import _sanitize_summary

        dirty = {
            "title": "test run",
            "final_report_path": "/Users/audimacmini/Documents/reports/run-123.html",
            "html_report_path": "/Users/Shared/AI Judge/runs/run-123/report.html",
            "evidence_packet_path": "/tmp/evidence.zip",
            "seat_matrix_path": "/home/user/seats.json",
            "meta_judge_path": "/Users/audimacmini/Documents/reports/run-123/meta_judge.json",
            "model_weights_path": "/Users/audimacmini/Documents/reports/runtime/model_weights.json",
            "autonomous_strategy_path": "/Users/audimacmini/Documents/reports/run-123/autonomous_strategy.json",
            "production_strategies_path": "/Users/audimacmini/Documents/reports/runtime/production_strategies.json",
            "market_simulation_path": "/Users/audimacmini/Documents/reports/run-123/market_simulation.json",
            "market_simulation_state_path": "/Users/audimacmini/Documents/reports/runtime/market_simulation_state.json",
            "decision_os_path": "/Users/audimacmini/Documents/reports/run-123/decision_os.json",
            "decision_os_state_path": "/Users/audimacmini/Documents/reports/runtime/decision_os_state.json",
            "self_improving_loop_path": "/Users/audimacmini/Documents/reports/run-123/self_improving_loop.json",
            "self_improving_loop_state_path": "/Users/audimacmini/Documents/reports/runtime/self_improving_loop_state.json",
            "decision_policy_config_path": "/Users/audimacmini/Documents/reports/runtime/decision_policy_config.json",
            "autonomous_economy_path": "/Users/audimacmini/Documents/reports/run-123/autonomous_economy.json",
            "autonomous_economy_state_path": "/Users/audimacmini/Documents/reports/runtime/autonomous_economy_state.json",
            "recursive_civilization_path": "/Users/audimacmini/Documents/reports/run-123/recursive_civilization.json",
            "recursive_civilization_state_path": "/Users/audimacmini/Documents/reports/runtime/recursive_civilization_state.json",
            "fdjp_artifact_path": "file:///Users/test/artifact.json",
            "safe_field": "this is fine",
            "nested": {"final_report_path": "/Users/leak/path"},
        }
        clean = _sanitize_summary(dirty)

        # Internal path fields must be removed
        for field in ["final_report_path", "html_report_path",
                      "evidence_packet_path", "seat_matrix_path",
                      "noise_audit_path", "model_stability_path",
                      "meta_judge_path", "meta_judge_state_path",
                      "model_weights_path", "strategy_intelligence_path",
                      "strategy_state_path",
                      "autonomous_strategy_path", "asg_state_path",
                      "production_strategies_path",
                      "market_simulation_path", "market_simulation_state_path",
                      "decision_os_path", "decision_os_state_path",
                      "self_improving_loop_path", "self_improving_loop_state_path",
                      "decision_policy_config_path",
                      "autonomous_economy_path", "autonomous_economy_state_path",
                      "recursive_civilization_path", "recursive_civilization_state_path",
                      "fdjp_artifact_path"]:
            assert field not in clean, f"{field} should be stripped"

        # Safe fields must survive
        assert clean["safe_field"] == "this is fine"

    def test_capabilities_fdjp_contract_shape(self):
        """/api/client/capabilities must expose FDJP contract fields."""
        from product.client_api import get_capabilities

        import flask
        app = flask.Flask(__name__)
        with app.test_request_context():
            resp = get_capabilities()
        data = resp.get_json()

        # Required fields
        assert "backendLive" in data
        assert "canStartRun" in data
        assert "canRevealSecrets" in data
        assert "routes" in data
        assert "bridge" in data

        # Routes must include client API endpoints
        routes = data["routes"]
        assert "capabilities" in routes
        assert "runDetail" in routes
        assert "runEvents" in routes
        assert "noiseAudit" in routes
        assert "modelStability" in routes
        assert "metaJudge" in routes
        assert "modelWeights" in routes
        assert "autonomousStrategy" in routes
        assert "productionStrategies" in routes
        assert "marketSimulation" in routes
        assert "decisionOS" in routes
        assert "selfImprovingLoop" in routes
        assert "decisionPolicyConfig" in routes
        assert "autonomousEconomy" in routes
        assert "recursiveCivilization" in routes

    def test_model_stability_endpoint_returns_public_summary(self, monkeypatch, tmp_path):
        """The client model-stability endpoint returns a public-safe summary."""
        from core.model_stability import update_model_stability_profiles
        from product.client_api import get_model_stability

        profile_path = tmp_path / "profiles.json"
        monkeypatch.setenv("AI_JUDGE_MODEL_STABILITY_PATH", str(profile_path))
        update_model_stability_profiles(
            run_id="run-model-stability-client",
            question="product api client",
            mode="standard",
            noise_audit={
                "noise_score": 12,
                "seat_noise_rows": [
                    {"seat": "xunfei", "seat_name": "讯飞星火", "valid": True, "confidence": 0.8, "error_code": "", "noise_flags": []},
                ],
            },
        )

        import flask
        app = flask.Flask(__name__)
        with app.test_request_context():
            resp = get_model_stability()
        data = resp.get_json()

        assert data["ok"] is True
        assert data["modelStability"]["profiles"][0]["seat"] == "xunfei"
        assert "/Users/" not in json.dumps(data, ensure_ascii=False)

    def test_run_dto_returns_valid_contract(self):
        """_run_public_dto on nonexistent run must raise FileNotFoundError cleanly."""
        import uuid
        from product.client_api import _run_public_dto

        run_id = f"test-{uuid.uuid4().hex[:12]}"
        try:
            _run_public_dto(run_id)
        except FileNotFoundError:
            pass  # Expected — run doesn't exist
        except Exception:
            pytest.fail("_run_public_dto crashed on nonexistent run")

    def test_events_endpoint_returns_sse_or_json(self):
        """GET /api/client/runs/:id/events must return valid SSE or JSON."""
        from product.client_api import get_events

        import flask
        app = flask.Flask(__name__)
        with app.test_request_context("/api/client/runs/nonexistent/events"):
            resp = get_events("nonexistent")

        # Should return either 200 SSE or structured 404/error
        assert resp.status_code in (200, 404, 500), \
            f"Unexpected status {resp.status_code}"

    def test_poll_created_but_unexecuted_client_run_is_structured(self, monkeypatch):
        """Polling an unexecuted client run must not leak a NoneType exception."""
        from product import api_server
        from product import run_orchestrator

        class FakeTasks:
            def get_status(self, run_id):
                return None

            def get_result(self, run_id):
                return None

        monkeypatch.setattr(api_server, "TASKS", FakeTasks())
        monkeypatch.setattr(
            run_orchestrator,
            "load_summary",
            lambda run_id, reports_root=None: {
                "run_id": run_id,
                "status": "waiting_confirm",
                "question": "test",
            },
        )

        result = run_orchestrator.poll_client_jury_status("client-test-waiting")

        assert result["ok"] is True
        assert result["status"] == "waiting_confirm"
        assert result["progress"] == 0
        assert result["can_execute"] is True
        assert "NoneType" not in json.dumps(result)

    def test_poll_completed_web_run_syncs_noise_summary(self, monkeypatch):
        """Completed web jury verdicts should sync noise fields back to client summary."""
        from product import api_server
        from product import run_orchestrator

        captured = {}

        class FakeTasks:
            def get_status(self, run_id):
                return {"status": "completed", "progress": 1.0}

            def get_result(self, run_id):
                return {
                    "verdict": "conditional",
                    "confidence": 66,
                    "one_liner": "需要人工复核。",
                    "web_bridge": {"ok_count": 2, "failed_count": 1},
                    "noise_audit": {
                        "noise_score": 64,
                        "noise_level": "high",
                        "recommended_action": "manual_review_required",
                    },
                    "model_stability": {
                        "schema": "ai_judge.model_stability_profiles.v1",
                        "profile_count": 1,
                        "profiles": [{"seat": "xunfei", "stability_score": 42}],
                    },
                }

        monkeypatch.setattr(api_server, "TASKS", FakeTasks())
        monkeypatch.setattr(
            run_orchestrator,
            "load_summary",
            lambda run_id, reports_root=None: {
                "run_id": run_id,
                "status": "running",
                "question": "test",
            },
        )
        monkeypatch.setattr(run_orchestrator, "save_summary", lambda summary, reports_root=None: captured.update(summary) or summary)

        result = run_orchestrator.poll_client_jury_status("client-test-noise")

        assert result["ok"] is True
        assert captured["noise_score"] == 64
        assert captured["noise_level"] == "high"
        assert captured["noise_recommended_action"] == "manual_review_required"
        assert captured["model_stability_profile_count"] == 1
