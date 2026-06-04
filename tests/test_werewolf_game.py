import threading
import time

import core.werewolf_executor as werewolf_executor
from core.werewolf_game import (
    BOARD_PRESETS,
    DEFAULT_WEREWOLF_SEATS,
    DEFAULT_PLAY_MODE,
    PLAY_MODE_PRESETS,
    WEREWOLF_CANDIDATE_SEATS,
    board_seat_count,
    build_werewolf_demo,
    normalize_werewolf_roster,
    play_mode_public_config,
    play_mode_rules,
    private_role_packets,
)
from core.werewolf_executor import (
    _contains_private_role_leak,
    _runner_call_with_timeout,
    _run_single_seat,
    build_public_speech_prompt,
    resume_werewolf_without_substitute,
    start_werewolf_session,
    substitute_werewolf_seat,
)


def test_werewolf_pool_has_fourteen_candidates_and_default_nine():
    assert len(WEREWOLF_CANDIDATE_SEATS) == 14
    assert len(DEFAULT_WEREWOLF_SEATS) == 9
    assert "grok" in WEREWOLF_CANDIDATE_SEATS
    assert "wenxin" in WEREWOLF_CANDIDATE_SEATS
    assert "meta" in WEREWOLF_CANDIDATE_SEATS
    assert "grok" in DEFAULT_WEREWOLF_SEATS
    assert "wenxin" in DEFAULT_WEREWOLF_SEATS
    assert normalize_werewolf_roster(["gork", "wenxin"])[:2] == ["grok", "wenxin"]


def test_werewolf_boards_expose_white_wolf_and_fourteen_player_presets():
    assert board_seat_count("quick_6") == 6
    assert board_seat_count("compact_8") == 8
    assert board_seat_count("standard") == 9
    assert board_seat_count("advanced_10") == 10
    assert board_seat_count("classic_12") == 12
    assert board_seat_count("thirteen") == 13
    assert board_seat_count("white_wolf") == 9
    assert board_seat_count("standard_14") == 14
    assert board_seat_count("white_wolf_14") == 14
    assert "white_wolf" in BOARD_PRESETS["classic_12"]["roles"]
    assert "white_wolf" in BOARD_PRESETS["thirteen"]["roles"]
    assert "white_wolf" in BOARD_PRESETS["white_wolf"]["roles"]
    assert "white_wolf" in BOARD_PRESETS["white_wolf_14"]["roles"]


def test_werewolf_only_exposes_standard_and_ai_experiment_modes():
    modes = play_mode_public_config()

    assert DEFAULT_PLAY_MODE == "standard_competition"
    assert set(modes) == {"standard_competition", "ai_experiment"}
    assert PLAY_MODE_PRESETS["standard_competition"]["rules"]["allow_no_death_night"] is True
    assert play_mode_rules("ai_experiment")["audit_level"] == "full"


def test_fourteen_player_white_wolf_demo_uses_all_candidate_seats():
    game = build_werewolf_demo("14 人白狼王验收局", board="white_wolf_14")

    assert game["board"] == "white_wolf_14"
    assert game["seat_count"] == 14
    assert game["mode"] == "werewolf_14_pool_14p_white_wolf_14"
    assert len(game["seats"]) == 14
    assert game["standby_seats"] == []
    assert any(packet["role"] == "white_wolf" for packet in game["private_role_packets"])


def test_private_role_packets_stay_separate_from_public_events():
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]
    game = build_werewolf_demo("测试狼人杀", selected_seats=selected)
    public_text = "\n".join(event["text"] for event in game["public_events"])
    packets = private_role_packets(selected)

    assert len(packets) == 9
    assert {packet["seat"] for packet in packets} == set(selected)
    assert any(packet["seat"] == "wenxin" and packet["role"] == "werewolf" for packet in packets)
    assert "private_role_packets" in game
    assert all("role" not in player and "team" not in player for player in game["public_players"])
    assert "你是狼人" not in public_text
    assert game["winner"] == "good"
    assert game["scoreboard"][0]["seat"] == "claude"


