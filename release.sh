#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "╔══════════════════════════════════════╗"
echo "║    AI Judge — One-Click Release      ║"
echo "╚══════════════════════════════════════╝"
echo -e "${NC}"

# ── Step 1: Open browser to create repo ──
echo -e "${YELLOW}📋 Step 1: Opening GitHub to create repository...${NC}"
REPO_URL="https://github.com/new?name=ai-judge&description=Multi-model+AI+jury+system+%E2%80%94+9+models+deliberate%2C+you+hold+the+gavel&visibility=public"
open "$REPO_URL"

echo ""
echo -e "${YELLOW}👆 A browser window just opened.${NC}"
echo "   Do NOT check any boxes (no README, no .gitignore, no license)."
echo "   Just click the green 'Create repository' button."
echo ""
echo -e "${CYAN}   Press ENTER after you've created the repository...${NC}"
read -r

# ── Step 2: Clean git and re-init ──
echo ""
echo -e "${YELLOW}🔧 Step 2: Preparing git...${NC}"
rm -rf .git 2>/dev/null || true
git init
git branch -m main 2>/dev/null || true
git config user.email "reguorider@gmail.com"
git config user.name "AI Judge"
git add -A
git commit -m "feat: AI Judge v2.0.0 — Hermes skill package

Multi-model AI jury system (BSL 1.1).
9 models deliberate. You hold the gavel." 2>/dev/null || echo "(already committed)"

# ── Step 3: Push ──
echo ""
echo -e "${YELLOW}⬆️  Step 3: Pushing to GitHub...${NC}"

# Try SSH first, fall back to HTTPS
if [ -f "$HOME/.ssh/id_ed25519" ] || [ -f "$HOME/.ssh/id_rsa" ]; then
  REMOTE="git@github.com:reguorier/ai-judge.git"
  echo "   Using SSH: $REMOTE"
else
  REMOTE="https://github.com/reguorier/ai-judge.git"
  echo "   Using HTTPS: $REMOTE"
fi

git remote add origin "$REMOTE" 2>/dev/null || git remote set-url origin "$REMOTE"
git push -u origin main --force

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗"
echo "║  ✅ AI Judge is now live on GitHub!   ║"
echo "║  🌐 github.com/reguorier/ai-judge  ║"
echo "╚══════════════════════════════════════╝${NC}"
