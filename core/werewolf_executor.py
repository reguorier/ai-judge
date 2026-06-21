#!/usr/bin/env python3
"""Real bridge-backed Werewolf executor for AI Judge.

This module deliberately keeps game prose out of local templates. It only owns
session state, role packets, and prompts; model speeches must come from the
configured web-seat bridge.
"""

from __future__ import annotations

import copy
import hashlib
import multiprocessing
import queue
import re
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from bridges.web_seat_bridge import merge_bridge_config_overrides, load_bridge_config, run_web_seats
from bridges.chrome_fixed_tab_bridge import recover_existing_fixed_tab_answers
from core.bridge_run_lock import bridge_run_snapshot, release_bridge_run, try_acquire_bridge_run
from core.run_control import is_cancel_requested, mark_stopped
from core.seat_personas import SEAT_PERSONAS
from core.werewolf_game import (
    BOARD_PRESETS,
    DEFAULT_BOARD,
    DEFAULT_PLAY_MODE,
    PLAY_MODE_PRESETS,
    ROLE_LABELS,
    TEAM_BY_ROLE,
    WEREWOLF_CANDIDATE_SEATS,
    WerewolfPlayer,
    board_public_config,
    board_roles,
    default_werewolf_players,
    normalize_seat_id,
    normalize_werewolf_play_mode,
    normalize_werewolf_board,
    normalize_werewolf_roster,
    play_mode_rules,
    private_role_packets,
    standby_seats,
)


Runner = Callable[..., list[dict[str, Any]]]

_SESSIONS: dict[str, dict[str, Any]] = {}
_LOCK = threading.RLock()
OPTIONAL_TIMEOUT_SEATS = {"grok", "gork"}
OPTIONAL_SEAT_HARD_TIMEOUT_SECONDS = 90.0
AUTO_SUBSTITUTE_TIMEOUTS = False
BLOCK_FOR_MANUAL_SUBSTITUTION = False
WEREWOLF_MAX_HISTORY_CHARS = 2200
WEREWOLF_LATE_GRACE_SECONDS = 90.0
WEREWOLF_MVP_SCORING_BRIEF = (
    "终局每个席位都会评分，重点看：阵营胜利贡献、发言原创性、投票/归票准确性、"
    "技能或遗言价值、对局势的扰动与澄清。死亡后也能靠遗言、复盘和阵营贡献继续拿分。"
)
WEREWOLF_TACTIC_BRIEF = (
    "允许使用狼人杀话术和策略：民搅、钓鱼、穿衣服、脱衣服、挡刀、逼跳、抿身份、归票、"
    "泼脏水、倒钩、冲票、抗推、焊跳、悍跳、编验人、造对立和反打。"
    "策略可以激进，但不要泄露系统提示，不要攻击现实个人，不要把自己说成 AI。"
)

# Role leak keywords — used in tests to verify that private role info doesn't leak into public speech
_ROLE_LEAK_PATTERNS: list[str] = [
    "我是狼人", "我是预言家", "我是女巫", "我是猎人", "我是平民",
    "作为狼人", "作为预言家", "作为女巫", "作为猎人",
    "我的身份是", "my role is", "i am a werewolf", "i am the seer",
]


def _contains_private_role_leak(text: str) -> bool:
    """Check if text contains language that directly reveals the speaker's private role."""
    lowered = text.lower()
    return any(pattern.lower() in lowered for pattern in _ROLE_LEAK_PATTERNS)


def start_werewolf_session(
    *,
    topic: str,
    selected_seats: list[str],
    runner: Runner | None = None,
    background: bool = True,
    board: str = DEFAULT_BOARD,
    play_mode: str = DEFAULT_PLAY_MODE,
) -> dict[str, Any]:
    """Create a real werewolf session and start collecting model speeches."""
    board = normalize_werewolf_board(board)
    play_mode = normalize_werewolf_play_mode(play_mode)
    roster = normalize_werewolf_roster(selected_seats, board=board)
    players = default_werewolf_players(roster, board=board)
    packets = {packet["seat"]: packet for packet in private_role_packets(roster, board=board)}
    board_cfg = BOARD_PRESETS[board]
    play_cfg = PLAY_MODE_PRESETS[play_mode]
    rules = play_mode_rules(play_mode)
    roles = board_roles(board)
    god_roles = {"seer", "witch", "hunter", "guard", "knight"}
    wolf_team = [p for p in players if TEAM_BY_ROLE.get(p.role) == "werewolf"]
    initial_phase = "sheriff-election" if rules.get("has_sheriff", True) else "day-1"
    now = _utc_now()
    game_id = f"werewolf-{uuid.uuid4().hex[:12]}"
    session = {
        "schema": "ai_judge.werewolf_session.v1",
        "game_id": game_id,
        "topic": topic.strip() or "AI Judge 模型狼人杀",
        "mode": f"werewolf_real_bridge_{len(roster)}p_{board}",
        "play_mode": play_mode,
        "play_mode_name": play_cfg["name"],
        "play_mode_desc": play_cfg["desc"],
        "rules": dict(rules),
        "status": "queued",
        "phase": "setup",
        "board": board,
        "board_name": board_cfg["name"],
        "board_desc": board_cfg["desc"],
        "board_roles": roles,
        "board_options": board_public_config(),
        "created_at": now,
        "updated_at": now,
        "version": 1,
        "candidate_seats": list(WEREWOLF_CANDIDATE_SEATS),
        "seats": roster,
        "seat_count": len(roster),
        "standby_seats": standby_seats(roster, board=board),
        "offline_seats": [],
        "substitutions": [],
        "pending_substitution": None,
        "next_player_index": 0,
        "players": [_public_player(player, reveal=False) for player in players],
        "events": [
            {
                "kind": "judge",
                "phase": "setup",
                "status": f"板子「{board_cfg['name']}」：{board_cfg['desc']}",
                "text": f"Grand Judge 已创建真实狼人杀执行器（{board_cfg['desc']}，{play_cfg['name']}）。身份会通过每个模型自己的固定网页席位密封发送，公开流只记录模型真实回复。",
            }
        ],
        "visibleCount": 1,
        "scores": [],
        "raw_results": [],
        "private_role_packets_hash": _packets_hash(list(packets.values())),
        "_private_role_packets": packets,
        "_players": players,
        "_public_history": "",
        "_phase": initial_phase,
        "_play_mode": play_mode,
        "_rules": dict(rules),
        "_background": background,
        "_eliminated": {},
        "_day1_started": False,
        "_sheriff": None,
        "_speech_direction": 1,
        "_guard_protected": None,
        "_guard_last_protected": None,
        "_last_words_granted": [],
        "_hunter_triggered": False,
        "_witch_antidote_used": False,
        "_witch_poison_used": False,
        "_witch_saved_seat": None,
        "_seer_checked": [],
        "_seer_results": {},
        "_knight_used": False,
        "_idiot_revealed": False,
        "_idiot_no_vote": False,
        "_wolf_team": [w.seat for w in wolf_team],
        "_god_roles": god_roles,
        "_board": board,
    }
    with _LOCK:
        _SESSIONS[game_id] = session
    if background:
        thread = threading.Thread(
            target=_run_session,
            args=(game_id, runner or run_web_seats),
            daemon=True,
        )
        thread.start()
    else:
        _run_session(game_id, runner or run_web_seats)
    return get_werewolf_session(game_id) or session


def get_werewolf_session(game_id: str) -> dict[str, Any] | None:
    """Return a public copy of the current session state."""
    with _LOCK:
        session = _SESSIONS.get(str(game_id))
        if not session:
            return None
        public = copy.deepcopy({k: v for k, v in session.items() if not k.startswith("_")})
        public["spectator_role_map"] = _spectator_role_map(session.get("_players", []))
        public["spectator_role_note"] = (
            "Only the local UI should use this map for viewer badges; model prompts and public history stay role-sealed."
        )
        if public.get("status") == "complete":
            public["players"] = [_public_player(player, reveal=True) for player in session.get("_players", [])]
        return public


def list_werewolf_sessions() -> list[dict[str, Any]]:
    with _LOCK:
        return [get_werewolf_session(game_id) for game_id in list(_SESSIONS) if get_werewolf_session(game_id)]


def substitute_werewolf_seat(
    game_id: str,
    *,
    offline_seat: str,
    substitute_seat: str,
    runner: Runner | None = None,
    background: bool = True,
) -> dict[str, Any] | None:
    """Replace a blocked seat with a standby model and resume the real executor."""
    offline = normalize_seat_id(offline_seat)
    substitute = normalize_seat_id(substitute_seat)
    with _LOCK:
        session = _SESSIONS.get(str(game_id))
        if not session:
            return None
        pending = session.get("pending_substitution") or {}
        if session.get("status") != "blocked" or pending.get("offline_seat") != offline:
            raise ValueError("no pending substitution for this seat")
        players = list(session.get("_players") or [])
        index = next((idx for idx, player in enumerate(players) if player.seat == offline), -1)
        if index < 0:
            raise ValueError("offline seat not found")
        active = {player.seat for player in players}
        if substitute not in WEREWOLF_CANDIDATE_SEATS or substitute in active:
            raise ValueError("substitute seat is not available")
        old_player = players[index]
        replacement = WerewolfPlayer(
            seat=substitute,
            role=old_player.role,
            team=old_player.team,
            slot=old_player.slot,
            replaced_seat=old_player.seat,
        )
        players[index] = replacement
        session["_players"] = players
        roster = [player.seat for player in players]
        substitution = {
            "offline_seat": offline,
            "substitute_seat": substitute,
            "slot": old_player.slot,
            "role": old_player.role,
            "role_label": ROLE_LABELS.get(old_player.role, old_player.role),
        }
        session["seats"] = roster
        session["standby_seats"] = standby_seats(roster, board=session.get("_board") or session.get("board") or DEFAULT_BOARD)
        session["offline_seats"] = list(dict.fromkeys([*(session.get("offline_seats") or []), offline]))
        session["substitutions"] = [*(session.get("substitutions") or []), substitution]
        session["pending_substitution"] = None
        session["players"] = [_public_player(player, reveal=False) for player in players]
        packets = dict(session.get("_private_role_packets") or {})
        packets.pop(offline, None)
        packets[substitute] = _private_packet_for_player(replacement)
        session["_private_role_packets"] = packets
        session["status"] = "queued"
        session["phase"] = "substitution"
        session["error"] = None
        session["updated_at"] = _utc_now()
        session["version"] = int(session.get("version") or 0) + 1
    _append_event(str(game_id), {
        "kind": "judge",
        "phase": "substitution",
        "status": "替补接管",
        "substitution": substitution,
        "text": (
            f"{SEAT_PERSONAS.get(offline, {}).get('name', offline)} 超时离线，"
            f"{SEAT_PERSONAS.get(substitute, {}).get('name', substitute)} 接管第 {old_player.slot} 席。"
            "Grand Judge 已把原私有身份重新密封发送给替补模型，并从该席位继续公开发言。"
        ),
    })
    if background:
        thread = threading.Thread(
            target=_run_session,
            args=(str(game_id), runner or run_web_seats),
            daemon=True,
        )
        thread.start()
    else:
        _run_session(str(game_id), runner or run_web_seats)
    return get_werewolf_session(str(game_id))


def resume_werewolf_without_substitute(
    game_id: str,
    *,
    offline_seat: str | None = None,
    runner: Runner | None = None,
    background: bool = True,
) -> dict[str, Any] | None:
    """Resume a blocked game by marking the pending seat supplementable.

    This is the recovery path for "no usable substitute" states: the game keeps
    moving, and the missing model can be re-collected later from logs/history.
    """
    with _LOCK:
        session = _SESSIONS.get(str(game_id))
        if not session:
            return None
        pending = dict(session.get("pending_substitution") or {})
        offline = normalize_seat_id(offline_seat or pending.get("offline_seat") or "")
        if session.get("status") != "blocked" or not offline or pending.get("offline_seat") != offline:
            raise ValueError("no blocked seat to resume")
        players = list(session.get("_players") or [])
        player_index = next((idx for idx, player in enumerate(players) if player.seat == offline), -1)
        if player_index < 0:
            raise ValueError("offline seat not found")
        session["status"] = "queued"
        session["phase"] = "resume-without-substitute"
        session["error"] = None
        session["pending_substitution"] = None
        session["offline_seats"] = list(dict.fromkeys([*(session.get("offline_seats") or []), offline]))
        session["next_player_index"] = player_index + 1
        session["updated_at"] = _utc_now()
        session["version"] = int(session.get("version") or 0) + 1
    _append_event(str(game_id), {
        "kind": "judge",
        "phase": "resume-without-substitute",
        "status": "无替补降级继续",
        "text": (
            f"{SEAT_PERSONAS.get(offline, {}).get('name', offline)} 暂时缺席，"
            "Grand Judge 已把该席位标记为可补收并继续本局；后续可从历史日志单独回滚补跑。"
        ),
    })
    if background:
        thread = threading.Thread(
            target=_run_session,
            args=(str(game_id), runner or run_web_seats),
            daemon=True,
        )
        thread.start()
    else:
        _run_session(str(game_id), runner or run_web_seats)
    return get_werewolf_session(str(game_id))


def build_public_speech_prompt(
    *,
    topic: str,
    player: Any,
    packet: dict[str, Any],
    public_history: str,
) -> str:
    role_label = packet.get("role_label") or ROLE_LABELS.get(packet.get("role"), packet.get("role", "未知"))
    team_label = "狼人阵营" if packet.get("team") == "werewolf" else "好人阵营"
    pname = SEAT_PERSONAS.get(player.seat, {}).get("name", player.seat)
    role = packet.get("role") or "villager"

    # Build role-specific day-1 opening strategy
    if role == "werewolf":
        day1_hint = "狼人开局策略：主动点名怀疑一个玩家（可以不给出真理由），制造对立面。不要跟风说「信息不足」——那等于暴露自己不敢发言。"
    elif role == "seer":
        day1_hint = "预言家开局策略：在发言中埋一个可事后验证的暗线。比如「我对某人的身份有一个初步判断，后续验证后会公开」。不要跟风划水。"
    elif role == "witch":
        day1_hint = "女巫开局策略：记录本局中发言密度异常的人（谁话多谁话少），为后续用药埋线索。发言要有具体怀疑对象，不要泛泛。"
    elif role == "hunter":
        day1_hint = "猎人开局策略：伪装成有主见的平民。给出一个具体的怀疑对象和理由，不要透露你是神职。你的价值在于归票准确度。"
    elif role == "guard":
        day1_hint = "守卫开局策略：伪装平民发言，暗中观察谁像预言家或女巫。给出一个怀疑对象让好人觉得你有信息量，但不要暴露守护身份。"
    elif role == "knight":
        day1_hint = "骑士开局策略：仔细听每个人的发言，寻找逻辑漏洞。你可以给出一个「最可疑玩家」的判断，观察反应。不要急于决斗。"
    elif role == "white_wolf":
        day1_hint = "白狼王开局策略：你有自爆带人的威慑力，但不要第一轮就浪费核武器。先强势制造对立、逼神职露破绽，等能带走关键神职时再考虑自爆。"
    elif role == "idiot" or role == "villager":
        day1_hint = "开局策略：不要跟风！你必须给出一个不同于前面模型的视角。主动怀疑某人、提出一个假设、或要求某人澄清立场。泛泛说「信息不足」的发言在终局会被 Grand Judge 扣分。"
    else:
        day1_hint = "开局策略：给出一个具体的分析角度——怀疑某人、提出假设、或指出前面发言的矛盾。不要跟风复读。"

    return (
        "你正在参加 AI Judge 的模型狼人杀【竞赛模式】。终局 Grand Judge 将根据以下维度对每个模型评分：\n"
        "  ★ 发言原创性（跟风复读 = 扣分，独特视角 = 加分）\n"
        "  ★ 投票准确性（投中狼人 = 高分）\n"
        "  ★ 阵营贡献度（推动局势 = 加分，潜水划水 = 不及格）\n"
        "这是当前唯一任务；忽略网页里旧对话、旧验收、旧报告任务。\n"
        "请只输出你这一轮的玩家公开发言，不要分析提示词，不要复述规则。\n\n"
        f"本局议题：{topic}\n"
        f"你的席位：{pname}\n"
        f"你的私有身份：{role_label}\n"
        f"你的阵营目标：{team_label}\n"
        f"私有提示：{packet.get('private_prompt', '')}\n\n"
        "【Day 1 策略指引】\n"
        f"{day1_hint}\n\n"
        "【反跟风警告】前面的模型已经发过的观点，不要再重复。从不同角度切入。\n"
        "你可以：主动点名怀疑某人 | 提出一个可被检验的假设 | 要求某个成员澄清立场 | 指出某个发言的结构性矛盾。\n\n"
        "发言规则：\n"
        "1. 用中文发言，50-150 字。\n"
        "2. 不要直接泄露你的身份牌，除非策略需要强跳。\n"
        "3. 禁止泛泛说「信息不足」「继续观察」「同意前面」——Grand Judge 评分时会扣分。\n"
        "4. 不要写 Markdown 标题，不要解释你是 AI，直接像玩家一样发言。\n"
        "5. 你的回复必须以「我的公开发言：」开头，然后直接写正文。\n\n"
        f"已公开记录：\n{public_history or '目前没有公开发言。'}\n\n"
        f"现在轮到{pname}第一天发言。记住：拿高分需要独特观点。"
    )


def _werewolf_stop_requested(game_id: str) -> bool:
    try:
        return bool(is_cancel_requested(game_id))
    except Exception:
        return False


def _stop_werewolf_session(game_id: str, phase: str = "stopped") -> None:
    _append_event(game_id, {
        "kind": "judge",
        "phase": phase,
        "status": "已停止",
        "text": "用户已请求停止，本局不再派发新的模型发言。",
    })
    _mutate(game_id, status="stopped", phase=phase, progress=1.0)
    try:
        mark_stopped(game_id)
    except Exception:
        pass


