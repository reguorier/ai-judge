# AI Judge Desktop and Web Seat Bridge

## Desktop Client

Build the local macOS wrapper:

```bash
.venv/bin/python tools/build_mac_app.py
```

The generated app is:

```text
dist/mac/AI Judge.app
```

When launched, the app starts `product/api_server.py` on `127.0.0.1:8501` if the API is not already running, then loads the product dashboard in a native WKWebView window.

This local wrapper is unsigned. Internal/local use is fine, but public distribution should add Apple Developer signing and notarization.

## Seat Engines

AI Judge now exposes two product-side engines:

- `local`: deterministic local jury, stable default, no external login required.
- `web`: isolated browser bridge for live model web apps. Web seats must pass calibration before deep collection.

The dashboard shows both under "席位来源". Web mode can always create a diagnosis report, but deep collection only starts when enough calibrated seats are ready.

## Product Flow

Every run now has two separate decisions:

1. **Mode**: Flash / Standard / Strategic decides breadth and scoring depth.
2. **Execution driver**: local synthetic, isolated web DOM, desktop Operator, or future provider API decides how answers are collected.

Before a deep web run, AI Judge performs a local resonance pass:

- normalize the user's question
- expose assumptions that need checking
- generate a stricter professional prompt for external seats
- decide whether the selected web seats are calibrated enough to run

If not enough seats are calibrated, the run completes as `网页深度未启动` with a bridge diagnosis instead of pretending the model answered.

## Seat to Browser / Client Matrix

The bridge status endpoint returns a one-to-one mapping for every seat:

- Gemini -> Gemini web
- ChatGPT -> ChatGPT / ChatGPT Atlas web
- DeepSeek -> DeepSeek web
- Qwen -> Qwen Studio web
- Kimi -> Kimi web
- Grok -> Grok web
- Yuanbao -> Tencent Yuanbao web
- MiMo -> custom web target
- Claude -> Claude web
- MiniMax -> MiniMax web
- Zhipu -> ChatGLM / Zhipu web
- Wenxin -> Wenxin Yiyan web
- Doubao -> Doubao desktop client at `/Applications/豆包.app`

Doubao is intentionally marked as a desktop-client target. It appears in the mapping and readiness table, but desktop-client collection is not silently treated as Playwright web collection. It requires a safe desktop Operator before it can run in the background.

## Doubao Desktop Isolation Plan

Doubao desktop cannot be made reliably non-interfering from the same macOS user session if the bridge depends on `CGEvent`, foreground app activation, or the global pasteboard. Those APIs share the user's WindowServer, mouse, keyboard focus, and clipboard.

The production path is therefore split into two channels:

1. **Safe seat result path**: collect Doubao through a calibrated Doubao web/CDP tab when AI Judge needs a guaranteed non-interfering answer. This follows the same isolated bridge rules as other web seats.
2. **Desktop-client path**: enable the Doubao desktop app only through an isolated worker, either a second macOS user session, a VM, or a remote worker Mac. The main AI Judge app submits a task to that worker API and receives `{run_id, seat, answer, status, reason}` back. The worker owns its own WindowServer, mouse/keyboard focus, and clipboard, so it cannot disturb the user's active desktop.

The UI must show the channel used for each run. A local synthetic Doubao score is labeled as local scoring, a web/CDP Doubao answer is labeled as web collection, and a future isolated desktop result is labeled as desktop worker collection.

## Web Bridge Isolation

The web bridge uses Playwright browser contexts, not desktop GUI control.

It does not use:

- system mouse events
- the user's active keyboard focus
- the system clipboard
- the user's normal browser profile

Each seat uses its own persistent profile under:

```text
data/web_profiles/<seat>
```

That separation is intentional. It prevents AI Judge runs from disturbing normal Mac mouse/keyboard use and avoids mixing AI Judge automation into the user's active browser session.

## Setup

Install the optional browser bridge runtime:

```bash
.venv/bin/python -m pip install playwright
.venv/bin/python -m playwright install chromium
```

Create the editable seat config:

```bash
.venv/bin/python -m bridges.web_seat_bridge --init-config
```

Config file:

```text
data/web_seats.json
```

Enable seats only after the target model web app has been logged into and selector settings have been verified. If a model site changes its DOM, update that seat's selectors in `data/web_seats.json`.

Check readiness:

```bash
.venv/bin/python -m bridges.web_seat_bridge --status
```

Run real calibration probes:

```bash
.venv/bin/python -m bridges.web_seat_bridge --calibrate --seats gemini,chatgpt --timeout-seconds 8
```

Calibration verifies login/input/send/readback for each seat and writes:

```text
data/seat_calibration.json
```

Readiness now means:

- the seat is enabled and configured
- Playwright is installed for web seats
- the latest calibration passed and is not stale
- the execution driver can run safely in the background

## Current Guarantee

The product will not silently pretend a web model answered. If web mode is selected before seats are calibrated, the API returns a complete diagnostic report explaining exactly which seats are blocked and why.

The current desktop-controller Swift files are reference experiments only. They use foreground app activation/global events and are not wired into the product's background run path because that would disturb normal mouse/keyboard usage. The product will only enable a desktop seat after a safe Operator exists for that app.
