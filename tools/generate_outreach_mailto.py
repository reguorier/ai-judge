#!/usr/bin/env python3
"""Generate mailto links and .eml drafts for the first outreach batch."""

from __future__ import annotations

import json
from email.message import EmailMessage
from pathlib import Path
from urllib.parse import quote


ROOT = Path(__file__).resolve().parents[1]
QUEUE_PATH = ROOT / "growth" / "outreach_batch_001.json"
MAILTO_PATH = ROOT / "growth" / "outreach_mailto_links.md"
DRAFT_DIR = ROOT / "growth" / "outreach_drafts"


def mailto_for(target: dict[str, str]) -> str:
    subject = quote(target["subject"])
    body = quote(normalize_body(target["body"]))
    return f"mailto:{target['to']}?subject={subject}&body={body}"


def normalize_body(body: str) -> str:
    return body.replace("\\n", "\n")


def build_eml(target: dict[str, str]) -> str:
    message = EmailMessage()
    message["To"] = target["to"]
    message["Subject"] = target["subject"]
    message.set_content(normalize_body(target["body"]))
    return message.as_string()


def main() -> None:
    queue = json.loads(QUEUE_PATH.read_text(encoding="utf-8"))
    DRAFT_DIR.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Outreach Batch 001 Mailto Links",
        "",
        f"Batch: `{queue['batch_id']}`",
        f"Status: `{queue['status']}`",
        "",
        "These links open a compose window only. They do not send mail by themselves.",
        "After a message is actually sent, update `growth/outreach_batch_001.md` and `growth/feedback_log.md`.",
        "",
        "| ID | Target | To | Source | Compose | Draft file |",
        "|---|---|---|---|---|---|",
    ]

    for target in queue["targets"]:
        draft_path = DRAFT_DIR / f"{target['id']}.eml"
        draft_path.write_text(build_eml(target), encoding="utf-8")
        lines.append(
            "| {id} | {target} | `{to}` | {source} | [compose]({mailto}) | `{draft}` |".format(
                id=target["id"],
                target=target["target"],
                to=target["to"],
                source=target["source"],
                mailto=mailto_for(target),
                draft=draft_path.relative_to(ROOT),
            )
        )

    lines.append("")
    MAILTO_PATH.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