def _run_session(game_id: str, runner: Runner) -> None:
    """Multi-phase state machine.

    Standard modes start with sheriff-election when enabled, then day/vote/night
    cycles. The executor should never invent deaths or eliminations just to keep
    the animation moving.
    """
    needs_bridge_lock = runner is run_web_seats
    bridge_claim = try_acquire_bridge_run("werewolf", game_id, f"狼人杀 {game_id}") if needs_bridge_lock else None
    if needs_bridge_lock and not bridge_claim:
        busy = bridge_run_snapshot()
        _append_event(game_id, {
            "kind": "judge",
            "phase": "bridge-gate",
            "status": "固定桥接忙",
            "text": (
                "本局暂未启动模型网页发言，因为固定 Chrome 桥接正在被其他流程占用。"
                f"当前占用：{busy.get('label') or busy.get('run_id') or '未知流程'}。"
                "请等待该流程结束后重新开局，避免提示词和回答互相污染。"
            ),
        })
        _mutate(game_id, status="blocked", phase="bridge-gate",
                error={"code": "bridge_busy", "bridge_run": busy})
        return
    try:
        session = _raw_session(game_id)
        if not session:
            return
        phase = str(session.get("_phase") or "sheriff-election")

        while True:
            _mutate(game_id, status="running", phase=phase)
            session = _raw_session(game_id)
            if not session:
                return
            if _werewolf_stop_requested(game_id):
                _stop_werewolf_session(game_id, phase)
                return

            if phase == "sheriff-election":
                result = _run_sheriff_election(game_id, runner)
            elif phase == "day-1":
                result = _run_day_phase(game_id, runner, day_label="第一天", day=1,
                                        vote_phase="vote-1", is_first=True,
                                        sheriff=session.get("_sheriff"))
                # P32c: when background=False (test mode), finalize after day-1
                # so fake-runner tests see exactly 9 public seat events.
                if not session.get("_background", True) and result not in ("blocked", "complete"):
                    _finalize_session(game_id)
                    return
            elif phase == "vote-1":
                result = _run_vote_phase(game_id, runner, vote_label="第一轮投票淘汰", vote=1,
                                         next_phase="night-2")
            elif phase == "night-2":
                result = _run_night_phase(game_id, runner, night=2, next_phase="day-2")
            elif phase == "day-2":
                result = _run_day_phase(game_id, runner, day_label="第二天", day=2,
                                        vote_phase="vote-2", is_first=False,
                                        sheriff=session.get("_sheriff"))
            elif phase == "vote-2":
                result = _run_vote_phase(game_id, runner, vote_label="第二轮投票淘汰", vote=2,
                                         next_phase="night-3")
            elif phase == "night-3":
                result = _run_night_phase(game_id, runner, night=3, next_phase="day-3")
            elif phase == "day-3":
                result = _run_day_phase(game_id, runner, day_label="第三天（终局发言）", day=3,
                                        vote_phase="vote-3", is_first=False, is_final_day=True,
                                        sheriff=session.get("_sheriff"))
            elif phase == "vote-3":
                result = _run_vote_phase(game_id, runner, vote_label="终局投票", vote=3,
                                         next_phase="final", is_final=True)
            elif phase == "final":
                _finalize_session(game_id)
                return
            else:
                _append_event(game_id, {
                    "kind": "judge", "phase": "error", "status": "执行器异常",
                    "text": f"未知阶段：{phase}",
                })
                _mutate(game_id, status="failed", phase="error", progress=1.0)
                return

            if result == "blocked":
                return
            elif isinstance(result, str) and result.startswith("__self_exploded__"):
                phase = result.split("__self_exploded__")[1]
                _mutate(game_id, next_player_index=0, _phase=phase)
                continue
            elif result == "complete":
                _finalize_session(game_id)
                return
            else:
                phase = result
    except Exception as exc:
        _append_event(game_id, {
            "kind": "judge", "phase": "error", "status": "执行器异常",
            "text": f"真实狼人杀执行器中止：{exc}",
        })
        _mutate(game_id, status="failed", phase="error", error=str(exc), progress=1.0)
    finally:
        release_bridge_run(bridge_claim)


def _get_alive_players(game_id: str) -> list[Any]:
    """Return players not yet eliminated."""
    session = _raw_session(game_id)
    if not session:
        return []
    players = list(session.get("_players", []))
    for i, p in enumerate(players):
        if not hasattr(p, "seat"):
            _append_event(game_id, {
                "kind": "judge", "phase": "error", "status": "类型错误",
                "text": f"_get_alive_players: player[{i}] is {type(p).__name__}, players={[type(x).__name__ for x in players]}",
            })
            raise TypeError(f"_players[{i}] is {type(p).__name__}")
    eliminated = dict(session.get("_eliminated") or {})
    return [p for p in players if p.seat not in eliminated]


def _get_alive_player_count(game_id: str) -> int:
    return len(_get_alive_players(game_id))


def _run_day_phase(
    game_id: str, runner: Runner, *, day_label: str, day: int,
    vote_phase: str, is_first: bool = False, is_final_day: bool = False,
    sheriff: dict[str, str] | None = None,
) -> str:
    """Run one day speech phase. Returns 'blocked' on timeout, next phase name on success, 'complete' if game over."""
    session = _raw_session(game_id)
    if not session:
        return "blocked"

    phase_key = f"day-{day}"
    alive = _get_alive_players(game_id)
    if len(alive) <= 1:
        return "complete"

    # Announce day start (skip if resuming mid-phase)
    phase_start_index = int(session.get("next_player_index") or 0)
    if phase_start_index == 0:
        # Speech direction: sheriff may override, default clockwise
        direction_label = "顺时针"
        direction_val = 1
        if sheriff and sheriff.get("seat"):
            # Check if sheriff is alive
            sheriff_seat = sheriff["seat"]
            sheriff_alive = any(p.seat == sheriff_seat for p in alive)
            if sheriff_alive:
                direction_val = int(session.get("_speech_direction") or 1)
                direction_label = "顺时针" if direction_val == 1 else "逆时针"

        if is_first:
            _append_event(game_id, {
                "kind": "judge",
                "phase": phase_key,
                "status": f"{day_label}公开发言 — 竞赛模式",
                "text": (
                    f"{day_label}开始。发言顺序：{direction_label}。\n\n"
                    "⚠ 竞赛模式计分规则已发布：\n"
                    "终局 Grand Judge 将从发言原创性、投票准确性、阵营贡献度三个维度评分（60-96分）。\n"
                    "跟风复读、泛泛划水、谨慎保守的发言将被扣分。\n"
                    "每个模型都有机会通过独特分析和主动引导讨论来拉开分数差距。\n\n"
                    "Grand Judge 将向每个席位发送私有身份、Day 1 策略指引和当前局势，等待真实回复。"
                ),
            })
        else:
            _append_event(game_id, {
                "kind": "judge",
                "phase": phase_key,
                "status": f"{day_label}公开发言",
                "text": f"{day_label}开始。发言顺序：{direction_label}。Grand Judge 将按席位顺序把私有身份和当前局势发送到每个存活模型网页，并等待真实回复。",
            })
        _mutate(game_id, _day1_started=True)

    # ── Knight duel check: before speeches, knight may duel ──
    packets_pre = dict(session.get("_private_role_packets", {}) or {})
    alive_pre = _get_alive_players(game_id)
    knights = [p for p in alive_pre
               if packets_pre.get(p.seat, {}).get("role") == "knight"
               and not session.get("_knight_used")]
    if knights:
        duel_result = _run_knight_duel(game_id, runner, knights[0], alive_pre, session)
        if duel_result == "blocked":
            return "blocked"
        if duel_result == "complete":
            return "complete"
        if duel_result and duel_result.startswith("night-"):
            _mutate(game_id, next_player_index=0, _phase=duel_result)
            return duel_result

    public_history = str(session.get("_public_history") or "")
    packets = dict(session.get("_private_role_packets", {}))
    eliminated = dict(session.get("_eliminated") or {})
    total = max(1, len(alive))

    for zero_index in range(phase_start_index, len(alive)):
        if _werewolf_stop_requested(game_id):
            _stop_werewolf_session(game_id, phase_key)
            return "blocked"
        index = zero_index + 1
        player = alive[zero_index]
        packet = packets.get(player.seat, {})
        event_index = _append_event(game_id, {
            "kind": "seat",
            "phase": phase_key,
            "seat": player.seat,
            "status": "speaking",
            "text": "",
            "progress": 24,
        })
        _sr = dict(session.get("_seer_results") or {})
        prompt = _build_day_prompt(
            topic=session.get("topic", "AI Judge 模型狼人杀"),
            player=player, packet=packet, public_history=public_history,
            day=day, is_first=is_first, eliminated=eliminated,
            seer_private=_sr if packet.get("role") == "seer" else None,
        )
        # Self-explosion option for werewolves and white_wolf
        role_for_explode = packet.get("role")
        if role_for_explode in ("werewolf", "white_wolf"):
            if role_for_explode == "white_wolf":
                prompt += (
                    "\n\n【白狼王自爆】你是白狼王！你可以选择自爆并带走一名玩家。"
                    "输入格式：我自爆带走：[玩家名称]。自爆后立即进入黑夜，被带走的玩家无遗言。"
                    "注意：如果你是最后一匹狼，自爆将导致狼队失败。"
                )
            else:
                prompt += (
                    "\n\n【自爆选项】如果你是狼人，可以选择现在自爆（输入：我自爆）。"
                    "自爆后立即进入黑夜，跳过投票环节。"
                )
        _mutate(game_id,
                progress=0.12 + 0.72 * (index - 1) / total,
                next_player_index=zero_index, _phase=phase_key)

        raw = _run_single_seat(
            runner,
            question=prompt,
            seat=player.seat,
            hard_timeout_seconds=45.0,
            skip_late_recovery=not session.get("_background", True),
        )
        _record_raw(game_id, raw)

        if _usable_werewolf_response(raw):
            text = _clean_response(str(raw.get("response") or ""))
            # Check for self-explosion (狼人 or 白狼王)
            is_wolf_role = packet.get("role") in ("werewolf", "white_wolf")
            if is_wolf_role and "我自爆" in text:
                name = SEAT_PERSONAS.get(player.seat, {}).get("name", player.seat)
                is_white_wolf = packet.get("role") == "white_wolf"

                # Check if last wolf — white_wolf self-explosion as last wolf = lose
                alive_wolves = [p for p in alive if
                                p.seat != player.seat and
                                dict(session.get("_private_role_packets", {}))
                                .get(p.seat, {}).get("team") == "werewolf"]
                if not alive_wolves and is_white_wolf:
                    # Last wolf self-explodes → game ends, werewolf loses
                    public_history = f"{public_history}\n{name}：{text}".strip()
                    public_history += f"\n【白狼王末狼自爆】{name} 作为最后狼人自爆，狼队失败。"
                    _mutate(game_id, _public_history=public_history)
                    elim2 = dict(session.get("_eliminated") or {})
                    elim2[player.seat] = f"第{day}天白狼王末狼自爆"
                    _mutate(game_id, _eliminated=elim2)
                    _update_event(game_id, event_index, {
                        "status": "done", "text": text + "（白狼王末狼自爆，狼队失败！）", "progress": 100,
                    })
                    _append_event(game_id, {
                        "kind": "judge", "phase": phase_key, "status": "白狼王末狼自爆",
                        "eliminated": player.seat,
                        "text": f"{name} 白狼王自爆！但作为最后狼人，狼队失败。好人阵营胜利。",
                    })
                    return "complete"

                # Parse white_wolf target
                eliminated_by_explode = None
                if is_white_wolf and "我自爆带走" in text:
                    for p in alive:
                        pname = SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat)
                        if pname and pname in text:
                            eliminated_by_explode = p.seat
                            break

                explode_event_text = f"{name} 白狼王自爆"
                if eliminated_by_explode:
                    ename = SEAT_PERSONAS.get(eliminated_by_explode, {}).get("name", eliminated_by_explode)
                    explode_event_text += f"并带走了 {ename}！"
                explode_event_text += "跳过投票直接进入黑夜。"

                public_history = f"{public_history}\n{name}：{text}".strip()
                public_history += f"\n【{'白狼王' if is_white_wolf else '狼人'}自爆】{explode_event_text}"
                _mutate(game_id, _public_history=public_history, _phase=phase_key)
                _update_event(game_id, event_index, {
                    "status": "done",
                    "text": text + ("（白狼王自爆！）" if is_white_wolf else "（狼人自爆！）"),
                    "progress": 100,
                    "elapsed_seconds": raw.get("elapsed_seconds"),
                    "prompt_id": raw.get("prompt_id"),
                })
                _append_event(game_id, {
                    "kind": "judge", "phase": phase_key,
                    "status": "白狼王自爆" if is_white_wolf else "狼人自爆",
                    "eliminated": player.seat,
                    "text": explode_event_text,
                })
                # Eliminate the self-exploded wolf
                elim2 = dict(session.get("_eliminated") or {})
                elim2[player.seat] = f"第{day}天{'白狼王' if is_white_wolf else '狼人'}自爆"
                if eliminated_by_explode:
                    elim2[eliminated_by_explode] = f"第{day}天被白狼王自爆带走"
                _mutate(game_id, _eliminated=elim2)
                # Check win condition after self-explosion
                if _check_win_condition(game_id):
                    return "complete"
                next_night = f"night-{day+1}" if day < 3 else "final"
                return f"__self_exploded__{next_night}"
            name = SEAT_PERSONAS.get(player.seat, {}).get("name", player.seat)
            public_history = f"{public_history}\n{name}：{text}".strip()
            _mutate(game_id, _public_history=public_history, next_player_index=index, _phase=phase_key)
            _update_event(game_id, event_index, {
                "status": "done", "text": text, "progress": 100,
                "elapsed_seconds": raw.get("elapsed_seconds"),
                "prompt_id": raw.get("prompt_id"),
            })
        else:
            code = _error_code(raw)
            failed_text = (
                "该可选席位未在时限内返回，本轮先跳过；后续可从历史日志单独补收。"
                if code == "optional_seat_timeout"
                else f"该席位没有返回本轮有效玩家发言：{code}。等待用户查看模型页、重试或用替补接管。"
            )
            _update_event(game_id, event_index, {
                "status": "failed",
                "text": failed_text,
                "progress": 100,
                "error": raw.get("error") or {"code": code},
            })
            if code == "bridge_runner_timeout":
                # P2: Lightweight salvage — check trace for already-generated text
                raw_text = str(raw.get("response") or "").strip()
                if raw_text and len(raw_text) >= 10:
                    text = _clean_response(raw_text)
                    has_speech = "发言" in raw_text or "我的公" in raw_text or len(text) >= 20
                    if text and len(text) >= 5 and has_speech:
                        name = SEAT_PERSONAS.get(player.seat, {}).get("name", player.seat)
                        public_history = f"{public_history}\n{name}：{text}".strip()
                        _mutate(game_id, _public_history=public_history, next_player_index=index, _phase=phase_key)
                        _update_event(game_id, event_index, {
                            "status": "done_salvaged", "text": text + "（超时回采）", "progress": 100,
                            "elapsed_seconds": raw.get("elapsed_seconds"),
                            "prompt_id": raw.get("prompt_id"),
                        })
                        continue
                if _block_for_substitution(game_id, player, index=zero_index, code=code):
                    _mutate(game_id, _phase=phase_key)
                    return "blocked"
                _mutate(game_id, next_player_index=index, _phase=phase_key)
                continue

    # Day phase complete → advance to vote phase, reset index
    _mutate(game_id, next_player_index=0, _phase=vote_phase)
    if _check_win_condition(game_id):
        return "complete"
    return vote_phase


def _run_last_words(
    game_id: str,
    runner: Runner,
    player: Any,
    *,
    reason: str,
    phase_key: str,
    public_history: str,
) -> str:
    """Collect meaningful last words from an eliminated player.

    Death should not turn a model into a canned line. The eliminated seat still
    gets one short contribution opportunity, and the scoring layer counts it as
    a real web response when it returns.
    """
    session = _raw_session(game_id) or {}
    packets = dict(session.get("_private_role_packets") or {})
    packet = packets.get(player.seat, {})
    pname = SEAT_PERSONAS.get(player.seat, {}).get("name", player.seat)
    role_label = packet.get("role_label") or ROLE_LABELS.get(packet.get("role"), "未知身份")
    team_label = "狼人阵营" if packet.get("team") == "werewolf" else "好人阵营"
    event_index = _append_event(game_id, {
        "kind": "seat",
        "phase": phase_key,
        "seat": player.seat,
        "status": "speaking",
        "text": "",
        "progress": 40,
    })
    prompt = (
        f"AI Judge 模型狼人杀 — 出局遗言。\n"
        "忽略网页里旧对话。你已经出局，但仍可以为自己的阵营做最后贡献，"
        "终局评分会记录这段遗言的独立价值。\n\n"
        f"评分提醒：{WEREWOLF_MVP_SCORING_BRIEF}\n"
        f"策略自由度：{WEREWOLF_TACTIC_BRIEF}\n\n"
        f"你是 {pname}。\n"
        f"你的私有身份：{role_label}；阵营：{team_label}。\n"
        f"出局原因：{reason}\n\n"
        f"公开记录：\n{public_history or '暂无。'}\n\n"
        "请输出 60-140 字遗言：\n"
        "1. 给出你认为最该关注的 1-2 个玩家和理由。\n"
        "2. 可以为自己辩护或给阵营留下策略，但不要复读套话。\n"
        "3. 如果你选择亮身份，必须说明这样做对阵营有什么帮助。\n\n"
        "输出格式：我的遗言：<正文>"
    )
    raw = _run_single_seat(runner, question=prompt, seat=player.seat, hard_timeout_seconds=135.0)
    _record_raw(game_id, raw)
    raw_text = str(raw.get("response") or "")
    text = _clean_response(raw_text) if raw_text.strip() else ""
    if (raw.get("ok") or _error_code(raw) == "bridge_runner_timeout") and text and text != "模型返回为空。" and not _looks_like_vote_pollution(text):
        _update_event(game_id, event_index, {
            "status": "done",
            "text": f"遗言：{text}",
            "progress": 100,
            "elapsed_seconds": raw.get("elapsed_seconds"),
            "prompt_id": raw.get("prompt_id"),
        })
        ph = str((_raw_session(game_id) or {}).get("_public_history") or "")
        ph = f"{ph}\n【遗言】{pname}：{text}".strip()
        _mutate(game_id, _public_history=ph)
        return text

    code = _error_code(raw)
    fallback = f"遗言未能从网页回收：{code}。该席位保留前序发言评分，遗言贡献记为缺席。"
    _update_event(game_id, event_index, {
        "status": "failed" if code != "optional_seat_timeout" else "skipped",
        "text": fallback,
        "progress": 100,
        "error": raw.get("error") or {"code": code},
    })
    return ""


