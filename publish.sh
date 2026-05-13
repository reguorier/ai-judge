#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO="${1:-git@github.com:reguorider-gif/ai-judge.git}"

echo -e "${CYAN}"
echo "AI Judge v3.1.0 GitHub Publisher"
echo "Nine seats. Hard truth. Human final."
echo -e "${NC}"

if [ ! -d .git ]; then
  git init
  git branch -M main
fi

git remote add origin "$REPO" 2>/dev/null || git remote set-url origin "$REPO"

echo -e "${YELLOW}Staging public release files only...${NC}"
git add -- \
  .github/workflows/publish.yml \
  .gitignore \
  CONTRIBUTING.md \
  Dockerfile \
  LICENSE \
  README.md \
  RELEASE_V3.md \
  RELEASE_v2.md \
  SECURITY.md \
  SKILL.md \
  Publish-AI-Judge-V3.command \
  assets \
  bridges \
  cli \
  core \
  docker-compose.yml \
  docs \
  product \
  prompts \
  publish.sh \
  pyproject.toml \
  release.sh \
  schemas \
  tests

git commit -m "Explain why AI Judge v3.1 needs judgment profiling

The public package now presents AI Judge as a local-first, human-final
v3.1 jury workflow with reproducible cognitive proxy demos, hard truth
mode, and a clearer GitHub product page.

Constraint: Public release must not include local deploy keys or paid collector runtime
Rejected: Force-push a rebuilt repository | destructive and easy to misuse
Confidence: high
Scope-risk: moderate
Tested: PYTHONPATH=. python3 tests/smoke_test_v3.py
Not-tested: GitHub Actions after this local publish helper runs" 2>/dev/null || echo "No new commit needed."

echo -e "${YELLOW}Pushing to ${REPO}...${NC}"
git push -u origin main

echo ""
echo -e "${GREEN}AI Judge v3.1.0 is live: ${REPO}${NC}"
