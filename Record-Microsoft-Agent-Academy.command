#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$REPO_DIR/product/video-exports"
STAMP="$(date +"%Y%m%d-%H%M%S")"
RAW="$OUT_DIR/ai-judge-microsoft-agent-academy-$STAMP.mov"
MP4="$OUT_DIR/ai-judge-microsoft-agent-academy-$STAMP.mp4"

mkdir -p "$OUT_DIR"

echo "AI Judge Microsoft Agent Academy recorder"
echo "Output folder: $OUT_DIR"
echo
echo "Before continuing, arrange your screen in this order:"
echo "1. Microsoft Copilot/Cowork/Copilot Studio page with the generated agent output visible."
echo "2. AI Judge demo or terminal output ready in another tab/window."
echo "3. Architecture image ready: assets/microsoft-agent-academy-architecture.svg"
echo
echo "The recording will capture your main display for 300 seconds."
echo "The official limit is 5 minutes, so stop early if you finish sooner with Ctrl-C."
echo
read -r -p "Press Enter when the Microsoft product scene is visible and ready."

screencapture -v -V 300 -T 3 -k "$RAW"

if command -v ffmpeg >/dev/null 2>&1; then
  echo "Compressing to MP4..."
  ffmpeg -y -i "$RAW" -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p -movflags +faststart "$MP4" >/dev/null 2>&1
  echo "Done: $MP4"
else
  echo "ffmpeg not found. Raw recording saved: $RAW"
fi

echo
echo "Submit this MP4 with docs/MICROSOFT_AGENT_ACADEMY.md and assets/microsoft-agent-academy-architecture.svg."
read -r -p "Press Enter to close this window."
