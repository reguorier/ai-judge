# Quick Start — 5 Minutes to Your First Verdict

## Prerequisites

- macOS
- Python 3.11+
- Google Chrome with remote debugging enabled
- License Key ([get one](https://ai-judge.dev))

## Step 1: Enable Chrome Remote Debugging

```bash
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9223
```

## Step 2: Install

```bash
pip install ai-judge
```

## Step 3: Activate License

```bash
ai-judge license activate --key AJ-XXXX-XXXX-XXXX
ai-judge license status
```

## Step 4: Run Your First Jury

```bash
ai-judge jury --question "Should we enter the Japanese market this quarter?"
```

Creates a session with 9 AI seats.

## Step 5: Collect Answers

```bash
ai-judge collect --run latest
```

Sends your question to all 9 seats simultaneously. Takes 30-90 seconds.

## Step 6: Generate Verdict

```bash
ai-judge verdict --run latest
```

Produces a complete verdict with claim scoring, consensus detection, and audit trail.

## Step 7: You Decide

Open `~/.ai-judge/runs/latest/verdict.md`. Read the evidence. Make your decision.

## Docker Alternative

```bash
docker pull ghcr.io/audimacmini/ai-judge:latest
docker compose up
docker compose run --rm ai-judge jury --question "..."
```

## What Each Command Does

| Command | What Happens | Time |
|---------|-------------|------|
| `jury` | Create session, assign 9 seats | < 1s |
| `collect` | Send question, collect raw answers | 30-90s |
| `verdict` | Score claims, detect consensus, generate audit trail | 5-15s |
| `reflect` | Generate daily performance summary | < 1s |
| `list` | Show recent runs | < 1s |
