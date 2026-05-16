#!/usr/bin/env python3
"""AI Judge v3.4 Feishu bot.

Commands:
  /judge <question>              # Flash by default
  /judge --mode strategic <q>
  /flash <question>
  /standard <question>
  /strategic <question>
  /status <run_id>
  /seats
  /help

The bot is automatic: it returns a verdict card instead of asking users to
manually copy prompts into external models. Strategic tasks are accepted quickly
and completed through the same Feishu webhook when finished.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from bridges.notification_gateway import generate_secure_view_url, notify_verdict_ready
from core.async_task_manager import TaskManager
from core.auto_jury import run_auto_jury
from core.modes import list_modes, resolve_mode
from core.seat_personas import SEAT_PERSONAS

TASKS = TaskManager()


def handle_feishu_message(msg: dict[str, Any], webhook_url: str) -> dict[str, Any] | None:
    text = _extract_text(msg).strip()
    if not text:
        return None

    if text.startswith("/help"):
        return build_help_card()
    if text.startswith("/seats"):
        return build_seats_card()
    if text.startswith("/status"):
        parts = text.split(maxsplit=1)
        return build_status_card(parts[1].strip() if len(parts) > 1 else "")

    mode, question = _parse_mode_command(text)
    if not question:
        return build_error_card("请提供问题。示例：/judge --mode standard 这个方案值得做吗？")

    if mode == "strategic":
        run_id = TASKS.submit(question=question, mode=mode, seats=resolve_mode(mode)["seats"])
        _start_strategic_worker(run_id, question, mode, webhook_url)
        return build_accepted_card(run_id, question, mode)

    try:
        verdict = run_auto_jury(question=question, mode=mode)
    except Exception as exc:
        return build_error_card(str(exc))
    return build_verdict_card(verdict)


def _extract_text(msg: dict[str, Any]) -> str:
    if "text" in msg:
        return str(msg.get("text") or "")
    content = msg.get("content")
    if isinstance(content, str):
        try:
            parsed = json.loads(content)
            return str(parsed.get("text") or content)
        except json.JSONDecodeError:
            return content
    message = msg.get("message", {})
    if isinstance(message, dict):
        return _extract_text(message)
    return ""


def _parse_mode_command(text: str) -> tuple[str, str]:
    text = text.strip()
    aliases = {
        "/flash": "flash",
        "/standard": "standard",
        "/strategic": "strategic",
    }
    for prefix, mode in aliases.items():
        if text == prefix or text.startswith(prefix + " "):
            return mode, text[len(prefix):].strip()

    if text.startswith("/judge"):
        rest = text[len("/judge"):].strip()
        mode = "flash"
        if rest.startswith("--mode"):
            parts = rest.split(maxsplit=2)
            if len(parts) >= 2:
                mode = parts[1].lower()
                rest = parts[2] if len(parts) >= 3 else ""
        return mode, rest

    return "flash", text


def _start_strategic_worker(run_id: str, question: str, mode: str, webhook_url: str) -> None:
    def worker():
        try:
            TASKS.update_progress(run_id, "战略陪审进行中", 0.2)
            verdict = run_auto_jury(question=question, mode=mode, run_id=run_id)
            view_url = generate_secure_view_url(run_id)
            verdict["view_url"] = view_url
            TASKS.complete(run_id, verdict)
            notify_verdict_ready(
                run_id=run_id,
                mode=mode,
                verdict=verdict.get("verdict", "conditional"),
                score=float(verdict.get("average_score", 0.0) or 0.0),
                channels=["feishu"],
                summary=verdict.get("one_liner", ""),
                view_url=view_url,
                feishu_webhook=webhook_url,
            )
        except Exception as exc:
            TASKS.fail(run_id, str(exc))

    threading.Thread(target=worker, daemon=True).start()


def build_help_card() -> dict[str, Any]:
    modes_text = "\n".join(f"- `{m['mode']}`：{m['name']}，{m['seat_count']} 席，约 {m['estimated_time']}" for m in list_modes())
    return _card(
        title="AI Judge v3.4",
        template="blue",
        markdown=(
            "**可用命令：**\n"
            "- `/judge <问题>`：默认 Flash 自动陪审\n"
            "- `/judge --mode standard <问题>`：标准陪审\n"
            "- `/strategic <问题>`：战略陪审，后台完成后推送\n"
            "- `/status <run_id>`：查询后台任务\n"
            "- `/seats`：查看席位\n\n"
            f"**模式：**\n{modes_text}"
        ),
    )


def build_seats_card() -> dict[str, Any]:
    content = "\n".join(
        f"- **{p['name']}** ({p['mbti']})：{p['strength']}"
        for p in SEAT_PERSONAS.values()
    )
    return _card("AI Judge 议席", "blue", content)


def build_status_card(run_id: str) -> dict[str, Any]:
    if not run_id:
        return build_error_card("请提供 run_id。示例：/status abc123")
    status = TASKS.get_status(run_id)
    if not status:
        return build_error_card(f"未找到任务：{run_id}")
    result = TASKS.get_result(run_id)
    markdown = (
        f"**Run ID:** {status['run_id']}\n"
        f"**状态:** {status['status']}\n"
        f"**进度:** {int(float(status['progress']) * 100)}%\n"
        f"**当前阶段:** {status.get('current_step') or '-'}"
    )
    if result:
        markdown += f"\n\n**结论:** {result.get('one_liner', '-')}"
    return _card("AI Judge 任务状态", "blue", markdown)


def build_accepted_card(run_id: str, question: str, mode: str) -> dict[str, Any]:
    return _card(
        "AI Judge 已受理战略陪审",
        "blue",
        f"**Run ID:** {run_id}\n**模式:** {mode}\n**问题:** {question}\n\n完成后会自动推送判词卡片。",
    )


def build_verdict_card(verdict: dict[str, Any]) -> dict[str, Any]:
    reasons = "\n".join(f"- {r}" for r in verdict.get("reasons", [])[:3])
    steps = "\n".join(f"- {s}" for s in verdict.get("next_steps", [])[:2])
    markdown = (
        f"**问题:** {verdict.get('question')}\n\n"
        f"**结论:** {verdict.get('one_liner')}\n"
        f"**模式:** {verdict.get('mode_emoji', '')} {verdict.get('mode_name')}\n"
        f"**置信度:** {verdict.get('confidence')}%\n\n"
        f"**关键理由:**\n{reasons}\n\n"
        f"**建议行动:**\n{steps}"
    )
    return _card("AI Judge 自动判词", "green" if verdict.get("verdict") == "credible" else "yellow", markdown)


def build_error_card(message: str) -> dict[str, Any]:
    return _card("AI Judge 错误", "red", message)


def _card(title: str, template: str, markdown: str) -> dict[str, Any]:
    return {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": title}, "template": template},
            "elements": [{"tag": "markdown", "content": markdown}],
        },
    }


def create_app(webhook_url: str):
    from flask import Flask, jsonify, request
    import requests

    app = Flask(__name__)

    @app.route("/feishu/webhook", methods=["POST"])
    def feishu_webhook():
        data = request.get_json(silent=True) or {}
        if data.get("type") == "url_verification":
            return jsonify({"challenge": data.get("challenge", "")})

        event = data.get("event", data)
        reply = handle_feishu_message(event, webhook_url)
        if reply:
            try:
                requests.post(webhook_url, json=reply, timeout=10)
            except Exception as exc:
                print(f"Failed to send Feishu reply: {exc}", file=sys.stderr)
        return jsonify({"code": 0, "msg": "ok"})

    return app


def main():
    parser = argparse.ArgumentParser(description="AI Judge v3.4 Feishu Bot")
    parser.add_argument("--webhook-url", default=os.environ.get("AI_JUDGE_FEISHU_WEBHOOK"), help="Feishu bot webhook URL")
    parser.add_argument("--host", default="0.0.0.0", help="Listen host")
    parser.add_argument("--port", type=int, default=8502, help="Listen port")
    parser.add_argument("--test", action="store_true", help="Run self-test")
    args = parser.parse_args()

    if args.test:
        _self_test()
        return
    if not args.webhook_url:
        print("Error: --webhook-url or AI_JUDGE_FEISHU_WEBHOOK is required.", file=sys.stderr)
        sys.exit(1)

    app = create_app(args.webhook_url)
    print(f"\n  AI Judge Feishu Bot v3.4")
    print(f"  Listening on http://{args.host}:{args.port}/feishu/webhook\n")
    app.run(host=args.host, port=args.port, debug=False)


def _self_test():
    print("AI Judge Feishu Bot — Self Test")
    for builder in (
        build_help_card,
        build_seats_card,
        lambda: build_verdict_card(run_auto_jury("Should we ship v3.4?", mode="flash")),
        lambda: build_error_card("test error"),
    ):
        card = builder()
        assert card["msg_type"] == "interactive"
    reply = handle_feishu_message({"text": "/judge --mode flash Should we ship?"}, "https://example.invalid")
    assert reply and reply["msg_type"] == "interactive"
    print("All tests passed")


if __name__ == "__main__":
    main()