def test_werewolf_substitute_takes_over_original_role_slot():
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]
    game = build_werewolf_demo(
        "替补局",
        selected_seats=selected,
        substitutions=[{"offline_seat": "grok", "substitute_seat": "mimo"}],
    )
    packets = {packet["seat"]: packet for packet in game["private_role_packets"]}
    public_text = "\n".join(event["text"] for event in game["public_events"])

    assert "mimo" in game["seats"]
    assert "grok" not in game["seats"]
    assert packets["mimo"]["role"] == "werewolf"
    assert packets["mimo"]["replaced_seat"] == "grok"
    assert game["substitutions"][0]["offline_seat"] == "grok"
    assert "替补接管" in public_text


def test_real_werewolf_executor_uses_runner_responses_not_template_speeches():
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]

    def fake_runner(question, seats, **_kwargs):
        seat = seats[0]
        return [{
            "seat": seat,
            "seat_name": seat,
            "ok": True,
            "response": f"我的公开发言：{seat} 的真实网页回复，我会根据身份目标发言。",
            "elapsed_seconds": 0.1,
            "prompt_id": f"test-{seat}",
            "execution_validity": {"valid": True},
        }]

    game = start_werewolf_session(
        topic="真实执行器测试",
        selected_seats=selected,
        runner=fake_runner,
        background=False,
    )
    text = "\n".join(event.get("text", "") for event in game["events"])

    assert game["status"] == "complete"
    assert all("role" in player and "team" in player for player in game["players"])
    assert "chatgpt 的真实网页回复" in text
    assert "我的公开发言" not in text
    assert "第一天我倾向先稳住节奏" not in text
    day_speeches = [
        event for event in game["events"]
        if event.get("kind") == "seat" and event.get("phase") == "day-1"
    ]
    assert len(day_speeches) == 9


def test_real_werewolf_executor_starts_with_sheriff_gate():
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]

    def fake_runner(question, seats, **_kwargs):
        seat = seats[0]
        if "警长竞选阶段" in question:
            return [{"seat": seat, "ok": True, "response": "我不竞选", "execution_validity": {"valid": True}}]
        return [{
            "seat": seat,
            "ok": True,
            "response": f"我的公开发言：{seat} 的真实网页回复，我会根据身份目标发言。",
            "execution_validity": {"valid": True},
        }]

    game = start_werewolf_session(
        topic="警长流程测试",
        selected_seats=selected,
        runner=fake_runner,
        background=False,
    )
    text = "\n".join(event.get("text", "") for event in game["events"])

    assert "警长竞选开始" in text
    assert "无人竞选警长" in text
    sheriff_events = [
        event for event in game["events"]
        if event.get("kind") == "seat" and event.get("phase") == "sheriff-election"
    ]
    assert len(sheriff_events) == 9
    assert all("警长竞选意向" in event.get("text", "") for event in sheriff_events)
    assert game["play_mode"] == "standard_competition"


def _install_minimal_werewolf_session(game_id="werewolf-unit", board="standard"):
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]
    players = werewolf_executor.default_werewolf_players(selected, board=board)
    packets = {packet["seat"]: packet for packet in private_role_packets(selected, board=board)}
    session = {
        "game_id": game_id,
        "topic": "规则单测",
        "status": "running",
        "phase": "night-2",
        "board": board,
        "events": [],
        "raw_results": [],
        "players": [werewolf_executor._public_player(player, reveal=False) for player in players],
        "scores": [],
        "next_player_index": 0,
        "version": 1,
        "_players": players,
        "_private_role_packets": packets,
        "_public_history": "",
        "_phase": "night-2",
        "_background": False,
        "_eliminated": {},
        "_rules": play_mode_rules("standard_competition"),
        "_guard_last_protected": None,
        "_guard_protected": None,
        "_witch_antidote_used": False,
        "_witch_poison_used": False,
        "_last_words_granted": [],
        "_hunter_triggered": False,
        "_seer_checked": [],
        "_seer_results": {},
        "_sheriff": None,
        "_god_roles": {"seer", "witch", "hunter", "guard", "knight"},
        "_board": board,
    }
    with werewolf_executor._LOCK:
        werewolf_executor._SESSIONS[game_id] = session
    return game_id


