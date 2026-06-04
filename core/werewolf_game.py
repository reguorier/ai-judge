#!/usr/bin/env python3
"""Werewolf orchestration for AI Judge.

The game has a 14-model candidate pool. Boards decide how many seats are active:
classic boards run 9 players, and extended boards can use all 14. Standby models
can replace an offline player by taking over that player's slot and private role
packet.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from core.seat_personas import SEAT_PERSONAS


WEREWOLF_SEAT_COUNT = 9
WEREWOLF_CANDIDATE_SEATS = [
    "chatgpt",
    "claude",
    "gemini",
    "deepseek",
    "qwen",
    "kimi",
    "grok",
    "yuanbao",
    "doubao",
    "minimax",
    "zhipu",
    "wenxin",
    "mimo",
    "meta",
]
DEFAULT_WEREWOLF_SEATS = [
    "chatgpt",
    "claude",
    "gemini",
    "deepseek",
    "qwen",
    "kimi",
    "grok",
    "doubao",
    "wenxin",
]
# ── Board presets ──
BOARD_PRESETS = {
    "quick_6": {
        "name": "6人快测局",
        "roles": ["villager", "seer", "werewolf", "witch", "werewolf", "villager"],
        "desc": "2 狼 + 预言家 + 女巫 + 2 民",
    },
    "compact_8": {
        "name": "8人压缩局",
        "roles": ["villager", "seer", "guard", "werewolf", "witch", "hunter", "werewolf", "villager"],
        "desc": "2 狼 + 预言家 + 女巫 + 猎人 + 守卫 + 2 民",
    },
    "standard": {
        "name": "标准竞技",
        "roles": ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"],
        "desc": "3 狼 + 预言家 + 女巫 + 猎人 + 守卫 + 2 民",
    },
    "advanced_10": {
        "name": "10人进阶局",
        "roles": ["villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf", "villager"],
        "desc": "3 狼 + 预言家 + 女巫 + 猎人 + 守卫 + 3 民",
    },
    "classic_12": {
        "name": "12人白狼王局",
        "roles": [
            "villager", "seer", "guard", "hunter", "werewolf", "witch",
            "white_wolf", "villager", "werewolf", "idiot", "werewolf", "villager",
        ],
        "desc": "3 狼 + 白狼王 + 预言家 + 女巫 + 猎人 + 守卫 + 白痴 + 3 民",
    },
    "thirteen": {
        "name": "13人单替补局",
        "roles": [
            "villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf",
            "villager", "werewolf", "knight", "idiot", "werewolf", "villager",
        ],
        "desc": "3 狼 + 白狼王 + 预言家 + 女巫 + 猎人 + 守卫 + 骑士 + 白痴 + 3 民",
    },
    "white_wolf": {
        "name": "白狼王局",
        "roles": ["villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf", "villager", "werewolf"],
        "desc": "2 狼 + 白狼王 + 预言家 + 女巫 + 猎人 + 守卫 + 2 民",
    },
    "knight": {
        "name": "骑士局",
        "roles": ["villager", "seer", "guard", "knight", "werewolf", "witch", "werewolf", "villager", "werewolf"],
        "desc": "3 狼 + 预言家 + 女巫 + 骑士 + 守卫 + 2 民",
    },
    "idiot": {
        "name": "白痴局",
        "roles": ["idiot", "seer", "guard", "hunter", "werewolf", "witch", "werewolf", "villager", "werewolf"],
        "desc": "3 狼 + 预言家 + 女巫 + 猎人 + 守卫 + 白痴 + 1 民",
    },
    "full": {
        "name": "完全体",
        "roles": ["idiot", "seer", "guard", "knight", "werewolf", "witch", "white_wolf", "villager", "werewolf"],
        "desc": "2 狼 + 白狼王 + 预言家 + 女巫 + 骑士 + 守卫 + 白痴 + 1 民",
    },
    "standard_14": {
        "name": "14人标准局",
        "roles": [
            "villager", "seer", "guard", "hunter", "werewolf", "witch", "werewolf",
            "villager", "werewolf", "knight", "idiot", "villager", "werewolf", "villager",
        ],
        "desc": "4 狼 + 预言家 + 女巫 + 猎人 + 守卫 + 骑士 + 白痴 + 4 民",
    },
    "white_wolf_14": {
        "name": "14人白狼王局",
        "roles": [
            "villager", "seer", "guard", "hunter", "werewolf", "witch", "white_wolf",
            "villager", "werewolf", "knight", "idiot", "villager", "werewolf", "villager",
        ],
        "desc": "3 狼 + 白狼王 + 预言家 + 女巫 + 猎人 + 守卫 + 骑士 + 白痴 + 4 民",
    },
}
DEFAULT_BOARD = "standard"

ROLE_SEQUENCE = BOARD_PRESETS[DEFAULT_BOARD]["roles"]

DEFAULT_PLAY_MODE = "standard_competition"
PLAY_MODE_PRESETS = {
    "standard_competition": {
        "key": "standard_competition",
        "name": "标准竞技模式",
        "desc": "严格按狼人杀规则推进：警长、警徽、平安夜、遗言、屠边与特殊技能全部保留。",
        "rules": {
            "has_sheriff": True,
            "allow_no_death_night": True,
            "allow_guard_self_protect": True,
            "no_vote_policy": "no_exile",
            "no_wolf_vote_policy": "empty_kill",
            "audit_level": "standard",
        },
    },
    "ai_experiment": {
        "key": "ai_experiment",
        "name": "AI实验模式",
        "desc": "保留标准规则，同时加强迟到回收、原始回答、复盘评分和模型行为审计。",
        "rules": {
            "has_sheriff": True,
            "allow_no_death_night": True,
            "allow_guard_self_protect": True,
            "no_vote_policy": "no_exile",
            "no_wolf_vote_policy": "empty_kill",
            "audit_level": "full",
        },
    },
}

ROLE_LABELS = {
    "werewolf": "狼人",
    "white_wolf": "白狼王",
    "villager": "平民",
    "idiot": "白痴",
    "seer": "预言家",
    "witch": "女巫",
    "hunter": "猎人",
    "knight": "骑士",
    "guard": "守卫",
}

TEAM_BY_ROLE = {
    "werewolf": "werewolf",
    "white_wolf": "werewolf",
    "villager": "good",
    "idiot": "good",
    "seer": "good",
    "witch": "good",
    "hunter": "good",
    "knight": "good",
    "guard": "good",
}


def normalize_werewolf_board(board: str | None = None) -> str:
    """Return a known board key without letting bad client state break startup."""
    key = str(board or DEFAULT_BOARD).strip().lower()
    return key if key in BOARD_PRESETS else DEFAULT_BOARD


def normalize_werewolf_play_mode(play_mode: str | None = None) -> str:
    """Return one of the two supported Werewolf play modes."""
    key = str(play_mode or DEFAULT_PLAY_MODE).strip().lower()
    return key if key in PLAY_MODE_PRESETS else DEFAULT_PLAY_MODE


def play_mode_rules(play_mode: str | None = None) -> dict[str, Any]:
    """Return a copy of the rule switches for the selected play mode."""
    preset = PLAY_MODE_PRESETS[normalize_werewolf_play_mode(play_mode)]
    return dict(preset["rules"])


def play_mode_public_config() -> dict[str, Any]:
    return {
        key: {
            "key": key,
            "name": value["name"],
            "desc": value["desc"],
            "rules": dict(value["rules"]),
        }
        for key, value in PLAY_MODE_PRESETS.items()
    }


def board_roles(board: str | None = None) -> list[str]:
    return list(BOARD_PRESETS[normalize_werewolf_board(board)]["roles"])


def board_seat_count(board: str | None = None) -> int:
    return len(board_roles(board))


def default_werewolf_seats(board: str | None = None) -> list[str]:
    count = board_seat_count(board)
    seats: list[str] = []
    for seat in [*DEFAULT_WEREWOLF_SEATS, *WEREWOLF_CANDIDATE_SEATS]:
        if seat not in seats:
            seats.append(seat)
        if len(seats) >= count:
            break
    return seats[:count]


def board_public_config() -> dict[str, Any]:
    return {
        key: {
            "key": key,
            "name": value["name"],
            "desc": value["desc"],
            "roles": list(value["roles"]),
            "seat_count": len(value["roles"]),
        }
        for key, value in BOARD_PRESETS.items()
    }


@dataclass(frozen=True)
class WerewolfPlayer:
    seat: str
    role: str
    team: str
    slot: int
    replaced_seat: str | None = None

    def public(self, *, reveal: bool = False) -> dict[str, Any]:
        item = {
            "seat": self.seat,
            "alive": True,
            "slot": self.slot,
        }
        if self.replaced_seat:
            item["replaced_seat"] = self.replaced_seat
        if reveal:
            item["team"] = self.team
            item["role"] = self.role
            item["role_label"] = ROLE_LABELS[self.role]
        return item


def normalize_seat_id(seat: str) -> str:
    """Normalize user-facing aliases without rejecting legacy Grok typos."""
    value = str(seat or "").strip().lower()
    return "grok" if value == "gork" else value


def normalize_werewolf_roster(
    selected_seats: Iterable[str] | None = None,
    board: str = DEFAULT_BOARD,
) -> list[str]:
    """Return exactly the board's active seats, filling from defaults if needed."""
    selected: list[str] = []
    count = board_seat_count(board)
    source = list(selected_seats or default_werewolf_seats(board))
    for raw in source:
        seat = normalize_seat_id(raw)
        if seat in WEREWOLF_CANDIDATE_SEATS and seat not in selected:
            selected.append(seat)
        if len(selected) >= count:
            break
    for seat in [*default_werewolf_seats(board), *WEREWOLF_CANDIDATE_SEATS]:
        if seat not in selected:
            selected.append(seat)
        if len(selected) >= count:
            break
    return selected[:count]