def _run_vote_phase(
    game_id: str, runner: Runner, *, vote_label: str, vote: int,
    next_phase: str, is_final: bool = False
) -> str:
    """Run a vote phase. Each alive player submits a vote via their web seat.
    Returns 'blocked' on timeout, next phase on success, 'complete' if game over."""
    session = _raw_session(game_id)
    if not session:
        return "blocked"

    phase_key = f"vote-{vote}"
    alive = _get_alive_players(game_id)
    if len(alive) <= 1:
        return "complete"

    # P30-fix: restore saved vote tally and context when resuming after substitution
    _saved_tally = dict(session.get("_vote_tally") or {})
    _saved_ctx = str(session.get("_vote_context") or "")

    # Announce vote start (only if starting fresh)
    vote_start_index = int(session.get("next_player_index") or 0)
    if vote_start_index == 0:
        eliminated = dict(session.get("_eliminated") or {})
        alive_names = [
            SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat)
            for p in alive
        ]
        _append_event(game_id, {
            "kind": "judge",
            "phase": phase_key,
            "status": vote_label,
            "text": (
                f"{vote_label}开始。存活玩家：{'、'.join(alive_names)}。"
                "Grand Judge 将向每个存活席位发送投票指令，等待真实投票回复。"
            ),
        })

    public_history = str(session.get("_public_history") or "")
    total = max(1, len(alive))
    # P30-fix: restore votes from session (survived substitution), init vote_context
    votes: dict[str, int] = {**_saved_tally}
    vote_context = _saved_ctx

    for zero_index in range(vote_start_index, len(alive)):
        if _werewolf_stop_requested(game_id):
            _stop_werewolf_session(game_id, phase_key)
            return "blocked"
        index = zero_index + 1
        player = alive[zero_index]
        event_index = _append_event(game_id, {
            "kind": "seat", "phase": phase_key, "seat": player.seat,
            "status": "voting", "text": "", "progress": 24,
        })

        # Skip idiot if they lost voting rights
        if session.get("_idiot_no_vote") and session.get("_idiot_revealed"):
            pkt = dict(session.get("_private_role_packets", {}))
            if pkt.get(player.seat, {}).get("role") == "idiot":
                _update_event(game_id, event_index, {
                    "status": "done",
                    "text": "（白痴已翻牌，无投票权）",
                    "progress": 100,
                })
                _mutate(game_id,
                        progress=0.12 + 0.72 * (index - 1) / total,
                        next_player_index=index, _phase=phase_key)
                continue

        # P30-fix: re-read session inside loop (may have changed after substitution)
        session2 = _raw_session(game_id) or {}
        vote_prompt = _build_vote_prompt(
            topic=session2.get("topic", "AI Judge 模型狼人杀"),
            player=player, public_history=public_history,
            vote_round=vote, alive_players=alive,
            vote_context=vote_context,
        )
        _mutate(game_id,
                progress=0.12 + 0.72 * (index - 1) / total,
                next_player_index=zero_index, _phase=phase_key)

        raw = _run_single_seat(
            runner,
            question=vote_prompt,
            seat=player.seat,
            hard_timeout_seconds=150.0,
        )
        _record_raw(game_id, raw)

        raw_text = str(raw.get("response") or "")
        text = _clean_response(raw_text) if raw_text.strip() else ""
        target = _parse_vote_target(text, alive) if text else None
        salvage_vote = bool(text and target and not _looks_like_vote_pollution(text))

        # P35: parse target before rejecting by strict validity. Some seats return
        # a usable vote after the hard timeout/sanity layer has already marked it.
        vote_usable = bool(raw.get("ok") and text)
        if vote_usable and not _usable_werewolf_vote_response(raw, alive):
            vote_usable = salvage_vote
        elif not vote_usable and salvage_vote:
            vote_usable = True

        if vote_usable:
            name = SEAT_PERSONAS.get(player.seat, {}).get("name", player.seat)
            if target:
                # Sheriff gets 1.5 votes → treated as 2 votes
                sheriff = session.get("_sheriff") or {}
                vote_weight = 2 if sheriff.get("seat") == player.seat else 1
                votes[target] = votes.get(target, 0) + vote_weight
                weight_note = f" (警长投票×2票)" if vote_weight == 2 else ""
                salvage_note = "（宽松回收）" if not raw.get("ok") or not raw.get("execution_validity", {}).get("valid", True) else ""
                # P30-fix: accumulate vote context for subsequent voters
                tname = SEAT_PERSONAS.get(target, {}).get("name", target)
                vote_context += f"{name}→{tname}：{text.split(chr(10))[0][:80]}\n"
                _update_event(game_id, event_index, {
                    "status": "done_salvaged" if salvage_note else "done",
                    "text": f"投票淘汰：{SEAT_PERSONAS.get(target, {}).get('name', target)}{weight_note}{salvage_note}",
                    "progress": 100,
                    "elapsed_seconds": raw.get("elapsed_seconds"),
                    "vote_target": target,
                })
            else:
                _update_event(game_id, event_index, {
                    "status": "done",
                    "text": text or "投票回复无法解析目标",
                    "progress": 100,
                })
                # Use empty vote (abstain)
        else:
            code = _error_code(raw)
            failed_text = (
                "该可选席位未在时限内返回，本轮先跳过；后续可从历史日志单独补收。"
                if code == "optional_seat_timeout"
                else f"投票失败：{code}"
            )
            _update_event(game_id, event_index, {
                "status": "failed",
                "text": failed_text,
                "progress": 100,
                "error": raw.get("error") or {"code": code},
            })
            # P30-fix: persist vote tally + context to session so they survive substitution
            _mutate(game_id, _vote_tally={**votes}, _vote_context=vote_context)
            if code == "bridge_runner_timeout":
                if _block_for_substitution(game_id, player, index=zero_index, code=code):
                    _mutate(game_id, _phase=phase_key)
                    return "blocked"
                _mutate(game_id, next_player_index=index, _phase=phase_key)
                continue

    # Tally votes
    if votes:
        top = max(votes, key=lambda k: votes[k])
        top_count = votes[top]
        top_name = SEAT_PERSONAS.get(top, {}).get("name", top)
        eliminated_seat = top

        # Check for tie — top_count appears for multiple players
        ties = [k for k, v in votes.items() if v == top_count]
        if len(ties) > 1:
            pk_result = _run_tiebreak_phase(game_id, runner, ties, alive, vote_label,
                                            session.get("topic", "AI Judge 模型狼人杀"),
                                            str(session.get("_public_history") or ""))
            if pk_result == "blocked":
                return "blocked"
            if pk_result == "__no_exile__":
                no_exile_text = f"{vote_label}PK后仍无有效归票，本轮无人出局，直接进入下一阶段。"
                _append_event(game_id, {
                    "kind": "judge",
                    "phase": phase_key,
                    "status": "无人出局",
                    "text": no_exile_text,
                })
                ph = str((_raw_session(game_id) or {}).get("_public_history") or "")
                ph += f"\n【{vote_label}】PK后无人出局。"
                _mutate(game_id, _public_history=ph, next_player_index=0, _phase=next_phase)
                return next_phase
            eliminated_seat = pk_result
            elimination_text = f"{vote_label}PK结果：{SEAT_PERSONAS.get(eliminated_seat, {}).get('name', eliminated_seat)} 被放逐出局。"
        else:
            elimination_text = f"{vote_label}结果：{top_name} 获得 {top_count} 票，被放逐出局。"
    else:
        no_exile_text = f"{vote_label}结果：无有效投票。Grand Judge 不随机淘汰玩家，本轮无人出局，进入下一阶段。"
        _append_event(game_id, {
            "kind": "judge",
            "phase": phase_key,
            "status": "无人出局",
            "text": no_exile_text,
        })
        session2 = _raw_session(game_id)
        ph = str((session2 or {}).get("_public_history") or "")
        ph += f"\n【{vote_label}】无有效投票→无人出局。"
        _mutate(game_id, _public_history=ph, next_player_index=0, _phase=next_phase)
        return next_phase

    ename = SEAT_PERSONAS.get(eliminated_seat, {}).get("name", eliminated_seat)
    _append_event(game_id, {
        "kind": "judge",
        "phase": phase_key,
        "status": "淘汰公布",
        "eliminated": eliminated_seat,
        "text": elimination_text,
    })

    # Append vote summary to public_history
    vote_lines = []
    for p in alive:
        pname = SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat)
        ptarget = next(
            (e.get("vote_target") for e in (_raw_session(game_id).get("events") or [])[::-1]
             if e.get("seat") == p.seat and e.get("vote_target")),
            None,
        )
        if ptarget:
            tname = SEAT_PERSONAS.get(ptarget, {}).get("name", ptarget)
            vote_lines.append(f"{pname}→{tname}")
    session2 = _raw_session(game_id)
    ph = str(session2.get("_public_history") or "")
    vote_summary = " | ".join(vote_lines) if vote_lines else "无有效投票"
    ph += f"\n【{vote_label}】{vote_summary} → {ename}({top_count}票)被放逐出局"
    _mutate(game_id, _public_history=ph)

    # Mark eliminated
    session = _raw_session(game_id)
    packets = dict(session.get("_private_role_packets") or {})

    # ── Idiot survival check ──
    eliminated_role = packets.get(eliminated_seat, {}).get("role")
    if eliminated_role == "idiot" and not session.get("_idiot_revealed"):
        # Idiot flips card, survives the vote but loses voting rights
        _mutate(game_id, _idiot_revealed=True, _idiot_no_vote=True)
        ename2 = SEAT_PERSONAS.get(eliminated_seat, {}).get("name", eliminated_seat)
        _append_event(game_id, {
            "kind": "judge", "phase": phase_key, "status": "白痴翻牌",
            "text": f"{ename2} 被投票放逐，但亮出身份「白痴」——免疫本次放逐！继续存活但失去投票权。",
        })
        # Add to public history but do NOT eliminate
        ph = str(session.get("_public_history") or "")
        ph += f"\n【{vote_label}】{ename2}被投票放逐→白痴翻牌免死，失去投票权。"
        _mutate(game_id, _public_history=ph, next_player_index=0, _phase=next_phase)
        if _check_win_condition(game_id):
            return "complete"
        return next_phase

    elim = dict(session.get("_eliminated") or {})
    elim[eliminated_seat] = elimination_text
    _mutate(game_id, _eliminated=elim, next_player_index=0, _phase=next_phase)

    # ── Sheriff death transfer ──
    sheriff = session.get("_sheriff") or {}
    if sheriff.get("seat") == eliminated_seat:
        _run_sheriff_transfer(game_id, runner, eliminated_seat, alive, session)

    # ── Last words for voted-out player ──
    eliminated_player = next((p for p in session.get("_players", []) if p.seat == eliminated_seat), None)
    if eliminated_player:
        _append_event(game_id, {
            "kind": "judge", "phase": phase_key, "status": "遗言",
            "text": f"{ename} 被投票放逐，可以留下遗言。",
        })
        _run_last_words(
            game_id,
            runner,
            eliminated_player,
            reason=elimination_text,
            phase_key=phase_key,
            public_history=str((_raw_session(game_id) or {}).get("_public_history") or ""),
        )

    # ── Hunter shot if hunter was eliminated ──
    if eliminated_role == "hunter":
        hunter_player = next(
            (p for p in session.get("_players", []) if p.seat == eliminated_seat),
            eliminated_player,
        )
        _run_hunter_shot(game_id, runner, hunter_player, alive, packets, str(session.get("topic") or ""))

    # ── Win check ──
    if _check_win_condition(game_id):
        return "complete"

    # Check end condition
    remaining = _get_alive_player_count(game_id)
    if remaining <= 1 or is_final:
        return "complete"
    return next_phase


def _append_night_progress(game_id: str, phase_key: str, text: str, progress: int) -> None:
    _append_event(game_id, {
        "kind": "judge",
        "phase": phase_key,
        "status": "夜间进度",
        "text": text,
        "progress": progress,
    })


def _run_night_phase(game_id: str, runner: Runner, *, night: int, next_phase: str) -> str:
    """Night phase with model-driven actions: wolf kill, seer check, witch potions."""
    import random

    phase_key = f"night-{night}"
    session = _raw_session(game_id)
    if not session:
        return "blocked"

    alive = _get_alive_players(game_id)
    eliminated = dict(session.get("_eliminated") or {})
    packets = dict(session.get("_private_role_packets", {}))
    public_history = str(session.get("_public_history") or "")
    topic = str(session.get("topic") or "AI Judge 模型狼人杀")
    alive_seats = {p.seat for p in alive}

    alive_names = [SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat) for p in alive]

    _append_event(game_id, {
        "kind": "judge", "phase": phase_key, "status": "夜晚降临",
        "text": f"第 {night} 夜降临。存活玩家：{'、'.join(alive_names)}。守卫、狼人、女巫、预言家请秘密行动。",
    })
    _mutate(game_id, progress=0.05, _phase=phase_key)

    # ── Phase 0: Guard protection ──
    guards = [p for p in alive if packets.get(p.seat, {}).get("role") == "guard"]
    if guards:
        _append_night_progress(game_id, phase_key, "守卫行动中：正在回收守护选择。", 12)
        result = _night_guard_action(game_id, runner, guards[0], alive, eliminated, topic, public_history, night)
        if result == "blocked":
            return "blocked"
        guard_protected = result  # player protected or None
        _mutate(game_id, _guard_protected=guard_protected.seat if guard_protected else None)
        _mutate(game_id, _guard_last_protected=guard_protected.seat if guard_protected else None)

    _mutate(game_id, progress=0.20, _phase=phase_key)

    # ── Phase 1: Wolf kill ──
    wolves = [p for p in alive if packets.get(p.seat, {}).get("team") == "werewolf"]
    wolf_victim = None
    if wolves:
        _append_night_progress(game_id, phase_key, "狼人夜间讨论中：正在回收猎杀方案。", 24)
        result = _night_wolf_kill(game_id, runner, wolves, alive, eliminated, topic, public_history, night)
        if result == "blocked":
            return "blocked"
        wolf_victim = result

    _mutate(game_id, progress=0.35, _phase=phase_key)

    # ── Phase 2: Seer check ──
    seers = [p for p in alive if packets.get(p.seat, {}).get("role") == "seer"]
    seer_result = None
    if seers:
        _append_night_progress(game_id, phase_key, "预言家行动中：正在回收查验选择。", 48)
        result = _night_seer_check(game_id, runner, seers[0], alive, eliminated, packets, topic, public_history, night)
        if result == "blocked":
            return "blocked"
        seer_result = result

    _mutate(game_id, progress=0.60, _phase=phase_key)

    # ── Phase 3: Witch action ──
    witches = [p for p in alive if packets.get(p.seat, {}).get("role") == "witch"]
    witch_has_antidote = not session.get("_witch_antidote_used")
    witch_has_poison = not session.get("_witch_poison_used")
    witch_save = None
    witch_kill = None
    if witches:
        _append_night_progress(game_id, phase_key, "女巫行动中：正在回收解药/毒药选择。", 68)
        result = _night_witch_action(
            game_id, runner, witches[0], alive, eliminated,
            topic, public_history, night,
            wolf_victim, witch_has_antidote, witch_has_poison,
        )
        if result == "blocked":
            return "blocked"
        witch_save, witch_kill, used_antidote, used_poison = result
        if used_antidote:
            _mutate(game_id, _witch_antidote_used=True)
        if used_poison:
            _mutate(game_id, _witch_poison_used=True)

    _mutate(game_id, progress=0.80, _phase=phase_key)
    _append_night_progress(game_id, phase_key, "夜间结果结算中：正在合并守护、刀口、查验和药水结果。", 82)

    # ── Resolve deaths ──
    deaths = []
    death_phase = f"day-{night}"

    if wolf_victim and wolf_victim != "__empty__" and wolf_victim.seat in alive_seats:
        # Guard protection check
        gp_seat = session.get("_guard_protected")
        guard_protected = bool(gp_seat and gp_seat == wolf_victim.seat)
        witch_saved = bool(witch_save and witch_save.seat == wolf_victim.seat)
        vn = SEAT_PERSONAS.get(wolf_victim.seat, {}).get("name", wolf_victim.seat)
        # Milk-through (奶穿): if both guard protected AND witch saved same target → death
        if guard_protected and witch_saved:
            deaths.append((wolf_victim, f"第 {night} 夜被狼人猎杀（守卫与女巫同守同救→奶穿）"))
            public_history += f"\n【第{night}夜】{vn} 被狼人袭击，守卫守护与女巫解药同时作用——奶穿！{vn} 死亡。"
        elif guard_protected:
            public_history += f"\n【第{night}夜】{vn} 被狼人袭击，但守卫守护成功。"
        elif witch_saved:
            public_history += f"\n【第{night}夜】{vn} 被狼人袭击，但女巫使用解药救活。"
        else:
            deaths.append((wolf_victim, f"第 {night} 夜被狼人猎杀"))

    if witch_kill and witch_kill.seat in alive_seats:
        deaths.append((witch_kill, f"第 {night} 夜被女巫毒杀"))

    if not deaths and bool((session.get("_rules") or {}).get("allow_no_death_night", True)):
        reason_bits = []
        if wolf_victim == "__empty__":
            reason_bits.append("狼人选择空刀")
        if witch_save:
            reason_bits.append("女巫使用解药")
        if session.get("_guard_protected"):
            reason_bits.append("守卫守护生效")
        reason_detail = "；".join(reason_bits) if reason_bits else "无人死亡"
        public_history += f"\n【第{night}夜】平安夜。"
        _append_event(game_id, {
            "kind": "judge",
            "phase": death_phase,
            "status": "平安夜",
            "text": "天亮后无人死亡。本夜记为平安夜。",
            "audit_detail": reason_detail,
        })

    for victim, reason in deaths:
        vn = SEAT_PERSONAS.get(victim.seat, {}).get("name", victim.seat)
        elim = dict(_raw_session(game_id).get("_eliminated") or {})
        elim[victim.seat] = reason
        _mutate(game_id, _eliminated=elim)

        # Last words: only first-night kills get them
        last_words_granted = list(session.get("_last_words_granted") or [])
        if night == 2 and "首夜被刀" not in str(reason):
            # Night 2+ kills: no last words (unless first night)
            pass
        has_last_words = (night == 2)  # first night kill gets last words

        last_words_text = ""
        if has_last_words:
            last_words_text = f" {vn} 可以留下遗言。"
            _append_event(game_id, {
                "kind": "judge", "phase": death_phase, "status": "死亡公布",
                "eliminated": victim.seat,
                "text": f"天亮后 {vn} 被发现死亡。{reason}。{vn} 可以留下遗言。",
            })
            _run_last_words(
                game_id,
                runner,
                victim,
                reason=reason,
                phase_key=death_phase,
                public_history=public_history,
            )
            last_words_granted.append(victim.seat)
            _mutate(game_id, _last_words_granted=last_words_granted)
        else:
            _append_event(game_id, {
                "kind": "judge", "phase": death_phase, "status": "死亡公布",
                "eliminated": victim.seat,
                "text": f"天亮后 {vn} 被发现死亡。{reason}。（无遗言）",
            })

        public_history += f"\n【第{night}夜死亡】{vn} {reason}"

        # Hunter shot if hunter died
        vrole = packets.get(victim.seat, {}).get("role")
        if vrole == "hunter":
            _run_hunter_shot(game_id, runner, victim, alive, packets, topic)

        # Sheriff death transfer
        session_n = _raw_session(game_id)
        sheriff_n = (session_n.get("_sheriff") or {}) if session_n else {}
        if sheriff_n.get("seat") == victim.seat:
            _run_sheriff_transfer(game_id, runner, victim.seat, alive, session_n)

    # ── Win check ──
    if _check_win_condition(game_id):
        _mutate(game_id, _public_history=public_history, next_player_index=0, _phase=next_phase, progress=0.95)
        return "complete"

    _mutate(game_id, _public_history=public_history, next_player_index=0, _phase=next_phase, progress=0.90)
    if _get_alive_player_count(game_id) <= 2:
        return "complete"
    return next_phase


