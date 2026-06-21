"""Meeting-room static contract tests — Phase F.

Validates the meeting room / robot speech card contract in the canonical
dashboard.js source.  Uses actual CSS class names and function names from
the canonical source (P3.8.13-RC1 / P3.8.14-RC1 baseline).

NB: The PKG installer uses parliament-themed names (parliamentBubbleHtml,
submitParliamentMotion, etc.) that are NOT in the canonical source.
The canonical source uses renderRoomAgentTurnCards / executeJudge / submitJudge.
Both produce the same article.agent-turn-card contract.
"""

import os
import re
import pytest

CANON_REPO = os.path.abspath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", ".."
))


def _load_source(filename: str) -> str:
    path = os.path.join(CANON_REPO, "product", filename)
    if not os.path.exists(path):
        pytest.skip(f"{filename} not found at {path}")
    with open(path, encoding="utf-8") as f:
        return f.read()


def _func_body(source: str, func_name: str) -> str:
    """Extract function body from JS source."""
    pattern = rf'function\s+{re.escape(func_name)}\s*\('
    m = re.search(pattern, source)
    if not m:
        return ""
    brace_pos = source.find('{', m.end())
    if brace_pos == -1:
        return ""
    depth, i = 1, brace_pos + 1
    while i < len(source) and depth > 0:
        if source[i] == '{':
            depth += 1
        elif source[i] == '}':
            depth -= 1
        i += 1
    return source[brace_pos:i]


class TestMeetingRoomAgentTurnCardContract:
    """agent-turn-card robot speech module contract."""

    @pytest.fixture(scope="class")
    def dashboard_js(self):
        return _load_source("dashboard.js")

    @pytest.fixture(scope="class")
    def dashboard_html(self):
        return _load_source("dashboard.html")

    # ─── Core rendering ────────────────────────────────────────────

    def test_render_room_agent_turn_cards_exists(self, dashboard_js):
        """Canonical agent turn card renderer."""
        assert "function renderRoomAgentTurnCards" in dashboard_js

    def test_agent_turn_card_css_class(self, dashboard_js):
        """article.agent-turn-card in JS."""
        assert "agent-turn-card" in dashboard_js

    def test_render_room_exists(self, dashboard_js):
        """renderRoom() assembles meeting room."""
        assert "function renderRoom" in dashboard_js

    def test_submit_judge_exists(self, dashboard_js):
        """submitJudge() prepares question for judgment."""
        assert "function submitJudge" in dashboard_js

    def test_execute_judge_exists(self, dashboard_js):
        """executeJudge() is the async submit flow (calls /api/judge)."""
        assert "function executeJudge" in dashboard_js
        body = _func_body(dashboard_js, "executeJudge")
        assert "/api" in body or "fetchJson" in body or "API_BASE" in body, \
            "executeJudge body must reference API"

    # ─── CSS class contract (canonical names) ──────────────────────

    def test_turn_card(self, dashboard_js):
        assert "turn-card" in dashboard_js

    def test_turn_header(self, dashboard_js):
        assert "turn-header" in dashboard_js

    def test_turn_avatar(self, dashboard_js):
        assert "turn-avatar" in dashboard_js

    def test_turn_body(self, dashboard_js):
        assert "turn-body" in dashboard_js

    def test_turn_summary(self, dashboard_js):
        assert "turn-summary" in dashboard_js

    def test_turn_model_and_status(self, dashboard_js):
        for cls in ["turn-model", "turn-status-badge"]:
            assert cls in dashboard_js, f"{cls} not found"

    def test_turn_expand(self, dashboard_js):
        assert "turn-expand" in dashboard_js

    # ─── HTML shell ────────────────────────────────────────────────

    def test_dashboard_html_view_room(self, dashboard_html):
        """Canonical meeting room view id."""
        assert 'id="view-room"' in dashboard_html or "view-room" in dashboard_html

    def test_dashboard_html_room_thread_messages(self, dashboard_html):
        """Message stream container."""
        assert "room-thread-messages" in dashboard_html

    def test_dashboard_html_agent_turn_card_css(self, dashboard_html):
        """CSS styling for agent-turn-card."""
        assert "agent-turn-card" in dashboard_html


class TestWerewolfFlow:
    """Werewolf mode must be present and use the same agent-turn-card."""

    @pytest.fixture(scope="class")
    def dashboard_js(self):
        return _load_source("dashboard.js")

    def test_werewolf_mode_entry(self, dashboard_js):
        """Werewolf mode defined in MODES array."""
        assert '"werewolf"' in dashboard_js or "'werewolf'" in dashboard_js

    def test_werewolf_api_referenced(self, dashboard_js):
        """Dashboard references /api/werewolf."""
        assert "/api/werewolf" in dashboard_js

    def test_werewolf_uses_agent_turn_card(self, dashboard_js):
        """Same turn-card CSS contract reused for Werewolf."""
        assert "agent-turn-card" in dashboard_js

    def test_werewolf_board_and_session_fetch(self, dashboard_js):
        """Werewolf mode fetches boards and sessions from API."""
        assert "/api/werewolf/boards" in dashboard_js
        assert "/api/werewolf/sessions" in dashboard_js


class TestPKGvsSourceNaming:
    """Document that PKG installer parliament names are absent from canonical source."""

    PKG_ONLY = [
        "parliamentBubbleHtml",
        "parliamentSpeakers",
        "parliamentToolEventsForSpeaker",
        "submitParliamentMotion",
        "startPreRunFlow",
        "confirmAndStartParliament",
        "werewolfEventToMessage",
    ]

    @pytest.fixture(scope="class")
    def dashboard_js(self):
        return _load_source("dashboard.js")

    @pytest.mark.parametrize("pkg_name", PKG_ONLY)
    def test_pkg_name_not_in_canonical(self, pkg_name, dashboard_js):
        """PKG installer naming should NOT appear in canonical source.

        The canonical source uses renderRoomAgentTurnCards / executeJudge etc.
        The PKG installer uses parliament-themed aliases that appear only in
        the bundled distribution artifact (419KB dashboard.js).
        """
        assert pkg_name not in dashboard_js, \
            f"PKG-only name '{pkg_name}' leaked into canonical source"