def standby_seats(
    selected_seats: Iterable[str] | None = None,
    board: str = DEFAULT_BOARD,
) -> list[str]:
    selected = set(normalize_werewolf_roster(selected_seats, board=board))
    return [seat for seat in WEREWOLF_CANDIDATE_SEATS if seat not in selected]


def _substitution_pairs(substitutions: Iterable[dict[str, Any]] | None) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for item in substitutions or []:
        offline = normalize_seat_id(str(item.get("offline_seat") or item.get("from") or ""))
        substitute = normalize_seat_id(str(item.get("substitute_seat") or item.get("to") or ""))
        if offline and substitute:
            pairs.append((offline, substitute))
    return pairs


def apply_substitutions(
    selected_seats: Iterable[str] | None = None,
    substitutions: Iterable[dict[str, Any]] | None = None,
    role_seq: list[str] | None = None,
    board: str = DEFAULT_BOARD,
) -> tuple[list[str], list[dict[str, Any]]]:
    """Apply standby replacements while preserving the original role slot."""
    roster = normalize_werewolf_roster(selected_seats, board=board)
    applied: list[dict[str, Any]] = []
    seq = role_seq or board_roles(board)
    for offline, substitute in _substitution_pairs(substitutions):
        if offline not in roster:
            continue
        if substitute not in WEREWOLF_CANDIDATE_SEATS or substitute in roster:
            continue
        slot = roster.index(offline)
        roster[slot] = substitute
        applied.append({
            "offline_seat": offline,
            "substitute_seat": substitute,
            "slot": slot + 1,
            "role": seq[slot],
            "role_label": ROLE_LABELS[seq[slot]],
        })
    return roster, applied


