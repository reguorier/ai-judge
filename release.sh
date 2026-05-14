#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

exec ./publish.sh "${1:-git@github.com:reguorier/ai-judge.git}"
