#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

REPO="${1:-git@github.com:reguorier/ai-judge.git}"

echo -e "${CYAN}"
echo "AI Judge v3.3.0 GitHub Publisher"
echo "Nine persona seats. Evidence trace. Human final."
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
  RELEASE_V3_2.md \
  RELEASE_V3_3.md \
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

git commit -m "Release AI Judge v3.3 COUNCIL-004

The public package now presents COUNCIL-004 fixed persona seats and
lightweight L1/L2/L3 evidence tracing on top of the v3.2 reasoning,
dissent, and risk-routing workflow.

Constraint: Public release must not include local deploy keys or paid collector runtime
Rejected: Force-push a rebuilt repository | destructive and easy to misuse
Confidence: high
Scope-risk: moderate
Tested: python3 -B cli/main.py seats --list; python3 -B cli/main.py trace --demo; PYTHONPATH=. python3 -B tests/smoke_test_council_004.py
Not-tested: GitHub Actions after this local publish helper runs" 2>/dev/null || echo "No new commit needed."

echo -e "${YELLOW}Pushing to ${REPO}...${NC}"
git push -u origin main

echo ""
echo -e "${GREEN}AI Judge v3.3.0 is live: ${REPO}${NC}"