def test_werewolf_night_can_end_as_peaceful_night_without_random_death():
    game_id = _install_minimal_werewolf_session()

    def peaceful_runner(question, seats, **_kwargs):
        if "狼人夜间讨论" in question:
            response = "我的夜间讨论：今晚空刀，制造平安夜信息差。"
        elif "狼人猎杀投票" in question:
            response = "我猎杀：空刀"
        elif "守卫守护阶段" in question:
            response = "我守护：Gemini"
        elif "预言家查验阶段" in question:
            response = "我查验：Claude"
        elif "女巫行动阶段" in question:
            response = "解药：不使用\n毒药：不使用"
        else:
            response = "我的公开发言：继续观察票型。"
        return [{"seat": seats[0], "ok": True, "response": response, "execution_validity": {"valid": True}}]

    result = werewolf_executor._run_night_phase(game_id, peaceful_runner, night=2, next_phase="day-2")
    session = werewolf_executor._SESSIONS[game_id]
    text = "\n".join(event.get("text", "") for event in session["events"])

    assert result == "day-2"
    assert session["_eliminated"] == {}
    assert "平安夜" in text


def test_werewolf_vote_with_no_valid_votes_has_no_random_exile():
    game_id = _install_minimal_werewolf_session()
    with werewolf_executor._LOCK:
        werewolf_executor._SESSIONS[game_id]["_phase"] = "vote-1"
        werewolf_executor._SESSIONS[game_id]["phase"] = "vote-1"

    def invalid_vote_runner(question, seats, **_kwargs):
        return [{"seat": seats[0], "ok": True, "response": "我还需要继续观察。", "execution_validity": {"valid": True}}]

    result = werewolf_executor._run_vote_phase(
        game_id,
        invalid_vote_runner,
        vote_label="第一轮投票淘汰",
        vote=1,
        next_phase="night-2",
    )
    session = werewolf_executor._SESSIONS[game_id]
    text = "\n".join(event.get("text", "") for event in session["events"])

    assert result == "night-2"
    assert session["_eliminated"] == {}
    assert "无人出局" in text


def test_real_werewolf_executor_keeps_roles_sealed_until_complete():
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]
    release = threading.Event()

    def slow_runner(question, seats, **_kwargs):
        release.wait(timeout=1)
        return [{"seat": seats[0], "ok": False, "error": {"code": "manual_stop"}}]

    game = start_werewolf_session(
        topic="密封测试",
        selected_seats=selected,
        runner=slow_runner,
        background=True,
    )

    assert game["status"] in {"queued", "running"}
    assert all("role" not in player and "team" not in player for player in game["players"])
    assert game["spectator_role_map"]["chatgpt"]["role_label"] == "平民"
    assert game["spectator_role_map"]["deepseek"]["role_label"] == "猎人"
    release.set()


def test_werewolf_prompts_encourage_competitive_strategy_without_public_role_leak():
    player = type("Player", (), {"seat": "chatgpt"})()
    packet = {
        "role": "villager",
        "role_label": "平民",
        "team": "good",
        "private_prompt": "你要帮助好人阵营找狼。",
    }

    prompt = werewolf_executor._build_day_prompt(
        topic="提示词测试",
        player=player,
        packet=packet,
        public_history="Qwen：我先观察。",
        day=1,
        is_first=True,
        eliminated={},
    )
    vote_prompt = werewolf_executor._build_vote_prompt(
        topic="提示词测试",
        player=player,
        public_history="Qwen：我先观察。",
        vote_round=1,
        alive_players=[player],
    )

    for text in (prompt, vote_prompt):
        assert "终局每个席位都会评分" in text
        assert "民搅" in text
        assert "泼脏水" in text
        assert "穿衣服" in text