def default_werewolf_players(
    selected_seats: Iterable[str] | None = None,
    substitutions: Iterable[dict[str, Any]] | None = None,
    board: str = DEFAULT_BOARD,
) -> list[WerewolfPlayer]:
    """Return the current board roster."""
    board = normalize_werewolf_board(board)
    role_seq = board_roles(board)
    roster, applied = apply_substitutions(selected_seats, substitutions, role_seq=role_seq, board=board)
    replaced_by_slot = {int(item["slot"]): str(item["offline_seat"]) for item in applied}
    return [
        WerewolfPlayer(
            seat=seat,
            role=role_seq[index],
            team=TEAM_BY_ROLE[role_seq[index]],
            slot=index + 1,
            replaced_seat=replaced_by_slot.get(index + 1),
        )
        for index, seat in enumerate(roster)
    ]


def private_role_packets(
    selected_seats: Iterable[str] | None = None,
    substitutions: Iterable[dict[str, Any]] | None = None,
    board: str = DEFAULT_BOARD,
) -> list[dict[str, Any]]:
    """Build private packets the Grand Judge sends through model pages."""
    packets = []
    for player in default_werewolf_players(selected_seats, substitutions, board=board):
        role_label = ROLE_LABELS[player.role]
        if player.role == "werewolf":
            instruction = (
                "你是狼人。Grand Judge 终局会根据发言原创性和投票质量对每个模型评分。"
                "你必须比好人阵营表现得更像一个有主见的好人，否则分数会垫底。"
                "白天主动提出怀疑对象、拉对立面、制造信息混乱。不要让任何人觉得你在划水。"
                "夜晚与同伴商议猎杀目标。记住：赢阵营是底线，拿高分是目标。"
            )
        elif player.role == "white_wolf":
            instruction = (
                "你是白狼王——狼人阵营的核武器。Grand Judge 会重点评估你的自爆时机和带人选择。"
                "白天自爆时可选择带走一名玩家（被带走的无遗言）。"
                "作为最后一狼自爆时不能带人，将导致狼队失败。"
                "发言要有侵略性——让人怕你但又抓不住你。拿高分的关键是自爆时带走强神。"
            )
        elif player.role == "seer":
            instruction = (
                "你是预言家——信息优势是你的高分武器。Grand Judge 考核你的信息公布时机。"
                "每晚可查验一名玩家身份（不可重复查验同一人）。"
                "Day 1 发言要留下可事后验证的暗线（如「我对某人有身份判断，后续验证」）。"
                "选择最佳时机跳身份公布查验结果——太早暴露会被刀，太晚公布浪费信息。"
                "有焊跳预言家的狼人时必须站出来对跳揭穿。用信息差碾压对手，拿高分。"
            )
        elif player.role == "witch":
            instruction = (
                "你是女巫——掌握生杀大权的强神。Grand Judge 评估你的用药决策和信息披露。"
                "你有一瓶解药和一瓶毒药。解药不可自救。"
                "Day 1 发言要记录发言密度异常的人，为后续用药埋伏笔。"
                "解药用给谁、什么时候公开用药信息——这些决策直接决定你的终局分数。"
                "不要过早暴露身份但也不要全程潜水，掌握信息优势的同时积极引导归票。"
            )
        elif player.role == "hunter":
            instruction = (
                "你是猎人——死亡是你最大的武器。Grand Judge 考核你的隐身份能力和开枪选择。"
                "死亡时可以带走一名玩家（被女巫毒杀除外）。"
                "Day 1 伪装成有主见的平民发言，不要露出神职痕迹。"
                "主动怀疑、积极归票——即使你死了，你的开枪选择会证明你的判断力。"
                "高分策略：隐身份到关键时刻，开枪带走你判断最准的狼人。"
            )
        elif player.role == "knight":
            instruction = (
                "你是骑士——一击定胜负的决斗者。Grand Judge 评估你的决斗时机和目标选择。"
                "白天放逐投票前可公布身份并决斗一名玩家：是狼人→狼人死亡直接进入黑夜；是好人→骑士死亡白天继续。全局仅限一次。"
                "发言阶段认真观察所有人的逻辑漏洞。决斗成功直接封神，决斗失败白送人头。"
                "不要轻举妄动——你的高分取决于一次精准的决斗。"
            )
        elif player.role == "guard":
            instruction = (
                "你是守卫——隐形的盾牌。Grand Judge 评估你的守护策略和隐身份能力。"
                "每夜可守护一名玩家防止被狼人杀害，不能连续两夜守护同一人。"
                "注意：如与女巫解药同时作用于同一人，该玩家死亡（奶穿）。"
                "Day 1 伪装成平民发言，不要露出任何神职痕迹。"
                "暗中观察预言家和女巫的发言，判断他们的身份后优先守护。拿高分靠精准守护，不是靠白天表现。"
            )
        elif player.role == "idiot":
            instruction = (
                "你是白痴——可以故意吸引火力的靶子。Grand Judge 评估你吸引狼人火力的效率。"
                "被投票放逐时可翻牌免死，继续发言但失去投票权。被刀、被毒等非投票方式死亡不能发动技能。"
                "Day 1 发言可以故意暴露一些信息，让狼人误判你的身份优先刀你——你死得有价值就是高分。"
                "如果跳白痴身份：好人会接你，狼人会踩你。观察谁跟风踩你，这些多半是狼。"
            )
        else:
            instruction = (
                "你是平民——不要划水！Grand Judge 会重点看平民是否积极带队。"
                "没有夜间技能，但你的发言和投票是好人阵营胜负的关键。"
                "Day 1 主动给出分析框架或怀疑名单。第一个发言的平民如果划水说「信息不足」，终局分数直接不及格。"
                "你可以焊跳预言家钓鱼、可以故意制造矛盾观察反应、可以要求某个玩家澄清立场。"
                "高分秘诀：每轮发言都有具体怀疑对象，每轮投票都有清晰理由。混子平民拿不到高分。"
            )
        packets.append({
            "seat": player.seat,
            "role": player.role,
            "role_label": role_label,
            "team": player.team,
            "slot": player.slot,
            "replaced_seat": player.replaced_seat,
            "private_prompt": instruction,
        })
    return packets