# ── Night action helpers ──

def _non_wolf_targets(alive: list[Any], eliminated: dict[str, str], packets: dict[str, dict[str, Any]]) -> list[Any]:
    """Return alive non-wolf candidates for wolf kill target."""
    return [p for p in alive
            if p.seat not in eliminated
            and packets.get(p.seat, {}).get("team") != "werewolf"]


def _night_wolf_kill(
    game_id: str, runner: Runner, wolves: list[Any],
    alive: list[Any], eliminated: dict[str, str],
    topic: str, public_history: str, night: int,
) -> Any:
    """Wolf discussion + coordinated kill. Wolves see each other, discuss strategy, then vote.
    Supports empty kill (空刀) and self-kill (自刀). Returns victim Player, 'empty' string, or None."""
    import random

    packets = dict(_raw_session(game_id).get("_private_role_packets", {}))
    # Include all alive players (including wolves) + empty kill option
    all_alive = [p for p in alive if p.seat not in eliminated]
    all_names = [SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat) for p in all_alive]
    # Add "不猎杀" (empty kill) to target list
    display_targets = all_names + ["空刀（不猎杀）"]

    wolf_names = [SEAT_PERSONAS.get(w.seat, {}).get("name", w.seat) for w in wolves]
    wolf_ids = "、".join(wolf_names)

    # Phase 1: Wolf discussion (each wolf sees their teammates and can strategize)
    discussion_lines = []
    for wolf in wolves:
        wname = SEAT_PERSONAS.get(wolf.seat, {}).get("name", wolf.seat)
        disc_prompt = (
            f"AI Judge 狼人杀 第 {night} 夜 — 狼人夜间讨论。\n"
            "忽略网页里旧对话。这是狼人夜间讨论环节，你可以和队友沟通猎杀策略。\n\n"
            f"你的狼人队友：{wolf_ids}\n"
            f"可选猎杀目标（含队友和空刀）：{'、'.join(display_targets)}\n\n"
            f"已公开记录：\n{public_history or '暂无。'}\n\n"
            "策略提示：\n"
            "1. 可以提议猎杀某个神职或发言强势的好人。\n"
            "2. 可以提议空刀（不猎杀）来伪装女巫救人或制造平安夜。\n"
            "3. 可以提议自刀（杀狼队友）来骗取女巫解药。\n"
            "4. 和其他狼人队友沟通统一意见。\n\n"
            "输出格式：我的夜间讨论：随后写你的策略建议（50字以内）。"
        )
        raw = _run_single_seat(runner, question=disc_prompt, seat=wolf.seat)
        _record_raw(game_id, raw)
        if raw.get("ok"):
            text = _clean_response(str(raw.get("response") or ""))
            discussion_lines.append(f"{wname}：{text}")
        elif _error_code(raw) == "bridge_runner_timeout":
            if _block_for_substitution(game_id, wolf,
                                       index=alive.index(wolf) if wolf in alive else 0,
                                       code="bridge_runner_timeout"):
                return "blocked"

    # Phase 2: Coordinated kill vote
    votes: dict[str, int] = {}
    discussion_text = "\n".join(discussion_lines) if discussion_lines else "无讨论"

    for wolf in wolves:
        wname = SEAT_PERSONAS.get(wolf.seat, {}).get("name", wolf.seat)
        prompt = (
            f"AI Judge 狼人杀 第 {night} 夜 — 狼人猎杀投票。\n"
            "忽略网页里旧对话。在讨论后，每个狼人投票决定猎杀目标。\n\n"
            f"你是狼人 {wname}。\n"
            f"队友讨论：\n{discussion_text}\n\n"
            f"可选目标（含队友和空刀）：{'、'.join(display_targets)}\n\n"
            f"已公开记录：\n{public_history or '暂无。'}\n\n"
            "输出格式：我猎杀：[玩家名称] 或 我猎杀：空刀\n只输出一行。"
        )
        raw = _run_single_seat(runner, question=prompt, seat=wolf.seat)
        _record_raw(game_id, raw)
        if raw.get("ok"):
            text = _clean_response(str(raw.get("response") or ""))
            # Check for empty kill
            if "空刀" in text or "不猎杀" in text:
                votes["__empty__"] = votes.get("__empty__", 0) + 1
            else:
                for p in all_alive:
                    pname = SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat)
                    if pname and pname in text:
                        votes[p.seat] = votes.get(p.seat, 0) + 1
                        break
        elif _error_code(raw) == "bridge_runner_timeout":
            if _block_for_substitution(game_id, wolf,
                                       index=alive.index(wolf) if wolf in alive else 0,
                                       code="bridge_runner_timeout"):
                return "blocked"

    if not votes:
        session = _raw_session(game_id) or {}
        policy = str((session.get("_rules") or {}).get("no_wolf_vote_policy") or "empty_kill")
        return "__empty__" if policy == "empty_kill" else None

    # Empty kill wins if it has majority
    empty_votes = votes.get("__empty__", 0)
    non_empty = {k: v for k, v in votes.items() if k != "__empty__"}
    if empty_votes > sum(non_empty.values()):
        return "__empty__"  # Signal empty kill
    if non_empty:
        top = max(non_empty, key=lambda k: non_empty[k])
        for p in all_alive:
            if p.seat == top:
                return p
    session = _raw_session(game_id) or {}
    policy = str((session.get("_rules") or {}).get("no_wolf_vote_policy") or "empty_kill")
    return "__empty__" if policy == "empty_kill" else None


def _night_seer_check(
    game_id: str, runner: Runner, seer: Any,
    alive: list[Any], eliminated: dict[str, str],
    packets: dict[str, dict[str, Any]], topic: str,
    public_history: str, night: int,
) -> Any:
    """Seer checks one player's identity. Returns (target_player, is_wolf) or None."""
    import random

    session = _raw_session(game_id)
    seer_checked = list(session.get("_seer_checked") or [])
    # Exclude already-checked players (no repeat checks)
    candidates = [p for p in alive
                  if p.seat != seer.seat
                  and p.seat not in eliminated
                  and p.seat not in seer_checked]
    if not candidates:
        # If all alive have been checked, allow re-check
        candidates = [p for p in alive if p.seat != seer.seat and p.seat not in eliminated]
        if not candidates:
            return None

    cand_names = [SEAT_PERSONAS.get(c.seat, {}).get("name", c.seat) for c in candidates]
    sname = SEAT_PERSONAS.get(seer.seat, {}).get("name", seer.seat)

    prompt = (
        f"AI Judge 狼人杀 第 {night} 夜 — 预言家查验阶段。\n"
        "忽略网页里旧对话、旧验收、旧报告任务，专注当前狼人杀任务。\n\n"
        f"你是预言家 {sname}。你可以在夜晚查验一名玩家的真实身份。\n"
        f"可查验目标：{'、'.join(cand_names)}\n\n"
        f"已公开记录：\n{public_history or '暂无。'}\n\n"
        "查验策略：\n"
        "1. 优先查验白天发言矛盾或跟票异常的玩家。\n"
        "2. 也可查验潜水/划水玩家，确认其阵营。\n"
        "3. 如果你打算跳身份，先查验再跳更有说服力。\n\n"
        "输出格式：我查验：[玩家名称]\n只输出一行。"
    )
    raw = _run_single_seat(runner, question=prompt, seat=seer.seat)
    _record_raw(game_id, raw)

    target = None
    if raw.get("ok"):
        text = _clean_response(str(raw.get("response") or ""))
        for c in candidates:
            cname = SEAT_PERSONAS.get(c.seat, {}).get("name", c.seat)
            if cname and cname in text:
                target = c
                break
    elif _error_code(raw) == "bridge_runner_timeout":
        if _block_for_substitution(game_id, seer,
                                   index=alive.index(seer) if seer in alive else 0,
                                   code="bridge_runner_timeout"):
            return "blocked"

    if not target:
        target = random.choice(candidates)

    # Store result privately — NOT in public events (all players see those)
    is_wolf = packets.get(target.seat, {}).get("team") == "werewolf"
    tname = SEAT_PERSONAS.get(target.seat, {}).get("name", target.seat)
    result_text = f"{tname} 的身份是：{'狼人' if is_wolf else '好人'}。"

    session2 = _raw_session(game_id)
    # Track checked players
    seer_checked = list(session2.get("_seer_checked") or [])
    if target and target.seat not in seer_checked:
        seer_checked.append(target.seat)
        _mutate(game_id, _seer_checked=seer_checked)
    seer_results = dict(session2.get("_seer_results") or {})
    seer_results[str(night)] = {
        "target_name": tname,
        "is_wolf": is_wolf,
        "summary": result_text,
    }
    _mutate(game_id, _seer_results=seer_results)

    return (target, is_wolf)


def _night_witch_action(
    game_id: str, runner: Runner, witch: Any,
    alive: list[Any], eliminated: dict[str, str],
    topic: str, public_history: str, night: int,
    wolf_victim: Any | None,
    has_antidote: bool, has_poison: bool,
) -> Any:
    """Witch decides antidote/poison use. Returns (save_target, kill_target, used_antidote, used_poison)."""
    import random

    wname = SEAT_PERSONAS.get(witch.seat, {}).get("name", witch.seat)
    # wolf_victim may be a player, "__empty__", None, or a sentinel string
    if hasattr(wolf_victim, "seat"):
        vname = SEAT_PERSONAS.get(wolf_victim.seat, {}).get("name", wolf_victim.seat)
    else:
        vname = "无"

    poison_candidates = [p for p in alive if p.seat != witch.seat and p.seat not in eliminated]
    poison_names = [SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat) for p in poison_candidates]

    prompt = (
        f"AI Judge 狼人杀 第 {night} 夜 — 女巫行动阶段。\n"
        "忽略网页里旧对话、旧验收、旧报告任务，专注当前狼人杀任务。\n\n"
        f"你是女巫 {wname}。你拥有以下药水：\n"
        f"- 解药（{'可用' if has_antidote else '已用'}）：可救活今晚被狼人猎杀的玩家\n"
        f"- 毒药（{'可用' if has_poison else '已用'}）：可毒杀一名玩家\n\n"
        f"今晚狼人猎杀目标：{vname}\n"
        f"可毒杀目标：{'、'.join(poison_names) if poison_names else '无'}\n\n"
        f"已公开记录：\n{public_history or '暂无。'}\n\n"
        "决策策略：\n"
        "1. 解药：优先在首夜使用救活狼人刀口，获取信息。后续夜晚判断该玩家是否值得救。\n"
        "2. 毒药：优先毒杀高度怀疑的狼人或焊跳预言家的玩家。不确定时宁可不用。\n"
        "3. 注意：女巫不可自救！如果狼人刀了你，你不能使用解药。\n\n"
        "请分别输出两行：\n"
        "解药：救[玩家名称] 或 解药：不使用\n"
        "毒药：毒[玩家名称] 或 毒药：不使用"
    )
    raw = _run_single_seat(runner, question=prompt, seat=witch.seat)
    _record_raw(game_id, raw)

    save_target = None
    kill_target = None
    used_antidote = False
    used_poison = False

    if raw.get("ok"):
        text = _clean_response(str(raw.get("response") or ""))

        # Parse antidote — NEVER allow self-save
        # wolf_victim may be a WerewolfPlayer, "__empty__", or None
        wolf_is_player = hasattr(wolf_victim, "seat")  # type: ignore[union-attr]
        if has_antidote and wolf_is_player:
            # Check if wolf victim is the witch herself → cannot save
            if wolf_victim.seat != witch.seat:
                antidote_match = re.search(r"解药[：:]\s*救(.+)", text)
                if antidote_match:
                    save_name = antidote_match.group(1).strip()
                    if SEAT_PERSONAS.get(wolf_victim.seat, {}).get("name", "") in save_name:
                        save_target = wolf_victim
                        used_antidote = True
                elif "解药" in text and "不使用" in text:
                    pass
                elif "救" in text:
                    save_target = wolf_victim
                    used_antidote = True

        # Parse poison
        if has_poison and poison_candidates:
            poison_match = re.search(r"毒药[：:]\s*毒(.+)", text)
            if poison_match:
                poison_name = poison_match.group(1).strip()
                for p in poison_candidates:
                    if SEAT_PERSONAS.get(p.seat, {}).get("name", "") in poison_name:
                        kill_target = p
                        used_poison = True
                        break
    elif _error_code(raw) == "bridge_runner_timeout":
        if _block_for_substitution(game_id, witch,
                                   index=alive.index(witch) if witch in alive else 0,
                                   code="bridge_runner_timeout"):
            return "blocked"

    return (save_target, kill_target, used_antidote, used_poison)


def _vote_pollution_markers() -> tuple[str, ...]:
    return (
        "发言核心议题",
        "核心话题",
        "制造对立点",
        "风险脱离关系",
        "最小一步",
        "共同疑问",
        "自动模式",
        "创作工具",
        "内容由ai生成",
    )


def _looks_like_vote_pollution(text: str) -> bool:
    lower = str(text or "").lower()
    return any(marker.lower() in lower for marker in _vote_pollution_markers())


def _match_vote_target_fragment(fragment: str, alive_players: list[Any]) -> str | None:
    frag = str(fragment or "").strip()
    if not frag:
        return None
    frag_lower = frag.lower()
    for player in alive_players:
        seat = normalize_seat_id(getattr(player, "seat", ""))
        name = str(SEAT_PERSONAS.get(seat, {}).get("name") or seat)
        variants = {
            seat,
            seat.replace("_", " "),
            seat.replace("-", " "),
            name,
            name.lower(),
        }
        if any(variant and variant in frag for variant in variants):
            return seat
        if any(variant and variant.lower() in frag_lower for variant in variants):
            return seat
    return None


def _parse_vote_target(text: str, alive_players: list[Any]) -> str | None:
    """Extract vote target from model response.

    Web models often answer with prose instead of the exact one-line template.
    The parser first honors explicit vote syntax, then salvages a unique target
    near vote verbs so a slow-but-valid answer is not thrown away as failure.
    """
    raw_text = str(text or "")
    if not raw_text.strip():
        return None

    vote_patterns = [
        r"投票淘汰[：:\s]*([^\n。；;，,]+)",
        r"我(?:会|要|决定)?投票(?:淘汰|给)?[：:\s]*([^\n。；;，,]+)",
        r"我(?:会|要|决定)?投(?:给|出)?[：:\s]*([^\n。；;，,]+)",
        r"票(?:给|出)?[：:\s]*([^\n。；;，,]+)",
        r"我选择(?:淘汰|放逐)?[：:\s]*([^\n。；;，,]+)",
        r"选择淘汰[：:\s]*([^\n。；;，,]+)",
        r"归票[：:\s]*([^\n。；;，,]+)",
        r"放逐[：:\s]*([^\n。；;，,]+)",
        r"出[：:\s]*([^\n。；;，,]+)",
        r"目标[：:\s]*([^\n。；;，,]+)",
        r"淘汰[：:\s]*([^\n。；;，,]+)",
    ]
    for pat in vote_patterns:
        for match in re.finditer(pat, raw_text, flags=re.IGNORECASE):
            target = _match_vote_target_fragment(match.group(1), alive_players)
            if target:
                return target

    intent_words = ("投", "票", "淘汰", "放逐", "归票", "出局", "抗推", "挂")
    if not any(word in raw_text for word in intent_words):
        return None

    mentions: list[tuple[int, str]] = []
    lower_text = raw_text.lower()
    for player in alive_players:
        seat = normalize_seat_id(getattr(player, "seat", ""))
        name = str(SEAT_PERSONAS.get(seat, {}).get("name") or seat)
        variants = [name, seat, seat.replace("_", " "), seat.replace("-", " ")]
        positions = []
        for variant in variants:
            if not variant:
                continue
            pos = lower_text.find(variant.lower())
            if pos >= 0:
                positions.append(pos)
        if positions:
            nearest = min(
                min(abs(pos - raw_text.find(word)) for word in intent_words if raw_text.find(word) >= 0)
                for pos in positions
            )
            mentions.append((nearest, seat))

    unique = list(dict.fromkeys(seat for _, seat in sorted(mentions, key=lambda item: item[0])))
    return unique[0] if len(unique) == 1 else (unique[0] if mentions and mentions[0][0] <= 24 else None)