def test_real_werewolf_executor_rejects_invalid_bridge_capture():
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]

    def invalid_runner(question, seats, **_kwargs):
        return [{
            "seat": seats[0],
            "ok": True,
            "response": "AI Judge 网页以及本地客户端最终版如何达到 Marvis 级多 Agent 工作台质感？",
            "execution_validity": {"valid": False, "reason": "response_not_relevant"},
        }]

    game = start_werewolf_session(
        topic="真实执行器测试",
        selected_seats=selected,
        runner=invalid_runner,
        background=False,
    )

    seat_events = [event for event in game["events"] if event.get("kind") == "seat"]
    assert seat_events[0]["status"] == "failed"
    assert "response_not_relevant" in seat_events[0]["text"]
    assert "Marvis 级多 Agent" not in seat_events[0]["text"]


def test_real_werewolf_executor_accepts_player_prefixed_capture_even_if_generic_matcher_misses():
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]

    def prefixed_runner(question, seats, **_kwargs):
        return [{
            "seat": seats[0],
            "ok": True,
            "response": "分析链：先收集发言差异。\n我的公开发言：我先不急着定狼，重点看谁跟风、谁回避投票依据。",
            "execution_validity": {"valid": False, "reason": "response_not_relevant"},
        }]

    game = start_werewolf_session(
        topic="真实执行器测试",
        selected_seats=selected,
        runner=prefixed_runner,
        background=False,
    )

    first_seat = [
        event for event in game["events"]
        if event.get("kind") == "seat" and event.get("phase") == "day-1"
    ][0]
    assert first_seat["status"] == "done"
    assert first_seat["text"] == "我先不急着定狼，重点看谁跟风、谁回避投票依据。"
    assert "分析链" not in first_seat["text"]


def test_real_werewolf_executor_rejects_private_role_leak_from_public_flow():
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]

    def leak_runner(question, seats, **_kwargs):
        return [{
            "seat": seats[0],
            "ok": True,
            "response": "随后直接写正文\n必须包裹在特定标记中\n作为狼人，我需要伪装成好人并误导白天投票。",
            "execution_validity": {"valid": True},
        }]

    game = start_werewolf_session(
        topic="私有身份泄露测试",
        selected_seats=selected,
        runner=leak_runner,
        background=False,
    )

    first_seat = [event for event in game["events"] if event.get("kind") == "seat"][0]
    assert first_seat["status"] == "failed"
    assert "private_role_leak" in first_seat["text"]
    assert "作为狼人" not in first_seat["text"]
    assert _contains_private_role_leak("作为狼人，我需要伪装成好人")


def test_werewolf_single_seat_soft_timeout_accepts_late_answer():
    def slow_runner(question, seats, **_kwargs):
        time.sleep(0.05)
        return [{"seat": seats[0], "ok": True, "response": "我的公开发言：迟到的发言"}]

    results = _runner_call_with_timeout(
        slow_runner,
        timeout_seconds=0.01,
        late_grace_seconds=0.1,
        question="狼人杀测试",
        seats=["chatgpt"],
    )
    raw = results[0]

    assert raw["ok"] is True
    assert raw["late_after_hard_timeout"] is True


def test_werewolf_no_substitute_degrades_instead_of_deadlocking(monkeypatch):
    selected = list(WEREWOLF_CANDIDATE_SEATS[:9])
    monkeypatch.setattr(werewolf_executor, "WEREWOLF_CANDIDATE_SEATS", selected)
    game_id = _install_minimal_werewolf_session("werewolf-no-substitute")
    player = werewolf_executor._SESSIONS[game_id]["_players"][0]

    blocked = werewolf_executor._block_for_substitution(
        game_id,
        player,
        index=0,
        code="bridge_runner_timeout",
    )
    session = werewolf_executor._SESSIONS[game_id]
    text = "\n".join(event.get("text", "") for event in session["events"])

    assert blocked is False
    assert session["status"] == "running"
    assert session.get("pending_substitution") is None
    assert "缺席/可补收" in text or "可补收" in text


