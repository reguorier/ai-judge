# Recording Guide

This project now has two one-click recording scripts.

## Fast Launch Demo

Double-click:

```text
Record-AI-Judge-Demo.command
```

What it does:

- Opens `product/demo-video.html`
- Waits eight seconds
- Records your main display for 92 seconds
- Saves `.mov` and compressed `.mp4` files under `product/video-exports/`

Use this video for:

- Product Hunt
- Show HN
- Reddit
- AI tool directories
- Chinese social posts

## Microsoft Agent Academy Demo

The official Microsoft Agent Academy Hackathon requires a working agent using at least one Microsoft product, a demo video no longer than five minutes, an architecture overview, and a clear use case.

Official page:

```text
https://microsoft.github.io/agent-academy/events/hackathon/
```

Double-click:

```text
Record-Microsoft-Agent-Academy.command
```

Before pressing Enter in the script, prepare the visible screen:

1. Open Copilot Studio, M365 Copilot, or Copilot Cowork.
2. Paste the prompt from `examples/microsoft_agent_academy/copilot_cowork_packet.md`.
3. Generate the Microsoft agent output.
4. Keep that Microsoft product page visible.
5. Keep `assets/microsoft-agent-academy-architecture.svg` ready in another tab/window.
6. Keep `product/demo-video.html`, `harness-report.html`, or terminal output ready for the AI Judge section.

Recommended five-minute structure:

| Time | Screen | What to say |
|---:|---|---|
| 0:00-0:30 | Microsoft product page | "This is the working Microsoft agent output." |
| 0:30-1:30 | Copilot/Cowork output | Show the plan/answer produced by the Microsoft agent. |
| 1:30-2:30 | AI Judge packet or terminal | Explain that AI Judge checks unsupported claims, risk, and falsifiable next steps. |
| 2:30-3:30 | `harness-report.html` | Show benchmark and regression proof. |
| 3:30-4:20 | Architecture SVG | Show components, data flow, and integration points. |
| 4:20-5:00 | README/repo | Close with open-source status, local-first usage, and the human-final verdict principle. |

## What I Can Automate

I can generate the demo page, scripts, architecture image, application copy, and compressed MP4 workflow.

I cannot honestly fake the required Microsoft product scene. For the strongest submission, open a real Copilot Studio, M365 Copilot, or Copilot Cowork page first, then run the Microsoft recording script.

## Output Files

Recordings are saved here:

```text
product/video-exports/
```

Do not commit large raw video files unless you intentionally want them in Git history.
