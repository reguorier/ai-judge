#!/usr/bin/env python3
"""AI Judge Notification Gateway — COUNCIL-005 consensus feature.

Delivers verdict completion notifications through multiple channels:
  - Desktop (macOS Notification Center via osascript)
  - Email (SMTP)
  - Webhook (HTTP POST)
  - Slack (Incoming Webhook)
  - Console (stdout, for logging)

Usage:
  from bridges.notification_gateway import notify

  await notify(
      channels=["desktop", "email"],
      title="AI Judge Verdict Ready",
      body="Strategic mode completed. Verdict: Credible (0.82)",
      metadata={"run_id": "abc123", "mode": "strategic"},
  )
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import smtplib
import subprocess
import sys
import time
from datetime import datetime, timezone
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


# ─── Signed Result Links ───────────────────────────────────

def generate_secure_view_url(task_id: str, ttl_hours: int = 168) -> str:
    """Generate an HMAC-signed result URL.

    The link is safe to send through Feishu/email because the full verdict stays
    on the AI Judge server and the notification carries only a short signed URL.
    """
    app_url = os.environ.get("AI_JUDGE_APP_URL", "http://127.0.0.1:8501").rstrip("/")
    secret = os.environ.get("AI_JUDGE_APP_SECRET", "ai-judge-local-dev-secret").encode("utf-8")
    exp = int(time.time()) + ttl_hours * 3600
    raw = f"{task_id}:{exp}".encode("utf-8")
    sig = hmac.new(secret, raw, hashlib.sha256).hexdigest()
    return f"{app_url}/view?tid={task_id}&exp={exp}&sig={sig}"


def verify_secure_view(task_id: str, exp: str, sig: str) -> bool:
    """Verify a signed result URL."""
    if not task_id or not exp or not sig:
        return False
    try:
        exp_int = int(exp)
    except ValueError:
        return False
    if exp_int < int(time.time()):
        return False
    secret = os.environ.get("AI_JUDGE_APP_SECRET", "ai-judge-local-dev-secret").encode("utf-8")
    raw = f"{task_id}:{exp_int}".encode("utf-8")
    expected = hmac.new(secret, raw, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


# ─── Channel: Desktop Notification ────────────────────────

def _notify_desktop(title: str, body: str, **_kwargs) -> bool:
    """Send a macOS desktop notification."""
    try:
        safe_body = str(body).replace("\\", "\\\\").replace('"', '\\"')[:180]
        safe_title = str(title).replace("\\", "\\\\").replace('"', '\\"')[:80]
        script = f'display notification "{safe_body}" with title "{safe_title}" sound name "Glass"'
        subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            timeout=5,
        )
        return True
    except Exception:
        return False


# ─── Channel: Email ────────────────────────────────────────

def _notify_email(
    title: str,
    body: str,
    to: str | None = None,
    smtp_host: str | None = None,
    smtp_port: int = 587,
    smtp_user: str | None = None,
    smtp_password: str | None = None,
    **_kwargs,
) -> bool:
    """Send an email notification via SMTP."""
    to_addr = to or os.environ.get("AI_JUDGE_NOTIFY_EMAIL")
    host = smtp_host or os.environ.get("AI_JUDGE_SMTP_HOST", "smtp.gmail.com")
    user = smtp_user or os.environ.get("AI_JUDGE_SMTP_USER")
    password = smtp_password or os.environ.get("AI_JUDGE_SMTP_PASSWORD")

    if not to_addr:
        return False
    if not user or not password:
        return False

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = title
        msg["From"] = user
        msg["To"] = to_addr

        with smtplib.SMTP(host, smtp_port, timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        return False


# ─── Channel: Webhook ──────────────────────────────────────

def _notify_webhook(
    title: str,
    body: str,
    webhook_url: str | None = None,
    metadata: dict[str, Any] | None = None,
    **_kwargs,
) -> bool:
    """POST a notification payload to a webhook URL."""
    url = webhook_url or os.environ.get("AI_JUDGE_WEBHOOK_URL")
    if not url:
        return False

    try:
        import httpx

        payload = {
            "title": title,
            "body": body,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
        }
        resp = httpx.post(url, json=payload, timeout=10)
        return resp.status_code < 400
    except Exception:
        return False


# ─── Channel: Feishu / WeCom ──────────────────────────────

def _post_json_webhook(url: str, payload: dict[str, Any]) -> bool:
    try:
        import httpx

        resp = httpx.post(url, json=payload, timeout=10)
        return resp.status_code < 400
    except Exception:
        return False


def _notify_feishu(
    title: str,
    body: str,
    feishu_webhook: str | None = None,
    metadata: dict[str, Any] | None = None,
    view_url: str | None = None,
    **_kwargs,
) -> bool:
    """Send a Feishu interactive card through an incoming webhook."""
    url = feishu_webhook or os.environ.get("AI_JUDGE_FEISHU_WEBHOOK")
    if not url:
        return False

    metadata = metadata or {}
    elements: list[dict[str, Any]] = [
        {"tag": "markdown", "content": body},
        {"tag": "hr"},
        {
            "tag": "markdown",
            "content": (
                f"**Run ID:** {metadata.get('run_id', '-')}\n"
                f"**Mode:** {metadata.get('mode', '-')}\n"
                f"**Verdict:** {metadata.get('verdict', '-')}"
            ),
        },
    ]
    if view_url:
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "查看完整判词"},
                    "url": view_url,
                    "type": "primary",
                }
            ],
        })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {"title": {"tag": "plain_text", "content": title}, "template": "blue"},
            "elements": elements,
        },
    }
    return _post_json_webhook(url, payload)


def _notify_wecom(
    title: str,
    body: str,
    wecom_webhook: str | None = None,
    metadata: dict[str, Any] | None = None,
    view_url: str | None = None,
    **_kwargs,
) -> bool:
    """Send a WeCom markdown message through an incoming webhook."""
    url = wecom_webhook or os.environ.get("AI_JUDGE_WECOM_WEBHOOK")
    if not url:
        return False
    metadata = metadata or {}
    content = (
        f"**{title}**\n"
        f"{body}\n\n"
        f"> Run ID: {metadata.get('run_id', '-')}\n"
        f"> Mode: {metadata.get('mode', '-')}\n"
        f"> Verdict: {metadata.get('verdict', '-')}"
    )
    if view_url:
        content += f"\n\n[查看完整判词]({view_url})"
    return _post_json_webhook(url, {"msgtype": "markdown", "markdown": {"content": content}})


# ─── Channel: Slack ────────────────────────────────────────

def _notify_slack(
    title: str,
    body: str,
    slack_webhook: str | None = None,
    metadata: dict[str, Any] | None = None,
    **_kwargs,
) -> bool:
    """Send a Slack message via Incoming Webhook."""
    url = slack_webhook or os.environ.get("AI_JUDGE_SLACK_WEBHOOK")
    if not url:
        return False

    try:
        import httpx

        fields = []
        if metadata:
            for k, v in metadata.items():
                fields.append({"title": k, "value": str(v), "short": True})

        payload = {
            "attachments": [
                {
                    "color": "#ffc12f",
                    "title": title,
                    "text": body,
                    "fields": fields[:6],
                    "footer": "AI Judge v3.4",
                    "ts": int(datetime.now(timezone.utc).timestamp()),
                }
            ]
        }
        resp = httpx.post(url, json=payload, timeout=10)
        return resp.status_code < 400
    except Exception:
        return False


# ─── Channel: Console ──────────────────────────────────────

def _notify_console(title: str, body: str, **_kwargs) -> bool:
    """Print notification to stdout."""
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"  {body}")
    print(f"{'='*50}\n")
    return True


# ─── Channel Registry ──────────────────────────────────────

CHANNELS = {
    "desktop": _notify_desktop,
    "email": _notify_email,
    "webhook": _notify_webhook,
    "feishu": _notify_feishu,
    "wecom": _notify_wecom,
    "slack": _notify_slack,
    "console": _notify_console,
}


# ─── Main API ──────────────────────────────────────────────

async def notify(
    channels: list[str] | None = None,
    title: str = "AI Judge",
    body: str = "",
    metadata: dict[str, Any] | None = None,
    **kwargs,
) -> dict[str, bool]:
    """Send notifications through specified channels.

    Args:
        channels: List of channel names. Default: ["console"].
                  Available: desktop, email, webhook, slack, console.
        title: Notification title.
        body: Notification body text.
        metadata: Optional dict attached to webhook/slack payloads.
        **kwargs: Channel-specific config (to, smtp_host, webhook_url, etc.)

    Returns:
        {channel_name: success_bool}
    """
    if channels is None:
        channels = ["console"]

    results = {}
    for ch in channels:
        handler = CHANNELS.get(ch)
        if handler:
            try:
                results[ch] = handler(title=title, body=body, metadata=metadata, **kwargs)
            except Exception:
                results[ch] = False
        else:
            results[ch] = False

    return results


def notify_sync(
    channels: list[str] | None = None,
    title: str = "AI Judge",
    body: str = "",
    metadata: dict[str, Any] | None = None,
    **kwargs,
) -> dict[str, bool]:
    """Synchronous wrapper for environments without asyncio."""
    import asyncio

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(notify(channels, title, body, metadata, **kwargs))


# ─── Convenience: verdict notification ────────────────────

def notify_verdict_ready(
    run_id: str,
    mode: str,
    verdict: str,
    score: float,
    channels: list[str] | None = None,
    summary: str = "",
    view_url: str | None = None,
    **kwargs,
) -> dict[str, bool]:
    """Send a standardized verdict-ready notification."""
    from core.modes import JURY_MODES

    mode_info = JURY_MODES.get(mode, {})
    emoji = mode_info.get("emoji", "")

    title = f"{emoji} AI Judge Verdict Ready"
    body = (
        f"Run: {run_id}\n"
        f"Mode: {mode_info.get('name', mode)}\n"
        f"Verdict: {verdict.upper()}\n"
        f"Score: {score:.3f}\n"
        f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    )
    if summary:
        body = f"{summary}\n\n{body}"
    if view_url:
        body = f"{body}\nView: {view_url}"

    return notify_sync(
        channels=channels or ["console"],
        title=title,
        body=body,
        metadata={"run_id": run_id, "mode": mode, "verdict": verdict, "score": score},
        view_url=view_url,
        **kwargs,
    )


# ─── Standalone test ──────────────────────────────────────

if __name__ == "__main__":
    print("AI Judge Notification Gateway — Self Test\n")

    # Test each channel (console always works)
    for ch in ["console", "desktop"]:
        result = notify_sync(
            channels=[ch],
            title="Test Notification",
            body=f"Testing {ch} channel from AI Judge Notification Gateway.",
            metadata={"test": True, "channel": ch},
        )
        status = "✓" if result.get(ch) else "✗"
        print(f"  {ch}: {status}")

    print("\n  All console tests passed")