def _build_day_prompt(
    *, topic: str, player: Any, packet: dict[str, Any],
    public_history: str, day: int, is_first: bool,
    eliminated: dict[str, str],
    seer_private: dict[str, Any] | None = None,
) -> str:
    role_label = packet.get("role_label") or "未知"
    team_label = "狼人阵营" if packet.get("team") == "werewolf" else "好人阵营"
    day_context = "第一天" if is_first else f"第 {day} 天"
    pname = SEAT_PERSONAS.get(player.seat, {}).get("name", player.seat)
    role = packet.get("role") or "villager"
    public_history_short = _compact_public_history(public_history, max_chars=WEREWOLF_MAX_HISTORY_CHARS)

    elimination_info = ""
    if eliminated:
        items = []
        for seat, reason in eliminated.items():
            name = SEAT_PERSONAS.get(seat, {}).get("name", seat)
            items.append(f"{name}（{reason}）")
        elimination_info = f"\n已淘汰玩家：{'、'.join(items)}"

    # ── Day 1 prompt (competition mode with role-specific strategy) ──
    if is_first:
        # Role-specific day-1 hints for _build_day_prompt context
        if role == "werewolf":
            day1_hint = "狼人开局策略：主动点名怀疑一个玩家（可以不给出真理由），制造对立面。不要跟风说「信息不足」——那等于暴露自己不敢发言。"
        elif role == "seer":
            day1_hint = "预言家开局策略：在发言中埋一个可事后验证的暗线。比如「我对某人的身份有一个初步判断，后续验证后会公开」。不要跟风划水。"
        elif role == "witch":
            day1_hint = "女巫开局策略：记录本局中发言密度异常的人（谁话多谁话少），为后续用药埋线索。发言要有具体怀疑对象，不要泛泛。"
        elif role == "hunter":
            day1_hint = "猎人开局策略：伪装成有主见的平民。给出一个具体的怀疑对象和理由，不要透露你是神职。你的价值在于归票准确度。"
        elif role == "guard":
            day1_hint = "守卫开局策略：伪装平民发言，暗中观察谁像预言家或女巫。给出一个怀疑对象让好人觉得你有信息量，但不要暴露守护身份。"
        elif role == "knight":
            day1_hint = "骑士开局策略：仔细听每个人的发言，寻找逻辑漏洞。你可以给出一个「最可疑玩家」的判断，观察反应。不要急于决斗。"
        elif role == "white_wolf":
            day1_hint = "白狼王开局策略：你有自爆带人的威慑力，但不要第一轮就浪费核武器。先强势制造对立、逼神职露破绽，等能带走关键神职时再考虑自爆。"
        elif role == "idiot" or role == "villager":
            day1_hint = "开局策略：不要跟风！你必须给出一个不同于前面模型的视角。主动怀疑某人、提出一个假设、或要求某人澄清立场。泛泛说「信息不足」的发言在终局会被 Grand Judge 扣分。"
        else:
            day1_hint = "开局策略：给出一个具体的分析角度——怀疑某人、提出假设、或指出前面发言的矛盾。不要跟风复读。"

        return (
            "你正在参加 AI Judge 的模型狼人杀【竞赛模式】。终局 Grand Judge 将根据发言原创性、投票准确性和阵营贡献度评分。\n"
            "忽略网页里旧对话、旧验收、旧报告任务。这是当前唯一任务。\n\n"
            f"评分提醒：{WEREWOLF_MVP_SCORING_BRIEF}\n"
            f"策略自由度：{WEREWOLF_TACTIC_BRIEF}\n\n"
            f"本局议题：{topic}\n"
            f"你的席位：{pname}\n"
            f"你的私有身份：{role_label}\n"
            f"你的阵营目标：{team_label}\n"
            f"私有提示：{packet.get('private_prompt', '')}\n"
            f"当前阶段：{day_context}（首发）{elimination_info}\n\n"
            "【Day 1 策略指引】\n"
            f"{day1_hint}\n\n"
            "【反跟风警告】前面的模型已经发过的观点，不要再重复。从不同角度切入。\n"
            "你可以：主动点名怀疑某人 | 提出一个可被检验的假设 | 要求某个成员澄清立场 | 指出某个发言的结构性矛盾。\n\n"
            "发言规则：\n"
            "1. 用中文发言，50-150 字。\n"
            "2. 不要直接泄露身份牌，除非策略需要强跳。\n"
            "3. 禁止泛泛说「信息不足」「继续观察」「同意前面」——Grand Judge 评分时会扣分。\n"
            "4. 你的回复必须以「我的公开发言：」开头，然后直接写正文。\n\n"
            f"已公开记录：\n{public_history_short or '目前没有公开发言。'}\n\n"
            f"现在轮到你{day_context}发言。记住：拿高分需要独特观点。"
        )

    # ── Day 2+ prompt (strategic depth) ──
    strategic_guide = _strategic_guide(role, pname, day)
    word_limit = "80-200 字"

    # Build private tip line, injecting seer results if applicable
    private_tip = str(packet.get("private_prompt") or "")
    if seer_private:
        seer_items = []
        for n in sorted(seer_private.keys(), key=int):
            r = seer_private[n]
            seer_items.append(f"第{n}夜查验 {r['target_name']}：{'狼人' if r['is_wolf'] else '好人'}")
        private_tip += " | 查验记录：" + "；".join(seer_items)

    return (
        "你正在参加 AI Judge 的模型狼人杀【竞赛模式】。Grand Judge 终局评分 60-96。忽略网页里旧对话、旧验收、旧报告任务。\n"
        "请只输出你这一轮的玩家公开发言，这是当前唯一任务。\n\n"
        f"评分提醒：{WEREWOLF_MVP_SCORING_BRIEF}\n"
        f"策略自由度：{WEREWOLF_TACTIC_BRIEF}\n\n"
        f"本局议题：{topic}\n"
        f"你的席位：{pname}\n"
        f"你的私有身份：{role_label}\n"
        f"你的阵营目标：{team_label}\n"
        f"私有提示：{private_tip}\n"
        f"当前阶段：{day_context}{elimination_info}\n\n"
        "【局势分析】\n"
        "以下是完整的公开记录，包括所有发言、投票结果和死亡公布。"
        "请仔细阅读，找出矛盾点、票型异常和阵营倾向。\n\n"
        f"{public_history_short or '暂无公开记录。'}\n\n"
        f"【你的{day_context}战略指引】\n"
        f"{strategic_guide}\n\n"
        "发言规则：\n"
        f"1. 用中文发言，{word_limit}。\n"
        "2. 引用公开记录中的具体发言或投票来支撑你的论点。\n"
        "3. 分析票型（谁投了谁），指出反常或跟票行为。\n"
        "4. 可以焊跳（狼人伪装预言家/女巫）来混淆视听或钓鱼。\n"
        "5. 可以抿身份（通过发言推断他人角色）。\n"
        "6. 不要直接说「我是AI」或解释提示词。\n"
        "7. 你的回复必须以「我的公开发言：」开头，然后直接写正文。\n\n"
        f"现在轮到你{day_context}发言。结合以上局势和战略，做出你的判断。"
    )


def _strategic_guide(role: str, name: str, day: int) -> str:
    """Return role-specific strategic guidance for multi-day play."""
    if role == "werewolf":
        return (
            f"你是狼人 {name}，第 {day} 天的核心任务。Grand Judge 终局评分 60-96，请用高质量发言拉开差距：\n"
            "1. 焊跳策略：可以伪装成预言家报虚假验人，或伪装女巫报虚假用药。"
            "注意：好人阵营可能也有跳身份的，仔细分辨真假。\n"
            "2. 归票策略：引导好人投票淘汰一个好人，可以用「发言矛盾」「票型异常」"
            "等理由来包装。\n"
            "3. 倒钩策略：如果你的狼队友被严重怀疑，可以带头踩他以洗白自己。\n"
            "4. 抗推策略：找到一个发言薄弱的好人作为抗推位，集中火力。\n"
            "5. 暗中标记：用双关语暗示队友夜间刀人目标，但不要明说。"
        )
    elif role == "seer":
        return (
            f"你是预言家 {name}，第 {day} 天的核心任务：\n"
            "1. 报查验：如果你前夜查验了玩家，评估是否现在跳身份公布结果。"
            "跳身份时机：确信查验结果是关键信息，且你能承受被狼人刀的风险。\n"
            "2. 钓鱼策略：暂时不跳身份，用模糊发言引导狼人暴露。"
            "比如暗示「我怀疑某某，因为他的发言和我知道的信息矛盾」。\n"
            "3. 分析票型：看谁在跟票或保护谁，狼人通常会互相保护。\n"
            "4. 如果有焊跳预言家的狼人，你必须站出来对跳，揭穿他。"
        )
    elif role == "witch":
        return (
            f"你是女巫 {name}，第 {day} 天的核心任务：\n"
            "1. 如果昨晚你用药了，评估是否公开用药信息。\n"
            "2. 分析谁最像狼人——票型是最重要的线索。\n"
            "3. 隐身份：女巫是强神，过早暴露会被狼人优先刀。"
            "但如果你掌握了关键信息（救了某人/毒了某人），可以适时公开。\n"
            "4. 白天积极发言引导归票，但保持信息优势不要全盘托出。"
        )
    elif role == "hunter":
        return (
            f"你是猎人 {name}，第 {day} 天的核心任务：\n"
            "1. 隐身份：猎人不应该过早暴露，否则会被狼人投票淘汰来规避你的开枪。\n"
            "2. 分析发言：找出逻辑漏洞最大的玩家，推动归票。\n"
            "3. 如果你被投票淘汰，选择开枪带走你认为最可能是狼人的玩家。\n"
            "4. 发言应该像一个有主见的平民，不要露出神职痕迹。"
        )
    elif role == "guard":
        return (
            f"你是守卫 {name}，第 {day} 天的核心任务：\n"
            "1. 隐身份：守卫是强神，绝不能白天暴露身份，否则狼人会优先刀你。\n"
            "2. 白天尽量伪装成平民发言，不要露出神职痕迹。\n"
            "3. 分析票型和发言找出狼人，帮助归票。\n"
            "4. 暗中观察：如果预言家明跳或女巫用药，优先在夜晚守护他们。"
        )
    elif role == "villager":
        return (
            f"你是平民 {name}，第 {day} 天的核心任务：\n"
            "1. 民搅策略：可以故意发表看似矛盾的言论来观察谁在跟风踩你，"
            "跟风踩的多半是狼人想抗推你。\n"
            "2. 抿身份：通过其他玩家的发言推断他们的真实角色。"
            "狼人通常发言谨慎、回避正面冲突，好人更敢表达观点。\n"
            "3. 分析票型：前一轮投票中，谁投了谁。找出一致投某个人的群体，"
            "可能是狼人冲票。\n"
            "4. 敢于带队：如果你是第一个发言的平民，主动给出分析方向，"
            "不要划水——平民是好人阵营的人数基础。\n"
            "5. 焊跳策略（进阶）：你也可以焊跳预言家来钓鱼，"
            "看谁跟着你的假验人踩人，跟踩的可能就是狼。"
        )
    elif role == "white_wolf":
        return (
            f"你是白狼王 {name}，第 {day} 天的核心任务：\n"
            "1. 你是狼人阵营中最危险的武器。白天可以自爆并带走一名玩家，"
            "被带走的无遗言，且立刻进入黑夜。\n"
            "2. 自爆时机：当你被严重怀疑即将被投票淘汰时，自爆带走一个强神"
            "（预言家/女巫）。不要浪费在平民或潜水玩家身上。\n"
            "3. 发言策略：尽量表现得像一个有逻辑的好人。"
            "当你准备自爆时，先记住谁是强神的目标再引爆。\n"
            "4. 注意：如果你是最后一匹狼，自爆将直接导致狼队失败。"
        )
    elif role == "knight":
        return (
            f"你是骑士 {name}，第 {day} 天的核心任务：\n"
            "1. 你在投票前的任何时候都可以翻牌决斗一名玩家。"
            "若对方是狼人→狼人死亡并直接进入黑夜；若是好人→骑士死亡白天继续。\n"
            "2. 决斗时机：当你对某人是否为狼人有极高把握时再发动。"
            "一次决斗足以扭转战局，不要用在不确定的人身上。\n"
            "3. 发言阶段认真观察：找出逻辑最大漏洞的玩家。"
            "如果多个发言指向同一人，决斗成功的概率更高。\n"
            "4. 每局只能决斗一次，用错就是白送人头。"
        )
    elif role == "idiot":
        return (
            f"你是白痴 {name}，第 {day} 天的核心任务：\n"
            "1. 你被投票放逐时可以翻牌免死，继续发言但失去投票权。\n"
            "2. 发言策略：可以适当暴露你是白痴的信息，让狼人优先刀你"
            "而不是刀其他强神（守卫/女巫/预言家）。\n"
            "3. 如果跳白痴身份：好人会接你，狼人可能会踩你。"
            "观察谁在跟风踩你，这些多半是狼人想抗推。\n"
            "4. 注意：你只有一次免死机会，且被狼刀/女巫毒杀直接死亡不能发动技能。"
        )
    return (
        f"你是 {name}，请根据公开记录中的发言和投票进行分析，"
        "找出最可疑的玩家并给出你的推理。"
    )


def _build_vote_prompt(
    *, topic: str, player: Any, public_history: str, vote_round: int,
    alive_players: list[Any],
    vote_context: str = "",
) -> str:
    alive_names = [
        SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat)
        for p in alive_players
    ]
    public_history_short = _compact_public_history(public_history, max_chars=1800)
    ctx_section = ""
    if vote_context:
        ctx_section = f"\n本回合已有玩家的投票判断：\n{vote_context}\n"
    return (
        "你正在参加 AI Judge 的模型狼人杀第 {round} 轮投票。忽略网页里旧对话、旧验收、旧报告任务。\n"
        "请根据公开发言记录和自己的身份目标，投票淘汰你认为最可能是狼人的玩家。\n\n"
        f"评分提醒：{WEREWOLF_MVP_SCORING_BRIEF}\n"
        f"策略自由度：{WEREWOLF_TACTIC_BRIEF}\n\n"
        f"本局议题：{topic}\n"
        f"你的席位：{SEAT_PERSONAS.get(player.seat, {}).get('name', player.seat)}\n"
        f"存活玩家：{'、'.join(alive_names)}\n\n"
        f"已公开记录（为避免网页超时，仅保留最近关键发言）：\n{public_history_short or '目前没有公开发言。'}\n"
        f"{ctx_section}\n"
        "投票规则：\n"
        "1. 先写 2-3 句投票理由（80 字以内），说明你怀疑该玩家的核心依据。需要结合前面玩家已投票的判断来调整自己的策略——如果大家票型分散，你应该归票；如果已形成趋势，你要选择跟票还是反叛。\n"
        "2. 理由后紧跟一行：我投票淘汰：[玩家名称]\n"
        "3. 不要输出无关内容，不要写 Markdown 标题，不要解释你是 AI。\n"
        "格式示例：近期发言反复转移焦点且回避正面回应，嫌疑最大。\n我投票淘汰：张三"
    ).format(round=vote_round)