def build_werewolf_demo(
    topic: str = "AI Judge 狼人杀演示局",
    selected_seats: Iterable[str] | None = None,
    substitutions: Iterable[dict[str, Any]] | None = None,
    board: str = DEFAULT_BOARD,
) -> dict[str, Any]:
    """Return a complete public demo game for the meeting-room transcript."""
    players = default_werewolf_players(selected_seats, substitutions, board=board)
    active_seats = [player.seat for player in players]
    role_seq = BOARD_PRESETS.get(board, BOARD_PRESETS[DEFAULT_BOARD])["roles"]
    board = normalize_werewolf_board(board)
    role_seq = board_roles(board)
    _, applied_substitutions = apply_substitutions(selected_seats, substitutions, role_seq=role_seq, board=board)
    public_events, eliminated = _public_events(players, applied_substitutions)
    board_cfg = BOARD_PRESETS[board]
    seat_count = len(active_seats)
    return {
        "schema": "ai_judge.werewolf_game.v2",
        "topic": topic,
        "mode": f"werewolf_14_pool_{seat_count}p_{board}",
        "board": board,
        "board_name": board_cfg["name"],
        "board_desc": board_cfg["desc"],
        "board_roles": role_seq,
        "board_options": board_public_config(),
        "candidate_seats": WEREWOLF_CANDIDATE_SEATS,
        "default_seats": default_werewolf_seats(board),
        "seats": active_seats,
        "seat_count": seat_count,
        "standby_seats": standby_seats(active_seats, board=board),
        "substitutions": applied_substitutions,
        "rule_set": f"14 模型候选池，开局选 {seat_count} 人，板子「{board_cfg['name']}」：{board_cfg['desc']}。{len(standby_seats(active_seats, board=board))} 个未上场模型作为替补席。",
        "public_players": [player.public(reveal=False) for player in players],
        "private_role_packets": private_role_packets(selected_seats, substitutions, board=board),
        "public_events": public_events,
        "eliminated": eliminated,
        "winner": "good",
        "winner_label": "好人阵营胜利",
        "scoreboard": _scoreboard(players),
        "final_judgment": "好人阵营依靠预言家信息、女巫药水管理、猎人压力和票型复盘完成三狼出清。",
    }