def test_real_werewolf_timeout_can_block_and_substitute_resumes(monkeypatch):
    monkeypatch.setattr(werewolf_executor, "BLOCK_FOR_MANUAL_SUBSTITUTION", True)
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]

    def timeout_runner(question, seats, **_kwargs):
        seat = seats[0]
        if seat == "claude":
            return [{"seat": seat, "ok": False, "response": "", "error": {"code": "bridge_runner_timeout"}}]
        return [{
            "seat": seat,
            "ok": True,
            "response": f"我的公开发言：{seat} 的真实玩家发言。",
            "execution_validity": {"valid": True},
        }]

    game = start_werewolf_session(
        topic="替补恢复测试",
        selected_seats=selected,
        runner=timeout_runner,
        background=False,
    )

    assert game["status"] == "blocked"
    assert game["pending_substitution"]["offline_seat"] == "claude"
    assert "claude" in game["offline_seats"]

    def resume_runner(question, seats, **_kwargs):
        seat = seats[0]
        return [{
            "seat": seat,
            "ok": True,
            "response": f"我的公开发言：{seat} 接管后继续真实发言。",
            "execution_validity": {"valid": True},
        }]

    resumed = substitute_werewolf_seat(
        game["game_id"],
        offline_seat="claude",
        substitute_seat="yuanbao",
        runner=resume_runner,
        background=False,
    )
    text = "\n".join(event.get("text", "") for event in resumed["events"])

    assert resumed["status"] == "complete"
    assert "yuanbao" in resumed["seats"]
    assert "claude" not in resumed["seats"]
    assert "Yuanbao 接管第 2 席" in text
    assert "yuanbao 接管后继续真实发言" in text


def test_real_werewolf_blocked_session_can_resume_without_substitute(monkeypatch):
    monkeypatch.setattr(werewolf_executor, "BLOCK_FOR_MANUAL_SUBSTITUTION", True)
    selected = ["chatgpt", "claude", "gemini", "deepseek", "qwen", "kimi", "grok", "doubao", "wenxin"]

    def timeout_runner(question, seats, **_kwargs):
        seat = seats[0]
        if seat == "claude":
            return [{"seat": seat, "ok": False, "response": "", "error": {"code": "bridge_runner_timeout"}}]
        return [{
            "seat": seat,
            "ok": True,
            "response": f"我的公开发言：{seat} 的真实玩家发言。",
            "execution_validity": {"valid": True},
        }]

    game = start_werewolf_session(
        topic="无替补恢复测试",
        selected_seats=selected,
        runner=timeout_runner,
        background=False,
    )

    assert game["status"] == "blocked"
    assert game["pending_substitution"]["offline_seat"] == "claude"

    def resume_runner(question, seats, **_kwargs):
        seat = seats[0]
        return [{
            "seat": seat,
            "ok": True,
            "response": f"我的公开发言：{seat} 继续发言。",
            "execution_validity": {"valid": True},
        }]

    resumed = resume_werewolf_without_substitute(
        game["game_id"],
        offline_seat="claude",
        runner=resume_runner,
        background=False,
    )
    text = "\n".join(event.get("text", "") for event in resumed["events"])

    assert resumed["status"] == "complete"
    assert resumed.get("pending_substitution") is None
    assert "暂时缺席" in text
    assert "gemini 继续发言" in text


def test_werewolf_public_prompt_hides_template_and_instructs_real_player_voice():
    player = type("Player", (), {"seat": "wenxin"})()
    prompt = build_public_speech_prompt(
        topic="谁最会伪装",
        player=player,
        packet={
            "seat": "wenxin",
            "role": "werewolf",
            "role_label": "狼人",
            "team": "werewolf",
            "private_prompt": "你是狼人，目标是伪装。",
        },
        public_history="",
    )

    assert "你的私有身份：狼人" in prompt
    assert "这是当前唯一任务" in prompt
    assert "我的公开发言" in prompt
    assert "不要直接泄露你的身份牌" in prompt
    assert "第一天我倾向先稳住节奏" not in prompt