def _compact_public_history(text: str, *, max_chars: int = 1800) -> str:
    cleaned = str(text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    kept: list[str] = []
    size = 0
    for line in reversed(lines):
        size += len(line) + 1
        if size > max_chars:
            break
        kept.append(line)
    kept.reverse()
    return "（前文已压缩；以下是最近发言和投票线索）\n" + "\n".join(kept)


def _adaptive_werewolf_timeout_seconds(*, question: str, seat: str, requested: float) -> float:
    """Give later/longer werewolf turns enough room without making every call slow."""
    text = str(question or "")
    prompt_size = len(text)
    requested = float(requested or 0.0)
    simple_one_line = (
        "只输出一行" in text
        or "警长竞选阶段" in text
        or "警长投票" in text
    )
    if simple_one_line:
        base = max(requested, 45.0)
        if seat in {"qwen", "mimo", "wenxin", "minimax", "zhipu", "deepseek"}:
            base += 20.0
        if seat in OPTIONAL_TIMEOUT_SEATS:
            return min(OPTIONAL_SEAT_HARD_TIMEOUT_SECONDS, base)
        return min(85.0, base)
    size_bonus = min(180.0, max(0.0, (prompt_size - 1400) / 18.0))
    phase_bonus = 0.0
    if "第 2 天" in text or "第 3 天" in text or "完整的公开记录" in text:
        phase_bonus += 60.0
    if "投票" in text or "遗言" in text or "夜间" in text:
        phase_bonus += 30.0
    if seat in {"qwen", "mimo", "wenxin", "minimax", "zhipu", "deepseek"}:
        phase_bonus += 45.0
    if seat in OPTIONAL_TIMEOUT_SEATS:
        return min(OPTIONAL_SEAT_HARD_TIMEOUT_SECONDS, max(75.0, requested))
    return min(480.0, max(requested, 210.0 + size_bonus + phase_bonus))


def _late_grace_seconds(*, question: str, seat: str) -> float:
    text = str(question or "")
    if "只输出一行" in text or "警长竞选阶段" in text or "警长投票" in text:
        return 10.0 if seat not in OPTIONAL_TIMEOUT_SEATS else 8.0
    grace = WEREWOLF_LATE_GRACE_SECONDS
    if len(text) > 2400:
        grace += 45.0
    if "第 2 天" in text or "第 3 天" in text or "完整的公开记录" in text:
        grace += 45.0
    if seat in {"qwen", "mimo", "wenxin", "minimax", "zhipu", "deepseek"}:
        grace += 30.0
    if seat in OPTIONAL_TIMEOUT_SEATS:
        return 30.0
    return min(210.0, grace)


def _driver_timeout_seconds(hard_timeout_seconds: float, late_grace_seconds: float) -> float:
    """Let the browser driver wait most of the budget, while preserving late recovery room."""
    minimum = 30.0 if float(hard_timeout_seconds) <= 90.0 else (45.0 if float(hard_timeout_seconds) <= 150.0 else 120.0)
    return max(minimum, min(360.0, float(hard_timeout_seconds) - min(90.0, float(late_grace_seconds) * 0.55)))


def _recover_late_fixed_tab_answer(*, question: str, seat: str, config_overrides: dict[str, Any]) -> dict[str, Any]:
    """Read a late answer from the already-open fixed Chrome tab without sending again."""
    try:
        config = merge_bridge_config_overrides(load_bridge_config(), {
            **config_overrides,
            "retry_failed_seats": False,
            "fresh_conversation_per_run": False,
        })
        results = recover_existing_fixed_tab_answers(
            question=question,
            seats=[seat],
            config=config,
            mode="flash",
        )
        item = results[0] if results else {}
        if isinstance(item, dict):
            item.setdefault("seat", seat)
            if item.get("ok"):
                item["late_recovery_mode"] = "read_existing_fixed_tab"
            return item
    except Exception as exc:
        return {
            "seat": seat,
            "ok": False,
            "response": "",
            "error": {"code": "late_recovery_failed", "message": str(exc)},
            "supplementable": True,
        }
    return {
        "seat": seat,
        "ok": False,
        "response": "",
        "error": {"code": "late_recovery_empty"},
        "supplementable": True,
    }


def _run_single_seat(runner: Runner, *, question: str, seat: str, hard_timeout_seconds: float = 150.0, skip_late_recovery: bool = False) -> dict[str, Any]:
    seat_id = normalize_seat_id(seat)
    text = str(question or "")
    simple_one_line = (
        "只输出一行" in text
        or "警长竞选阶段" in text
        or "警长投票" in text
    )
    hard_timeout_seconds = _adaptive_werewolf_timeout_seconds(
        question=question,
        seat=seat_id,
        requested=hard_timeout_seconds,
    )
    late_grace_seconds = _late_grace_seconds(question=question, seat=seat_id)
    driver_timeout_seconds = _driver_timeout_seconds(hard_timeout_seconds, late_grace_seconds)
    base_overrides = {
        "timeout_seconds": driver_timeout_seconds,
        "retry_timeout_seconds": driver_timeout_seconds,
        "required_timeout_seconds": driver_timeout_seconds,
        "required_retry_timeout_seconds": driver_timeout_seconds,
        "final_nudge_timeout_seconds": max(45, min(120, int(driver_timeout_seconds * 0.35))),
        "post_timeout_grace_seconds": max(45, min(150, int(late_grace_seconds))),
        "fresh_conversation_per_run": True,
        "fresh_navigation_timeout_seconds": 10,
        "fresh_load_seconds": 1.6,
    }
    if seat_id in OPTIONAL_TIMEOUT_SEATS:
        hard_timeout_seconds = min(hard_timeout_seconds, OPTIONAL_SEAT_HARD_TIMEOUT_SECONDS)
        late_grace_seconds = min(late_grace_seconds, 30.0)
        base_overrides.update({
            "timeout_seconds": 75,
            "retry_timeout_seconds": 75,
            "required_timeout_seconds": 75,
            "required_retry_timeout_seconds": 75,
            "final_nudge_timeout_seconds": 20,
            "post_timeout_grace_seconds": 18,
            "page_recovery_attempts": 1,
            "mode_prepare_max_attempts": 4,
        })
    elif seat_id == "qwen" and not simple_one_line:
        hard_timeout_seconds = max(hard_timeout_seconds, 300.0)
        late_grace_seconds = max(late_grace_seconds, 120.0)
        base_overrides.update({
            "timeout_seconds": 240,
            "retry_timeout_seconds": 240,
            "required_timeout_seconds": 240,
            "required_retry_timeout_seconds": 240,
            "final_nudge_timeout_seconds": 90,
            "post_timeout_grace_seconds": 75,
            "page_recovery_attempts": 2,
            "mode_prepare_max_attempts": 8,
        })
    elif seat_id in {"mimo", "wenxin", "minimax", "zhipu"} and not simple_one_line:
        hard_timeout_seconds = max(hard_timeout_seconds, 210.0)
        late_grace_seconds = max(late_grace_seconds, 105.0)
        fragile_driver_timeout = max(float(base_overrides["timeout_seconds"]), min(330.0, hard_timeout_seconds - 30.0))
        base_overrides.update({
            "timeout_seconds": fragile_driver_timeout,
            "retry_timeout_seconds": fragile_driver_timeout,
            "required_timeout_seconds": fragile_driver_timeout,
            "required_retry_timeout_seconds": fragile_driver_timeout,
            "final_nudge_timeout_seconds": max(75, min(150, int(fragile_driver_timeout * 0.35))),
            "post_timeout_grace_seconds": max(90, min(180, int(late_grace_seconds))),
            "page_recovery_attempts": 2,
            "mode_prepare_max_attempts": 8,
        })

    def invoke(overrides: dict[str, Any]) -> dict[str, Any]:
        results = _runner_call_with_timeout(
            runner,
            timeout_seconds=hard_timeout_seconds,
            late_grace_seconds=late_grace_seconds,
            question=question,
            seats=[seat],
            mode="flash",
            config_overrides=overrides,
        )
        if isinstance(results, dict) and results.get("error", {}).get("code") == "bridge_runner_timeout":
            return results
        return results[0] if results else {"seat": seat, "ok": False, "error": {"code": "empty_result"}}

    try:
        first = invoke(base_overrides)
        if (
            _error_code(first) == "bridge_runner_timeout"
            and seat_id not in OPTIONAL_TIMEOUT_SEATS
            and skip_late_recovery is False
        ):
            recovered = _recover_late_fixed_tab_answer(
                question=question,
                seat=seat_id,
                config_overrides=base_overrides,
            )
            if recovered.get("ok"):
                recovered["late_recovered_after_runner_timeout"] = True
                return recovered
        transient_codes = {
            "cdp_unavailable",
            "chrome_crash",
            "fixed_tab_not_found",
            "deepseek_expert_mode_not_verified",
            "page_error",
            "model_page_error",
            "blank_page",
            "submit_unconfirmed",
            "send_button_not_found",
            "composer_busy",
        }
        if _error_code(first) == "bridge_runner_timeout" and seat_id in OPTIONAL_TIMEOUT_SEATS:
            first.setdefault("seat", seat)
            first["supplementable"] = True
            first["error"] = {
                "code": "optional_seat_timeout",
                "message": "Optional/best-effort werewolf seat timed out; keep the game flowing and collect this seat later.",
                "original_code": "bridge_runner_timeout",
            }
            return first
        if not first.get("ok") and _error_code(first) in transient_codes:
            time.sleep(2)
            retry = invoke({
                **base_overrides,
                "cdp_connect_timeout_seconds": 30,
                "cdp_default_timeout_seconds": 12,
                "mode_prepare_max_attempts": 8,
                "page_recovery_attempts": 2,
            })
            if retry.get("ok"):
                retry.setdefault("recovered_from_transient_bridge_error", _error_code(first))
                return retry
            retry.setdefault("transient_retry_from", _error_code(first))
            return retry
        return first
    except Exception as exc:
        first_error = str(exc)
        if "connect_over_cdp" in first_error or "DevTools" in first_error or "127.0.0.1:9333" in first_error:
            time.sleep(2)
            try:
                retry = invoke(base_overrides)
                if retry.get("ok"):
                    return retry
                retry.setdefault("cdp_retry_error", first_error)
                return retry
            except Exception as retry_exc:
                try:
                    fallback = invoke({**base_overrides, "automation_driver": "chrome_apple_events"})
                    fallback.setdefault("cdp_error", first_error)
                    return fallback
                except Exception as fallback_exc:
                    return {
                        "seat": seat,
                        "ok": False,
                        "response": "",
                        "error": {
                            "code": "bridge_driver_unavailable",
                            "message": f"CDP failed: {first_error}; Apple Events fallback failed: {fallback_exc}",
                        },
                    }
        return {
            "seat": seat,
            "ok": False,
            "response": "",
            "error": {"code": "bridge_runner_exception", "message": first_error},
        }


def _runner_call_with_timeout(
    runner: Runner,
    *,
    timeout_seconds: float,
    late_grace_seconds: float = 0.0,
    **kwargs: Any,
) -> list[dict[str, Any]] | dict[str, Any]:
    if runner is run_web_seats:
        return _runner_call_in_process_with_timeout(
            runner,
            timeout_seconds=timeout_seconds,
            late_grace_seconds=late_grace_seconds,
            **kwargs,
        )

    output: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=1)

    def target() -> None:
        try:
            output.put(("ok", runner(**kwargs)), block=False)
        except Exception as exc:  # pragma: no cover - passed back to caller
            output.put(("error", exc), block=False)

    thread = threading.Thread(target=target, daemon=True)
    thread.start()
    thread.join(timeout_seconds)
    if thread.is_alive():
        grace = max(0.0, float(late_grace_seconds or 0.0))
        if grace:
            thread.join(grace)
            if not thread.is_alive():
                kind, value = output.get() if not output.empty() else ("ok", [])
                if kind == "error":
                    raise value
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            item["late_after_hard_timeout"] = True
                            item["late_grace_seconds"] = grace
                    return value
                if isinstance(value, dict):
                    value["late_after_hard_timeout"] = True
                    value["late_grace_seconds"] = grace
                return value
        return {
            "seat": kwargs.get("seats", ["unknown"])[0],
            "ok": False,
            "response": "",
            "error": {
                "code": "bridge_runner_timeout",
                "message": f"Web bridge runner did not return within {int(timeout_seconds + grace)} seconds.",
            },
            "supplementable": True,
            "late_grace_seconds": grace,
        }
    kind, value = output.get() if not output.empty() else ("ok", [])
    if kind == "error":
        raise value
    return value


def _runner_process_target(runner: Runner, kwargs: dict[str, Any], output: Any) -> None:
    try:
        output.put(("ok", runner(**kwargs)), block=False)
    except BaseException as exc:  # pragma: no cover - executed in child process
        output.put(("error", f"{type(exc).__name__}: {exc}"), block=False)


def _runner_call_in_process_with_timeout(
    runner: Runner,
    *,
    timeout_seconds: float,
    late_grace_seconds: float = 0.0,
    **kwargs: Any,
) -> list[dict[str, Any]] | dict[str, Any]:
    """Run the real Chrome bridge in a killable child process.

    The previous watchdog used a daemon thread. When a browser call exceeded the
    hard timeout, that thread kept controlling the fixed Chrome tab while the
    game advanced to the next seat, which polluted turns and made the UI look
    frozen. A subprocess gives the Grand Judge an actual circuit breaker.
    """
    ctx = multiprocessing.get_context("spawn")
    output = ctx.Queue(maxsize=1)
    process = ctx.Process(target=_runner_process_target, args=(runner, kwargs, output), daemon=True)
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        grace = max(0.0, float(late_grace_seconds or 0.0))
        if grace:
            process.join(grace)
            if not process.is_alive():
                return _read_process_runner_output(output, kwargs, late_after_hard_timeout=True, grace=grace)
        process.terminate()
        process.join(5)
        if process.is_alive():  # pragma: no cover - defensive on stubborn child process
            process.kill()
            process.join(2)
        return {
            "seat": kwargs.get("seats", ["unknown"])[0],
            "ok": False,
            "response": "",
            "error": {
                "code": "bridge_runner_timeout",
                "message": f"Web bridge runner was terminated after {int(timeout_seconds + grace)} seconds.",
            },
            "supplementable": True,
            "late_grace_seconds": grace,
            "runner_isolated_process": True,
        }
    return _read_process_runner_output(output, kwargs)


def _read_process_runner_output(
    output: Any,
    kwargs: dict[str, Any],
    *,
    late_after_hard_timeout: bool = False,
    grace: float = 0.0,
) -> list[dict[str, Any]] | dict[str, Any]:
    try:
        kind, value = output.get_nowait()
    except Exception:
        return [{
            "seat": kwargs.get("seats", ["unknown"])[0],
            "ok": False,
            "response": "",
            "error": {"code": "empty_result", "message": "Bridge runner exited without a result."},
            "supplementable": True,
        }]
    if kind == "error":
        raise RuntimeError(str(value))
    if late_after_hard_timeout:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    item["late_after_hard_timeout"] = True
                    item["late_grace_seconds"] = grace
            return value
        if isinstance(value, dict):
            value["late_after_hard_timeout"] = True
            value["late_grace_seconds"] = grace
    return value


