#!/bin/bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$REPO_DIR/product/video-exports"
STAMP="$(date +"%Y%m%d-%H%M%S")"
RAW="$OUT_DIR/ai-judge-90s-demo-$STAMP.mov"
MP4="$OUT_DIR/ai-judge-90s-demo-$STAMP.mp4"

mkdir -p "$OUT_DIR"

echo "AI Judge 90-second launch demo recorder"
echo "Output folder: $OUT_DIR"
echo
echo "Opening the demo page. Make the browser full screen if you want a clean recording."
open "$REPO_DIR/product/demo-video.html"
echo
echo "Recording starts in 8 seconds and stops automatically after 92 seconds."
sleep 8

screencapture -v -V 92 -T 3 -k "$RAW"

if command -v ffmpeg >/dev/null 2>&1; then
  echo "Compressing to MP4..."
  ffmpeg -y -i "$RAW" -c:v libx264 -preset medium -crf 22 -pix_fmt yuv420p -movflags +faststart "$MP4" >/dev/null 2>&1
  echo "Done: $MP4"
else
  echo "ffmpeg not found. Raw recording saved: $RAW"
fi

echo
echo "Tip: use this short demo for Product Hunt, Show HN, Reddit, and directory submissions."
read -r -p "Press Enter to close this window."