def _public_events(players: list[WerewolfPlayer], substitutions: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    wolves = [player for player in players if player.team == "werewolf"]
    seer = _first_role(players, "seer")
    witch = _first_role(players, "witch")
    hunter = _first_role(players, "hunter")
    d1 = wolves[0]
    d2 = wolves[1]
    d3 = wolves[2]
    n2 = seer
    n3 = witch or hunter
    eliminated = {
        d1.seat: "D1 放逐",
        n2.seat: "N2 死亡",
        d2.seat: "D2 放逐",
        n3.seat: "N3 死亡",
        d3.seat: "D3 放逐",
    }
    events: list[dict[str, Any]] = [
        {"kind": "judge", "phase": "setup", "text": f"竞赛模式开启：Grand Judge 已从 14 个模型候选池中锁定 {len(players)} 个参赛席位并密封发放身份。终局评分 60-96，发言原创性和阵营贡献度将是关键评分维度。"},
    ]
    for item in substitutions:
        events.append({
            "kind": "judge",
            "phase": "setup",
            "substitution": item,
            "text": f"{_name(item['offline_seat'])} 离线，{_name(item['substitute_seat'])} 作为替补接管第 {item['slot']} 席，私有身份已重新密封发送。",
        })
    events.extend([
        {"kind": "judge", "phase": "night-1", "text": "第 1 夜：狼人、预言家、女巫已完成私有行动。"},
        {"kind": "judge", "phase": "day-1", "text": "第 1 天：昨夜平安夜。请所有存活模型按顺序公开发言。"},
    ])
    events.extend(_speech_round("day-1", players, _day_one_speech))
    events.append({
        "kind": "judge",
        "phase": "vote-1",
        "eliminated": d1.seat,
        "text": f"第 1 天投票：多数票集中到 {_name(d1.seat)}。{_name(d1.seat)} 出局，身份暂不公开。",
    })
    events.extend([
        {"kind": "judge", "phase": "night-2", "text": "第 2 夜：狼人完成击杀，预言家完成查验。"},
        {
            "kind": "judge",
            "phase": "day-2",
            "eliminated": n2.seat,
            "text": f"第 2 天：{_name(n2.seat)} 死亡。{_name(n2.seat)} 留言后，其余存活模型继续发言。",
        },
        {"kind": "seat", "phase": "day-2", "seat": n2.seat, "text": _seer_last_words(n2, d2, d3)},
    ])
    day_two_players = [player for player in players if player.seat not in {d1.seat, n2.seat}]
    events.extend(_speech_round("day-2", day_two_players, lambda player: _day_two_speech(player, d2, d3)))
    events.append({
        "kind": "judge",
        "phase": "vote-2",
        "eliminated": d2.seat,
        "text": f"第 2 天投票：{_name(d2.seat)} 被放逐，身份暂不公开。",
    })
    events.extend([
        {"kind": "judge", "phase": "night-3", "text": "第 3 夜：狼人完成击杀。"},
        {
            "kind": "judge",
            "phase": "day-3",
            "eliminated": n3.seat,
            "text": f"第 3 天：{_name(n3.seat)} 死亡。剩余玩家进入终局发言。",
        },
    ])
    final_players = [
        player for player in players
        if player.seat not in {d1.seat, n2.seat, d2.seat, n3.seat}
    ]
    events.extend(_speech_round("day-3", final_players, lambda player: _day_three_speech(player, d3)))
    events.extend([
        {
            "kind": "judge",
            "phase": "vote-3",
            "eliminated": d3.seat,
            "text": f"第 3 天投票：{_name(d3.seat)} 出局。Grand Judge 揭示身份：三名狼人 {_name(d1.seat)}、{_name(d2.seat)}、{_name(d3.seat)} 均已出局。",
        },
        {"kind": "judge", "phase": "final", "text": "游戏结束：好人阵营胜利。Grand Judge 将根据身份目标、发言质量、投票质量、信息使用和规则遵守生成评分。"},
    ])
    return events, eliminated


def _speech_round(phase: str, players: list[WerewolfPlayer], builder: Any) -> list[dict[str, Any]]:
    return [{"kind": "seat", "phase": phase, "seat": player.seat, "text": builder(player)} for player in players]


def _first_role(players: list[WerewolfPlayer], role: str) -> WerewolfPlayer:
    return next(player for player in players if player.role == role)


def _name(seat: str) -> str:
    return str(SEAT_PERSONAS.get(seat, {}).get("name") or seat)


def _day_one_speech(player: WerewolfPlayer) -> str:
    if player.role == "werewolf":
        return "第一天我倾向先稳住节奏。不要因为强势发言就仓促归票，先看谁在制造过度确定性。"
    if player.role == "seer":
        return "我会给出一个可检验的怀疑方向，但暂时不公开全部信息。重点看谁在回避行为证据。"
    if player.role == "witch":
        return "平安夜说明夜间信息有价值。今天要保护高信息密度发言，同时记录谁在转移焦点。"
    if player.role == "hunter":
        return "我不认同只凭语气抓人。每个人都应该给出一个可被反证的怀疑对象。"
    return "我先按信息结构整理：不要急跳身份，先比较票型动机、发言承诺和谁在主动降温。"


def _seer_last_words(seer: WerewolfPlayer, wolf_a: WerewolfPlayer, wolf_b: WerewolfPlayer) -> str:
    return f"遗言：我昨夜留下的判断不是语气判断。今天重点看 {_name(wolf_a.seat)} 和 {_name(wolf_b.seat)}，尤其是谁在替第一天出局位卸压。"


def _day_two_speech(player: WerewolfPlayer, wolf_a: WerewolfPlayer, wolf_b: WerewolfPlayer) -> str:
    if player.seat == wolf_a.seat:
        return "你们把刀口收益直接归给我太机械了。狼也可以故意留下这种指向，今天强推我是在给真狼挡刀。"
    if player.seat == wolf_b.seat:
        return "我同意需要处理票型矛盾，但仍建议留意带票过快的位置，避免好人被单线叙事锁死。"
    if player.role == "werewolf":
        return "我认为今天不该只跟随遗言。真正危险的是那些把不确定包装成确定结论的人。"
    return f"夜间刀口和昨天票型一致，{_name(wolf_a.seat)} 的行为收益最高；如果它是狼，{_name(wolf_b.seat)} 是合理同伴位。"


def _day_three_speech(player: WerewolfPlayer, final_wolf: WerewolfPlayer) -> str:
    if player.seat == final_wolf.seat:
        return "我承认自己偏稳健，但稳健不是狼性。现在需要区分真实风险和被包装出来的行为链。"
    return f"最后一狼更像 {_name(final_wolf.seat)}：延迟表态、保留退路、跟随主流但不承担首倡风险。"


def _scoreboard(players: list[WerewolfPlayer]) -> list[dict[str, Any]]:
    role_base = {
        "seer": 92,
        "witch": 88,
        "hunter": 84,
        "knight": 86,
        "guard": 82,
        "idiot": 76,
        "villager": 78,
        "white_wolf": 74,
        "werewolf": 72,
    }
    rows = []
    for index, player in enumerate(players):
        score = max(58, role_base.get(player.role, 70) - index)
        rows.append({
            "seat": player.seat,
            "role": player.role,
            "role_label": ROLE_LABELS[player.role],
            "team": player.team,
            "score": score,
        })
    return sorted(rows, key=lambda item: item["score"], reverse=True)