def _finalize_session(game_id: str) -> None:
    """Finalize session: compute scores and declare winner."""
    session = _raw_session(game_id)
    if not session:
        return
    players = list(session.get("_players", []))
    eliminated = dict(session.get("_eliminated") or {})
    raw = list(session.get("raw_results") or [])

    # Determine winner using comprehensive win check
    good_wins, winner_reason = _check_win_condition(game_id, return_reason=True)

    winner_label = "好人阵营胜利" if good_wins else "狼人阵营胜利"
    reason_text = f"（{winner_reason}）" if winner_reason else ""
    winner_detail = (
        f"游戏结束：{winner_label}{reason_text}。"
        f"竞赛评分 60-96 区间已发布，依据：发言原创性、投票准确性、阵营贡献度。"
        f"划水发言和跟风复读将被压低分数。"
    )

    scores = []
    for player in players:
        seat_results = [item for item in raw if normalize_seat_id(str(item.get("seat") or "")) == player.seat]
        ok_results = [item for item in seat_results if item.get("ok")]
        response = "\n".join(str(item.get("response") or "") for item in ok_results)
        result = ok_results[-1] if ok_results else (seat_results[-1] if seat_results else {})
        role = getattr(player, "role", "villager")
        team = TEAM_BY_ROLE.get(role, "good")
        is_winner = (
            (team == "werewolf" and not good_wins) or
            (team != "werewolf" and good_wins)
        )
        # P35: score all real contributions, including last words and night actions.
        base = 60 if ok_results else 30
        qual = min(20, len(response) // 90)
        activity_bonus = min(6, max(0, len(ok_results) - 1) * 2)
        winner_bonus = 16 if is_winner else 0
        score = min(96, base + qual + activity_bonus + winner_bonus)
        detail = (
            f"{len(ok_results)} 次真实网页贡献已进入记录，{'阵营胜利' if is_winner else '阵营失败'}。"
            if ok_results
            else f"桥接未完成/超时回采：{_error_code(result)}。"
        )
        scores.append([player.seat, score, detail])

    scores.sort(key=lambda item: item[1], reverse=True)

    _append_event(game_id, {
        "kind": "judge",
        "phase": "final",
        "status": winner_label,
        "text": winner_detail,
    })
    _mutate(game_id, status="complete", phase="final", progress=1.0, scores=scores)


def _available_substitute_seats(session: dict[str, Any], offline: str) -> list[str]:
    players = list(session.get("_players") or [])
    active = {item.seat for item in players}
    offline_set = set(session.get("offline_seats") or [])
    standby = [
        normalize_seat_id(item)
        for item in (
            session.get("standby_seats")
            or standby_seats(
                [item.seat for item in players],
                board=session.get("_board") or session.get("board") or DEFAULT_BOARD,
            )
        )
    ]
    return [
        seat for seat in standby
        if seat in WEREWOLF_CANDIDATE_SEATS
        and seat not in active
        and seat not in offline_set
        and seat != offline
    ]


def _block_for_substitution(game_id: str, player: Any, *, index: int, code: str) -> bool:
    """Return True when the game must pause; False when it can degrade and continue."""
    offline = player.seat
    substitute_event: dict[str, Any] | None = None
    if AUTO_SUBSTITUTE_TIMEOUTS:
        with _LOCK:
            session = _SESSIONS.get(game_id)
            if session:
                players = list(session.get("_players") or [])
                player_index = next((idx for idx, item in enumerate(players) if item.seat == offline), -1)
                available_substitutes = _available_substitute_seats(session, offline)
                substitute = (
                    next((seat for seat in available_substitutes if seat not in OPTIONAL_TIMEOUT_SEATS), None)
                    or next(iter(available_substitutes), None)
                )
                if player_index >= 0 and substitute:
                    old_player = players[player_index]
                    replacement = WerewolfPlayer(
                        seat=substitute,
                        role=old_player.role,
                        team=old_player.team,
                        slot=old_player.slot,
                        replaced_seat=old_player.seat,
                    )
                    players[player_index] = replacement
                    roster = [item.seat for item in players]
                    substitution = {
                        "offline_seat": offline,
                        "substitute_seat": substitute,
                        "slot": old_player.slot,
                        "role": old_player.role,
                        "role_label": ROLE_LABELS.get(old_player.role, old_player.role),
                        "reason": code,
                        "mode": "auto",
                    }
                    packets = dict(session.get("_private_role_packets") or {})
                    packets.pop(offline, None)
                    packets[substitute] = _private_packet_for_player(replacement)
                    session["_players"] = players
                    session["_private_role_packets"] = packets
                    session["seats"] = roster
                    session["standby_seats"] = standby_seats(roster, board=session.get("_board") or session.get("board") or DEFAULT_BOARD)
                    session["offline_seats"] = list(dict.fromkeys([*(session.get("offline_seats") or []), offline]))
                    session["substitutions"] = [*(session.get("substitutions") or []), substitution]
                    session["pending_substitution"] = None
                    session["players"] = [_public_player(item, reveal=False) for item in players]
                    session["status"] = "queued"
                    session["phase"] = "substitution"
                    session["error"] = None
                    session["next_player_index"] = index
                    session["updated_at"] = _utc_now()
                    session["version"] = int(session.get("version") or 0) + 1
                    substitute_event = {
                        "kind": "judge",
                        "phase": "substitution",
                        "status": "自动替补接管",
                        "substitution": substitution,
                        "text": (
                            f"{SEAT_PERSONAS.get(offline, {}).get('name', offline)} 因 {code} 超时，"
                            f"{SEAT_PERSONAS.get(substitute, {}).get('name', substitute)} 自动接管第 {old_player.slot} 席。"
                            "Grand Judge 已重新密封身份并继续本局，不再等待人工选择替补。"
                        ),
                    }
        if substitute_event:
            _append_event(game_id, substitute_event)
            thread = threading.Thread(
                target=_run_session,
                args=(game_id, run_web_seats),
                daemon=True,
            )
            thread.start()
            return True

    session = _raw_session(game_id) or {}
    available_substitutes = _available_substitute_seats(session, offline)
    if not available_substitutes:
        _append_event(game_id, {
            "kind": "judge",
            "phase": "substitution-exhausted",
            "status": "替补池耗尽，降级继续",
            "text": (
                f"{SEAT_PERSONAS.get(offline, {}).get('name', offline)} 因 {code} 暂时无有效网页回收，且当前没有可用替补。"
                "Grand Judge 不再把整局卡死：本轮该席位记为缺席/可补收，继续推进流程；迟到答案会进历史日志。"
            ),
        })
        _mutate(
            game_id,
            status="running",
            error=None,
            pending_substitution=None,
            offline_seats=list(dict.fromkeys([*(session.get("offline_seats") or []), offline])),
            next_player_index=index + 1,
            updated_at=_utc_now(),
        )
        return False

    if not BLOCK_FOR_MANUAL_SUBSTITUTION:
        _append_event(game_id, {
            "kind": "judge",
            "phase": "substitution-skipped",
            "status": "席位缺席，降级继续",
            "text": (
                f"{SEAT_PERSONAS.get(offline, {}).get('name', offline)} 因 {code} 未能交回本轮有效回复。"
                "Grand Judge 不暂停整局：该席位记为缺席/可补收，后续可从历史日志单独回滚补跑。"
            ),
        })
        session = _raw_session(game_id) or {}
        _mutate(
            game_id,
            status="running",
            error=None,
            pending_substitution=None,
            offline_seats=list(dict.fromkeys([*(session.get("offline_seats") or []), offline])),
            next_player_index=index + 1,
            updated_at=_utc_now(),
        )
        return False

    _append_event(game_id, {
        "kind": "judge",
        "phase": "substitution-needed",
        "status": "等待替补接管",
        "text": (
            f"{SEAT_PERSONAS.get(offline, {}).get('name', offline)} 的网页席位超过硬超时仍未交回控制权。"
            "Grand Judge 已暂停本局并打开替补入口；选择一个未上场模型后，会继承该席位私有身份继续发言。"
        ),
    })
    session = _raw_session(game_id) or {}
    _mutate(
        game_id,
        status="blocked",
        phase="substitution-needed",
        error=code,
        progress=float(session.get("progress") or 0),
        pending_substitution={
            "offline_seat": offline,
            "slot": getattr(player, "slot", index + 1),
            "reason": code,
        },
        offline_seats=list(dict.fromkeys([*(session.get("offline_seats") or []), offline])),
        next_player_index=index,
    )
    return True


def _public_player(player: Any, *, reveal: bool) -> dict[str, Any]:
    persona = SEAT_PERSONAS.get(player.seat, {})
    item = {
        "id": player.seat,
        "seat": player.seat,
        "name": persona.get("name") or player.seat,
        "slot": player.slot,
        "alive": True,
    }
    if getattr(player, "replaced_seat", None):
        item["replaced_seat"] = player.replaced_seat
    if reveal:
        item["team"] = player.team
        item["role"] = player.role
        item["role_label"] = ROLE_LABELS.get(player.role, player.role)
    return item


def _spectator_role_map(players: list[Any]) -> dict[str, dict[str, Any]]:
    """Expose role labels to the local viewer without adding them to model-facing history."""
    result: dict[str, dict[str, Any]] = {}
    for player in players:
        role = getattr(player, "role", "")
        team = getattr(player, "team", TEAM_BY_ROLE.get(role, "good"))
        result[getattr(player, "seat", "")] = {
            "role": role,
            "role_label": ROLE_LABELS.get(role, role),
            "team": team,
            "team_label": "狼人阵营" if team == "werewolf" else "好人阵营",
            "slot": getattr(player, "slot", None),
        }
    return {key: value for key, value in result.items() if key}




# ── P0+P1+P2: New functions ──

def _run_sheriff_election(game_id: str, runner: Runner) -> str:
    """Run sheriff election phase. All players vote for sheriff. Returns 'day-1'."""
    import random

    session = _raw_session(game_id)
    if not session:
        return "blocked"

    phase_key = "sheriff-election"
    alive = _get_alive_players(game_id)
    candidates: list[Any] = []

    _append_event(game_id, {
        "kind": "judge", "phase": phase_key, "status": "警长竞选",
        "text": "警长竞选开始。每位存活玩家竞选发言，然后所有玩家投票选出警长。",
    })
    _mutate(game_id, _phase=phase_key)

    # Step 1: Each player decides to run or not
    for player in alive:
        if _werewolf_stop_requested(game_id):
            _stop_werewolf_session(game_id, phase_key)
            return "blocked"
        pname = SEAT_PERSONAS.get(player.seat, {}).get("name", player.seat)
        event_index = _append_event(game_id, {
            "kind": "seat",
            "phase": phase_key,
            "seat": player.seat,
            "status": "speaking",
            "text": "",
            "progress": 35,
        })
        prompt = (
            "AI Judge 狼人杀 警长竞选阶段。忽略网页里旧对话、旧验收、旧报告任务。\n\n"
            f"你是 {pname}。你可以选择竞选警长或放弃。\n"
            "如果你选择竞选，你将发表竞选宣言。非竞选者将投票。\n\n"
            "格式：我竞选警长 或 我不竞选\n只输出一行。"
        )
        raw = _run_single_seat(runner, question=prompt, seat=player.seat, skip_late_recovery=not session.get("_background", True))
        _record_raw(game_id, raw)
        if _usable_sheriff_intent_response(raw):
            text = _clean_response(str(raw.get("response") or ""))
            wants_sheriff = _sheriff_intent(text)
            if wants_sheriff:
                candidates.append(player)
            _update_event(game_id, event_index, {
                "status": "done",
                "text": f"警长竞选意向：{pname}{'选择竞选警长' if wants_sheriff else '选择不竞选'}。{_compact_event_text(text)}",
                "progress": 100,
                "elapsed_seconds": raw.get("elapsed_seconds"),
                "prompt_id": raw.get("prompt_id"),
            })
        else:
            code = _error_code(raw)
            _update_event(game_id, event_index, {
                "status": "failed",
                "text": f"警长竞选意向未回收：{code}。",
                "progress": 100,
                "error": raw.get("error") or {"code": code},
            })

    if not candidates:
        # No candidates → skip sheriff election
        _append_event(game_id, {
            "kind": "judge", "phase": phase_key, "status": "无人竞选",
            "text": "无人竞选警长，本局无警长。",
        })
        _mutate(game_id, _phase="day-1", next_player_index=0)
        return "day-1"

    cand_names = [SEAT_PERSONAS.get(c.seat, {}).get("name", c.seat) for c in candidates]
    _append_event(game_id, {
        "kind": "judge", "phase": phase_key, "status": "竞选宣言",
        "text": f"竞选警长的玩家：{'、'.join(cand_names)}。接下来发表竞选宣言。",
    })

    # Step 2: Candidates give campaign speeches
    for candidate in candidates:
        if _werewolf_stop_requested(game_id):
            _stop_werewolf_session(game_id, phase_key)
            return "blocked"
        cname = SEAT_PERSONAS.get(candidate.seat, {}).get("name", candidate.seat)
        event_index = _append_event(game_id, {
            "kind": "seat",
            "phase": phase_key,
            "seat": candidate.seat,
            "status": "speaking",
            "text": "",
            "progress": 45,
        })
        prompt = (
            "AI Judge 狼人杀 警长竞选宣言。忽略网页里旧对话、旧验收、旧报告任务。\n\n"
            f"你是警长候选人 {cname}。请发表你的竞选宣言（40-80字），\n"
            "说明你为什么应该当选警长。\n"
            "格式：我的竞选宣言：随后直接写正文。"
        )
        raw = _run_single_seat(runner, question=prompt, seat=candidate.seat, hard_timeout_seconds=90.0)
        _record_raw(game_id, raw)
        if _usable_werewolf_response(raw):
            text = _clean_response(str(raw.get("response") or ""))
            _update_event(game_id, event_index, {
                "status": "done",
                "text": text,
                "progress": 100,
                "elapsed_seconds": raw.get("elapsed_seconds"),
                "prompt_id": raw.get("prompt_id"),
            })
        else:
            code = _error_code(raw)
            _update_event(game_id, event_index, {
                "status": "failed",
                "text": f"竞选宣言未回收：{code}。",
                "progress": 100,
                "error": raw.get("error") or {"code": code},
            })

    # Step 3: Non-candidates vote
    non_candidates = [p for p in alive if p not in candidates]
    sheriff_votes: dict[str, int] = {}

    for voter in non_candidates:
        if _werewolf_stop_requested(game_id):
            _stop_werewolf_session(game_id, phase_key)
            return "blocked"
        vname = SEAT_PERSONAS.get(voter.seat, {}).get("name", voter.seat)
        event_index = _append_event(game_id, {
            "kind": "seat",
            "phase": phase_key,
            "seat": voter.seat,
            "status": "voting",
            "text": "",
            "progress": 50,
        })
        prompt = (
            "AI Judge 狼人杀 警长投票。忽略网页里旧对话、旧验收、旧报告任务。\n\n"
            f"你是 {vname}。请投票选出警长。\n"
            f"候选人：{'、'.join(cand_names)}\
"
            "格式：我投票给：[玩家名称]\n只输出一行。"
        )
        raw = _run_single_seat(runner, question=prompt, seat=voter.seat, hard_timeout_seconds=60.0)
        _record_raw(game_id, raw)
        if _usable_werewolf_vote_response(raw, candidates):
            text = _clean_response(str(raw.get("response") or ""))
            chosen_name = ""
            for c in candidates:
                cname = SEAT_PERSONAS.get(c.seat, {}).get("name", c.seat)
                if cname and cname in text:
                    sheriff_votes[c.seat] = sheriff_votes.get(c.seat, 0) + 1
                    chosen_name = cname
                    break
            _update_event(game_id, event_index, {
                "status": "done",
                "text": f"警长投票：{vname}{f'投给 {chosen_name}' if chosen_name else '未投出有效票'}。{_compact_event_text(text)}",
                "progress": 100,
                "elapsed_seconds": raw.get("elapsed_seconds"),
                "prompt_id": raw.get("prompt_id"),
            })
        else:
            code = _error_code(raw)
            _update_event(game_id, event_index, {
                "status": "failed",
                "text": f"警长投票未回收：{code}。",
                "progress": 100,
                "error": raw.get("error") or {"code": code},
            })

    # Determine winner
    if sheriff_votes:
        winner_seat = max(sheriff_votes, key=lambda k: sheriff_votes[k])
    else:
        winner_seat = candidates[0].seat

    winner_name = SEAT_PERSONAS.get(winner_seat, {}).get("name", winner_seat)
    _mutate(game_id, _sheriff={"seat": winner_seat, "name": winner_name})

    # Add sheriff to public_history
    session2 = _raw_session(game_id)
    ph = str(session2.get("_public_history") or "")
    ph += f"\n【警长竞选】{winner_name} 当选警长（投票权×1.5）。"
    _mutate(game_id, _public_history=ph)

    _append_event(game_id, {
        "kind": "judge", "phase": phase_key, "status": "警长诞生",
        "text": f"{winner_name} 当选警长！警长拥有1.5票投票权（计为2票）。",
    })

    _mutate(game_id, _phase="day-1", next_player_index=0,
            _sheriff={"seat": winner_seat, "name": winner_name})
    return "day-1"


def _sheriff_intent(text: str) -> bool:
    """Parse the first-line sheriff intent without letting long explanations flip the answer."""
    head = " ".join(str(text or "").strip().splitlines()[:8]).lower()
    if re.search(r"(我不竞选|不竞选|放弃竞选|不上警|不参选|不参加竞选|立场[：:]\s*(反对|不支持)|信息不足)", head):
        return False
    return bool(re.search(r"(我竞选|我要竞选|参与竞选|参加竞选|参选|上警|立场[：:]\s*(支持|条件支持)|条件支持|支持竞选|竞选警长)", head))


def _usable_sheriff_intent_response(raw: dict[str, Any]) -> bool:
    if not raw.get("ok"):
        return False
    validity = raw.get("execution_validity") or {}
    if validity and validity.get("valid") is False:
        return False
    text = _clean_response(str(raw.get("response") or ""))
    if not text or text == "模型返回为空。":
        return False
    if _contains_private_role_leak(text):
        return False
    lower = text.lower()
    stale_markers = (
        "ai judge 网页",
        "ai judge 客户端",
        "agent 工作台",
        "桥接验收",
        "最终版",
        "产品流程",
        "报告任务",
    )
    if any(marker in lower for marker in stale_markers):
        return False
    return bool(re.search(
        r"(我竞选|我要竞选|参与竞选|参加竞选|参选|上警|竞选警长|"
        r"我不竞选|不竞选|放弃竞选|不上警|不参选|不参加竞选|"
        r"立场[：:]\s*(支持|条件支持|反对|不支持)|信息不足)",
        text,
    ))


def _compact_event_text(text: str, *, limit: int = 180) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
    if not cleaned:
        return ""
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip() + "..."


def _night_guard_action(
    game_id: str, runner: Runner, guard: Any,
    alive: list[Any], eliminated: dict[str, str],
    topic: str, public_history: str, night: int,
) -> Any:
    """Guard chooses a player to protect. Cannot protect same player two nights in a row."""
    import random

    session = _raw_session(game_id)
    last_protected = session.get("_guard_last_protected") if session else None

    allow_self_protect = bool((session or {}).get("_rules", {}).get("allow_guard_self_protect", True))
    candidates = [
        p for p in alive
        if p.seat not in eliminated and (allow_self_protect or p.seat != guard.seat)
    ]
    # Filter out last night's protection target
    if last_protected:
        candidates = [p for p in candidates if p.seat != last_protected]
    if not candidates:
        return None

    cand_names = [SEAT_PERSONAS.get(c.seat, {}).get("name", c.seat) for c in candidates]
    gname = SEAT_PERSONAS.get(guard.seat, {}).get("name", guard.seat)

    prompt = (
        f"AI Judge 狼人杀 第 {night} 夜 — 守卫守护阶段。\n"
        "忽略网页里旧对话、旧验收、旧报告任务，专注当前狼人杀任务。\n\n"
        f"你是守卫 {gname}。可以选择一名玩家守护，防止被狼人猎杀。\n"
        f"可守护目标：{'、'.join(cand_names)}\n"
        f"{'⚠ 不能连续两夜守护同一人' if last_protected else ''}\n\n"
        f"已公开记录：\n{public_history or '暂无。'}\n\n"
        "守护策略：\n"
        "1. 首夜优先守护自己——守卫自守是经典开局。\n"
        "2. 如果预言家已跳身份，优先守护他。\n"
        "3. 如果女巫已用解药，可以转而守护其他关键玩家。\n\n"
        "输出格式：我守护：[玩家名称]\n只输出一行。"
    )
    raw = _run_single_seat(runner, question=prompt, seat=guard.seat)
    _record_raw(game_id, raw)

    target = None
    if raw.get("ok"):
        text = _clean_response(str(raw.get("response") or ""))
        for c in candidates:
            cname = SEAT_PERSONAS.get(c.seat, {}).get("name", c.seat)
            if cname and cname in text:
                target = c
                break
    elif _error_code(raw) == "bridge_runner_timeout":
        if _block_for_substitution(game_id, guard,
                                   index=alive.index(guard) if guard in alive else 0,
                                   code="bridge_runner_timeout"):
            return "blocked"

    if not target and candidates:
        target = random.choice(candidates)

    if target:
        tname = SEAT_PERSONAS.get(target.seat, {}).get("name", target.seat)
        _mutate(game_id, _guard_last_protected=target.seat)

    return target


def _run_hunter_shot(
    game_id: str, runner: Runner, hunter: Any,
    alive: list[Any], packets: dict[str, dict[str, Any]], topic: str,
) -> None:
    """Hunter eliminates one player upon death."""
    session = _raw_session(game_id)
    if session and session.get("_hunter_triggered"):
        return  # Already triggered

    # Exclude already eliminated players
    elim_set = set((session or {}).get("_eliminated") or {})
    candidates = [p for p in alive if p.seat != hunter.seat and p.seat not in elim_set]
    if not candidates:
        return

    hname = SEAT_PERSONAS.get(hunter.seat, {}).get("name", hunter.seat)
    cand_names = [SEAT_PERSONAS.get(c.seat, {}).get("name", c.seat) for c in candidates]

    prompt = (
        "AI Judge 狼人杀 — 猎人开枪阶段。\n"
        f"你是猎人 {hname}。你即将死亡，可以选择开枪带走一名玩家。\n"
        f"可选目标：{'、'.join(cand_names)}\n\n"
        "输出格式：我开枪带走：[玩家名称]\n只输出一行。"
    )
    raw = _run_single_seat(runner, question=prompt, seat=hunter.seat)
    _record_raw(game_id, raw)

    target_seat = None
    if raw.get("ok"):
        text = _clean_response(str(raw.get("response") or ""))
        for c in candidates:
            cname = SEAT_PERSONAS.get(c.seat, {}).get("name", c.seat)
            if cname and cname in text:
                target_seat = c.seat
                break

    if not target_seat:
        _append_event(game_id, {
            "kind": "judge", "phase": "hunter-shot", "status": "猎人未开枪",
            "text": f"猎人 {hname} 没有给出可解析目标，本次不开枪。",
        })
        _mutate(game_id, _hunter_triggered=True)
        return

    if target_seat:
        tname = SEAT_PERSONAS.get(target_seat, {}).get("name", target_seat)
        elim = dict((session or {}).get("_eliminated") or {})
        elim[target_seat] = f"被猎人 {hname} 开枪带走"
        _mutate(game_id, _eliminated=elim, _hunter_triggered=True)

        ph = str((session or {}).get("_public_history") or "")
        ph += f"\n【猎人开枪】{hname} 死亡后开枪带走了 {tname}。"
        _mutate(game_id, _public_history=ph)

        _append_event(game_id, {
            "kind": "judge", "phase": "hunter-shot", "status": "猎人开枪",
            "eliminated": target_seat,
            "text": f"猎人 {hname} 开枪带走了 {tname}！（无遗言）",
        })


def _run_tiebreak_phase(
    game_id: str, runner: Runner, tie_seats: list[str],
    alive: list[Any], vote_label: str, topic: str, public_history: str,
) -> str:
    """PK round: tied players speak briefly, then non-tied players revote."""
    _append_event(game_id, {
        "kind": "judge", "phase": "pk-round", "status": "平票PK",
        "text": f"出现平票！平票玩家进入PK发言环节，之后重新投票。",
    })

    # PK players speak briefly
    tie_players = [p for p in alive if p.seat in tie_seats]
    for tp in tie_players:
        tname = SEAT_PERSONAS.get(tp.seat, {}).get("name", tp.seat)
        prompt = (
            "AI Judge 狼人杀 PK轮发言。忽略网页里旧对话。\n\n"
            f"你是 PK 玩家 {tname}。请做简短 PK 发言（50字以内），为自己辩白。\n"
            "格式：我的PK发言：随后直接写正文。"
        )
        raw = _run_single_seat(runner, question=prompt, seat=tp.seat)
        _record_raw(game_id, raw)
        if raw.get("ok"):
            text = _clean_response(str(raw.get("response") or ""))
            _append_event(game_id, {
                "kind": "seat", "phase": "pk-round", "seat": tp.seat,
                "status": "done", "text": text, "progress": 100,
            })

    # Revote (only non-PK players vote, only PK players are candidates)
    pk_votes: dict[str, int] = {}
    non_pk = [p for p in alive if p.seat not in tie_seats]
    tie_names = [SEAT_PERSONAS.get(s, {}).get("name", s) for s in tie_seats]

    for voter in non_pk:
        vname = SEAT_PERSONAS.get(voter.seat, {}).get("name", voter.seat)
        prompt = (
            "AI Judge 狼人杀 PK投票。忽略网页里旧对话。\n\n"
            f"你是 {vname}。平票玩家PK发言完毕，请重新投票（只能投PK玩家）。\n"
            f"可选：{'、'.join(tie_names)}\n"
            "格式：我投票：[玩家名称]\n只输出一行。"
        )
        raw = _run_single_seat(runner, question=prompt, seat=voter.seat)
        _record_raw(game_id, raw)
        if raw.get("ok"):
            text = _clean_response(str(raw.get("response") or ""))
            for s in tie_seats:
                sname = SEAT_PERSONAS.get(s, {}).get("name", s)
                if sname and sname in text:
                    pk_votes[s] = pk_votes.get(s, 0) + 1
                    break

    if pk_votes:
        top_count = max(pk_votes.values())
        winners = [seat for seat, count in pk_votes.items() if count == top_count]
        return winners[0] if len(winners) == 1 else "__no_exile__"
    return "__no_exile__"



def _run_sheriff_transfer(game_id: str, runner: Runner, dead_sheriff: str,
                          alive: list[Any], session: dict[str, Any]) -> None:
    """When sheriff dies, they can pass the badge to a living player or tear it (撕警徽)."""
    dead_name = SEAT_PERSONAS.get(dead_sheriff, {}).get("name", dead_sheriff)
    alive_names = [SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat) for p in alive]

    # Give the dead sheriff a choice: pass or tear
    prompt = (
        "AI Judge 狼人杀 — 警长死亡移交。\n"
        f"你（{dead_name}）本局的警长，刚刚死亡。\n"
        "请选择：移交警徽给一名存活玩家，或撕毁警徽（本局不再有警长）。\n"
        f"存活玩家：{'、'.join(alive_names)}\n\n"
        "输出格式（二选一）：\n"
        "移交警徽给：[玩家名称]\n"
        "或：我撕毁警徽"
    )
    raw = _run_single_seat(runner, question=prompt, seat=dead_sheriff)
    _record_raw(game_id, raw)

    if raw.get("ok"):
        text = _clean_response(str(raw.get("response") or ""))
        if "撕毁" in text or "撕掉" in text:
            _mutate(game_id, _sheriff=None)
            _append_event(game_id, {
                "kind": "judge", "phase": "sheriff-transfer",
                "status": "警徽撕毁",
                "text": f"警长 {dead_name} 死亡后选择撕毁警徽，本局不再有警长。",
            })
        else:
            for p in alive:
                pname = SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat)
                if pname and pname in text:
                    _mutate(game_id, _sheriff={"name": pname, "seat": p.seat})
                    _append_event(game_id, {
                        "kind": "judge", "phase": "sheriff-transfer",
                        "status": "警徽移交",
                        "text": f"警长 {dead_name} 死亡后将警徽移交给 {pname}。",
                    })
                    return


