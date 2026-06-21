"""Security tests for client_api backport — Phase E.

Validates:
1. No local absolute paths leak through /api/client/* endpoints
2. canRevealSecrets remains False under edge cases
3. Admin escalation blocked
4. Path traversal attempts blocked
"""

import json
import os
import sys
import pytest
import flask

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestClientApiSecurity:
    """Security invariants for the public client API."""

    @pytest.fixture
    def client_app(self):
        """Create a minimal Flask test app with client blueprint registered."""
        from product.client_api import client_blueprint

        app = flask.Flask(__name__)
        app.register_blueprint(client_blueprint)
        app.config["TESTING"] = True
        return app.test_client()

    def test_capabilities_never_reveals_secrets(self, client_app):
        """Repeated calls must always show canRevealSecrets=False."""
        for _ in range(5):
            resp = client_app.get("/api/client/capabilities")
            data = resp.get_json()
            assert data["canRevealSecrets"] is False

    def test_admin_permission_mode_rejected_via_http(self, client_app):
        """HTTP POST with permission_mode=admin must return 403."""
        resp = client_app.post(
            "/api/client/runs",
            json={"question": "test", "permission_mode": "admin"},
        )
        assert resp.status_code == 403

        # Case-insensitive variations that should also be rejected
        for pm in ["ADMIN", "Admin"]:
            resp = client_app.post(
                "/api/client/runs",
                json={"question": "test", "permission_mode": pm},
            )
            assert resp.status_code == 403, \
                f"permission_mode={pm!r} should be rejected"

    def test_normal_run_creates_without_secret_leak(self, client_app):
        """A normal run create must not leak internal paths."""
        resp = client_app.post(
            "/api/client/runs",
            json={"question": "What is 2+2?"},
        )
        assert resp.status_code in (200, 201)
        data = resp.get_json()

        # Recursively check for local paths
        def has_local_path(obj, depth=0):
            if depth > 10:
                return False
            if isinstance(obj, str):
                patterns = ["/Users/", "/home/", "C:\\", "file:///"]
                return any(p in obj for p in patterns)
            if isinstance(obj, dict):
                return any(has_local_path(v, depth + 1) for v in obj.values())
            if isinstance(obj, list):
                return any(has_local_path(v, depth + 1) for v in obj)
            return False

        assert not has_local_path(data), \
            f"Response contains local path: {json.dumps(data, default=str)[:500]}"

    def test_path_traversal_not_interpreted(self, client_app):
        """Path traversal patterns in run_id must be handled safely."""
        malicious_ids = [
            "../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "run-123/../../../secret",
        ]
        for rid in malicious_ids:
            resp = client_app.get(f"/api/client/runs/{rid}")
            # Must not 500 crash, should return 404 or structured error
            assert resp.status_code in (200, 404), \
                f"Path traversal {rid!r} caused {resp.status_code}"

    def test_get_client_run_no_local_paths(self, client_app):
        """GET run detail must not expose local absolute paths."""
        # Create a run first to get a valid run_id
        create_resp = client_app.post(
            "/api/client/runs",
            json={"question": "Security test: path leak check"},
        )
        if create_resp.status_code not in (200, 201):
            pytest.skip("Cannot create run for path leak test")

        data = create_resp.get_json()
        run_id = data.get("run", {}).get("run_id")
        if not run_id:
            pytest.skip("No run_id in response")

        run_resp = client_app.get(f"/api/client/runs/{run_id}")
        run_data = run_resp.get_json()

        def has_abs_path(obj, depth=0):
            if depth > 10:
                return False
            if isinstance(obj, str):
                return any(p in obj for p in ["/Users/", "/home/", "C:\\", "file:///"])
            if isinstance(obj, dict):
                return any(has_abs_path(v, depth + 1) for v in obj.values())
            if isinstance(obj, list):
                return any(has_abs_path(v, depth + 1) for v in obj)
            return False

        assert not has_abs_path(run_data), \
            f"Run detail leaks paths: {json.dumps(run_data, default=str)[:500]}"

    def test_capabilities_no_internal_field_leak(self, client_app):
        """Capabilities must not leak internal implementation field names."""
        resp = client_app.get("/api/client/capabilities")
        data = resp.get_json()

        # canRevealSecrets is the one legitimate field with "secret" in name
        forbidden_fields = [
            "password", "api_key", "token",
            "aws_access", "private_key", "ssh_key",
        ]
        def has_forbidden(obj, depth=0):
            if depth > 5:
                return False
            if isinstance(obj, dict):
                for k in obj:
                    for forbidden in forbidden_fields:
                        if forbidden in k.lower():
                            return True
                    if has_forbidden(obj[k], depth + 1):
                        return True
            if isinstance(obj, list):
                return any(has_forbidden(v, depth + 1) for v in obj)
            return False

        assert not has_forbidden(data), \
            "Capabilities contains forbidden field names"