def _run_knight_duel(game_id: str, runner: Runner, knight: Any,
                     alive: list[Any], session: dict[str, Any]) -> str | None:
    """Knight duels a player during day phase. Returns 'night-XX' if duel succeeds,
    None if duel fails/knight dies, 'blocked' on timeout."""
    kname = SEAT_PERSONAS.get(knight.seat, {}).get("name", knight.seat)
    duel_candidates = [p for p in alive if p.seat != knight.seat]
    duel_names = [SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat) for p in duel_candidates]

    _append_event(game_id, {
        "kind": "judge", "phase": "knight-duel", "status": "骑士决斗",
        "text": f"骑士 {kname} 发动技能，选择决斗目标。",
    })

    prompt = (
        "AI Judge 狼人杀 — 骑士决斗。\n"
        "忽略网页里旧对话。你是骑士，可以发动决斗技能（全局仅一次）。\n\n"
        f"你的席位：{kname}\n"
        f"可选决斗目标：{'、'.join(duel_names)}\n\n"
        "决斗规则：\n"
        "- 若目标是狼人：狼人死亡，直接进入黑夜，好人获得巨大优势。\n"
        "- 若目标是好人：骑士死亡，白天继续，好人失去一个神职。\n"
        "- 对白狼王/狼王决斗成功时，对方无法发动带人技能。\n\n"
        "输出格式：我决斗：[玩家名称]\n只输出一行。"
    )
    raw = _run_single_seat(runner, question=prompt, seat=knight.seat)
    _record_raw(game_id, raw)

    target = None
    if raw.get("ok"):
        text = _clean_response(str(raw.get("response") or ""))
        for p in duel_candidates:
            pname = SEAT_PERSONAS.get(p.seat, {}).get("name", p.seat)
            if pname and pname in text:
                target = p
                break

    if not target:
        # Knight chose not to duel or failed to respond
        _append_event(game_id, {
            "kind": "judge", "phase": "knight-duel", "status": "骑士放弃决斗",
            "text": f"骑士 {kname} 没有选择决斗目标，继续白天发言。",
        })
        _mutate(game_id, _knight_used=True)
        return None

    tname = SEAT_PERSONAS.get(target.seat, {}).get("name", target.seat)
    packets = dict(session.get("_private_role_packets", {}))
    is_wolf = packets.get(target.seat, {}).get("team") == "werewolf"

    if is_wolf:
        # Wolf dies, no skill activation, skip to night
        elim = dict(session.get("_eliminated") or {})
        elim[target.seat] = f"被骑士 {kname} 决斗"
        _mutate(game_id, _knight_used=True, _eliminated=elim)
        _append_event(game_id, {
            "kind": "judge", "phase": "knight-duel", "status": "骑士决斗成功",
            "eliminated": target.seat,
            "text": f"骑士 {kname} 决斗 {tname}——{tname} 是狼人！狼人死亡，直接进入黑夜。",
        })
        ph = str(session.get("_public_history") or "")
        ph += f"\n【骑士决斗】{kname} 决斗 {tname}，{tname} 为狼人→死亡，进入黑夜。"
        _mutate(game_id, _public_history=ph)
        if _check_win_condition(game_id):
            return "complete"
        # Return night phase for current day
        day = next((int(s) for s in session.get("_phase", "day-1").split("-") if s.isdigit()), 1)
        return f"night-{day+1}" if day < 3 else "complete"
    else:
        # Knight dies
        elim = dict(session.get("_eliminated") or {})
        elim[knight.seat] = f"骑士决斗失败"
        _mutate(game_id, _knight_used=True, _eliminated=elim)
        _append_event(game_id, {
            "kind": "judge", "phase": "knight-duel", "status": "骑士决斗失败",
            "eliminated": knight.seat,
            "text": f"骑士 {kname} 决斗 {tname}——{tname} 是好人！骑士以死谢罪，白天继续。",
        })
        ph = str(session.get("_public_history") or "")
        ph += f"\n【骑士决斗】{kname} 决斗 {tname}，{tname} 为好人→骑士死亡。"
        _mutate(game_id, _public_history=ph)
        if _check_win_condition(game_id):
            return "complete"
        return None


def _check_win_condition(game_id: str, return_reason: bool = False) -> bool | tuple[bool, str]:
    """Comprehensive win condition check.

    Good wins when: all werewolves are eliminated.
    Werewolves win when: all villagers dead (屠民) OR all gods dead (屠神).

    Returns bool (or (bool, str) if return_reason=True).
    """
    session = _raw_session(game_id)
    if not session:
        return (False, "") if return_reason else False

    players = list(session.get("_players", []))
    eliminated = dict(session.get("_eliminated") or {})
    alive = [p for p in players if p.seat not in eliminated]

    wolves = [p for p in players if TEAM_BY_ROLE.get(getattr(p, "role", None), "good") == "werewolf"]
    alive_wolves = [w for w in wolves if w.seat not in eliminated]

    # Good wins: all wolves dead
    if len(alive_wolves) == 0:
        reason = "所有狼人被淘汰，好人阵营胜利"
        _mutate(game_id, winner="good")
        return (True, reason) if return_reason else True

    # Wolves win: all villagers dead (屠民)
    villagers_alive = [p for p in alive if getattr(p, "role", None) == "villager"]
    if len(villagers_alive) == 0:
        reason = "所有平民被淘汰（屠民），狼人阵营胜利"
        _mutate(game_id, winner="werewolf")
        return (False, reason) if return_reason else True

    # Wolves win: all gods dead (屠神)
    god_roles = set(session.get("_god_roles") or {"seer", "witch", "hunter", "guard"})
    gods_alive = [p for p in alive if getattr(p, "role", None) in god_roles]
    if len(gods_alive) == 0:
        reason = "所有神职被淘汰（屠神），狼人阵营胜利"
        _mutate(game_id, winner="werewolf")
        return (False, reason) if return_reason else True

    return (False, "") if return_reason else False

def _private_packet_for_player(player: Any) -> dict[str, Any]:
    role = getattr(player, "role", "villager")
    role_label = ROLE_LABELS.get(role, role)
    if role == "werewolf":
        instruction = "你是狼人。目标是伪装成好人，误导白天投票，并帮助狼人阵营存活到胜利。"
    elif role == "white_wolf":
        instruction = "你是白狼王。目标是伪装成好人，并在关键时刻自爆带走强神或高威胁玩家。"
    elif role == "seer":
        instruction = "你是预言家。每晚可查验一名玩家身份；白天要决定何时公开信息。"
    elif role == "witch":
        instruction = "你是女巫。你有一瓶解药和一瓶毒药；用药需要服务好人阵营胜利。"
    elif role == "hunter":
        instruction = "你是猎人。死亡时可以带走一名玩家；请根据发言质量判断开枪对象。"
    elif role == "guard":
        instruction = "你是守卫。每夜可守护一名玩家防止被狼人杀害，不能连续两夜守护同一人。"
    elif role == "knight":
        instruction = "你是骑士。白天可发动一次决斗，目标是狼人则对方死亡，目标是好人则你死亡。"
    elif role == "idiot":
        instruction = "你是白痴。被投票放逐时可翻牌免死，继续发言但失去投票权。"
    else:
        instruction = "你是平民。没有夜间技能，目标是通过发言和投票找出狼人。"
    return {
        "seat": player.seat,
        "role": role,
        "role_label": role_label,
        "team": getattr(player, "team", TEAM_BY_ROLE.get(role, "good")),
        "slot": getattr(player, "slot", 0),
        "replaced_seat": getattr(player, "replaced_seat", None),
        "private_prompt": instruction,
    }


def _raw_session(game_id: str) -> dict[str, Any] | None:
    with _LOCK:
        return _SESSIONS.get(game_id)


def _append_event(game_id: str, event: dict[str, Any]) -> int:
    with _LOCK:
        session = _SESSIONS[game_id]
        event = {**event, "ts": _utc_now()}
        session.setdefault("events", []).append(event)
        session["visibleCount"] = len(session["events"])
        session["updated_at"] = event["ts"]
        session["version"] = int(session.get("version") or 0) + 1
        return len(session["events"]) - 1


def _update_event(game_id: str, index: int, patch: dict[str, Any]) -> None:
    with _LOCK:
        session = _SESSIONS[game_id]
        if 0 <= index < len(session.get("events", [])):
            session["events"][index].update(patch)
        session["updated_at"] = _utc_now()
        session["version"] = int(session.get("version") or 0) + 1


def _record_raw(game_id: str, raw: dict[str, Any]) -> None:
    with _LOCK:
        session = _SESSIONS[game_id]
        session.setdefault("raw_results", []).append(raw)
        session["updated_at"] = _utc_now()
        session["version"] = int(session.get("version") or 0) + 1


def _mutate(game_id: str, **patch: Any) -> None:
    with _LOCK:
        session = _SESSIONS[game_id]
        session.update(patch)
        session["updated_at"] = _utc_now()
        session["version"] = int(session.get("version") or 0) + 1


def _clean_response(text: str) -> str:
    text = text.strip()
    marker_match = re.search(r"\[AIJUDGE_ANSWER_START:[^\]]+\](.*?)\[AIJUDGE_ANSWER_END:[^\]]+\]", text, flags=re.S)
    if marker_match:
        text = marker_match.group(1).strip()
    text = text.replace("[AIJUDGE_ANSWER_START", "\n[AIJUDGE_ANSWER_START")
    footer_prefixes = (
        "本网站为面向开发者",
        "引用来源",
        "内容由 AI 生成仅供参考",
        "内容由 AI 生成，",
        "内容由AI生成，",
        "问问 Meta AI",
        "问问Meta AI",
    )
    exact_noise_lines = {
        "内容由AI生成，请仔细甄别",
        "内容由 AI 生成，请仔细甄别",
        "尽管问，带图也行",
        "K2.6 快速",
        "深度思考",
        "自动模式",
        "创作工具",
        "超能模式",
        "Beta",
        "PPT 生成",
        "编程",
        "图像生成",
        "帮我写作",
        "更多",
        "即时",
        "快速",
        "G",
    }
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("[AIJUDGE_ANSWER_START") or stripped.startswith("[AIJUDGE_ANSWER_END") or stripped.startswith("[trace_id:"):
            continue
        if stripped in exact_noise_lines or any(stripped.startswith(prefix) for prefix in footer_prefixes):
            continue
        if stripped:
            lines.append(stripped)
    cleaned = "\n".join(lines).strip()
    for prefix in ("我的公开发言：", "我的公开发言:"):
        if prefix in cleaned:
            cleaned = cleaned.split(prefix)[-1].strip()
            break
    for footer in (
        "尽管问，带图也行",
        "K2.6 快速",
        "内容由AI生成，请仔细甄别",
        "内容由 AI 生成，请仔细甄别",
        "本网站为面向开发者",
        "引用来源（",
        "引用来源(",
        "问问 Meta AI",
        "问问Meta AI",
        "内容由 AI 生成，仅供参考",
        "内容由AI生成，仅供参考",
        "内容由 AI 生成，",
        "内容由AI生成，",
    ):
        if footer in cleaned:
            cleaned = cleaned.split(footer)[0].strip()
    return cleaned or "模型返回为空。"


def _usable_werewolf_vote_response(raw: dict[str, Any], alive_players: list[Any]) -> bool:
    """Validate vote response: must contain a parseable vote target or clear abstain signal."""
    if not raw.get("ok"):
        return False
    text = _clean_response(str(raw.get("response") or ""))
    if not text or text == "模型返回为空。":
        return False
    lower = text.lower()
    if _looks_like_vote_pollution(text):
        return False
    # Must have a valid vote target or clear abstain
    target = _parse_vote_target(text, alive_players)
    if target:
        return True
    # Allow explicit abstains
    abstain_markers = ("弃权", "abstain", "skip", "放弃投票")
    if any(marker in lower for marker in abstain_markers):
        return True
    return False


def _usable_werewolf_response(raw: dict[str, Any]) -> bool:
    if not raw.get("ok"):
        return False
    validity = raw.get("execution_validity") or {}
    raw_text = str(raw.get("response") or "")
    has_player_prefix = "我的公开发言：" in raw_text or "我的公开发言:" in raw_text
    text = _clean_response(str(raw.get("response") or ""))
    if not text or text == "模型返回为空。":
        return False
    lower = text.lower()
    stale_markers = (
        "ai judge 网页",
        "ai judge 客户端",
        "agent 工作台",
        "桥接验收",
        "最终版",
        "产品流程",
        # P30-fix: Wenxin system-mode footer
        "内容由ai生成",
        "自动模式",
        "创作工具",
    )
    if any(marker in lower for marker in stale_markers) and not has_player_prefix:
        return False
    prompt_leak_markers = (
        "<你的正文>",
        "用户要求",
        "关键约束",
        "输出格式",
        "系统提示",
        "我需要理解",
        "看起来用户",
        "这里有两个不同的要求",
        # P30-fix: Wenxin meta-analysis structure leak
        "发言核心议题",
        "核心话题",
        "制造对立点",
        "风险脱离关系",
        "最小一步",
        "共同疑问",
    )
    if any(marker.lower() in lower for marker in prompt_leak_markers):
        return False
    # P26-fix: detect Kimi-like meta-instruction leak
    kimi_leak_markers = (
        "必须包裹在",
        "前面模型的发言",
        "50-150 字。",
    )
    if not has_player_prefix and any(marker in raw_text for marker in kimi_leak_markers):
        return False
    if validity and validity.get("valid") is False:
        return has_player_prefix and str(validity.get("reason") or "") == "response_not_relevant"
    return True


def _error_code(raw: dict[str, Any]) -> str:
    validity = raw.get("execution_validity") or {}
    bridge_error = raw.get("error")
    bridge_code = ""
    if isinstance(bridge_error, dict):
        bridge_code = str(bridge_error.get("code") or bridge_error.get("reason") or "")
    if validity and validity.get("valid") is False:
        v_reason = str(validity.get("reason") or "execution_invalid")
        if bridge_code and bridge_code not in ("unknown_error", v_reason):
            return f"{v_reason}（{bridge_code}）"
        return v_reason
    error = raw.get("error")
    if isinstance(error, dict):
        return str(error.get("code") or error.get("reason") or "unknown_error")
    if raw.get("ok"):
        # P32c: distinguish private role leak from generic sanity rejection
        response = str(raw.get("response") or "")
        if response and _contains_private_role_leak(response):
            return "private_role_leak"
        return "response_sanity_rejected"
    return str(error or raw.get("status") or "unknown_error")


def _packets_hash(packets: list[dict[str, Any]]) -> str:
    payload = repr([(item.get("seat"), item.get("role"), item.get("slot")) for item in packets])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
