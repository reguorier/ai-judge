#!/bin/bash
set -euo pipefail

echo "🚀 AI Judge — GitHub Publisher"
echo "================================"
echo ""

# ── Check git ──
if ! command -v git &>/dev/null; then
  echo "❌ git not found. Install it first: https://git-scm.com"
  exit 1
fi

# ── Repo name ──
REPO_NAME="${1:-ai-judge}"
REMOTE_URL="https://github.com/reguorier/${REPO_NAME}.git"
# Use SSH if available, else HTTPS
if [ -f "$HOME/.ssh/id_ed25519" ] || [ -f "$HOME/.ssh/id_rsa" ]; then
  REMOTE_URL="git@github.com:reguorier/${REPO_NAME}.git"
fi

echo "📦 Target: $REMOTE_URL"
echo ""

# ── Clean any broken git state ──
rm -rf .git 2>/dev/null || true

# ── Init ──
git init
git branch -m main 2>/dev/null || true
git config user.email "reguorider@gmail.com"
git config user.name "AI Judge"

# ── Stage everything ──
git add -A

# ── Commit ──
git commit -m "feat: AI Judge v2.0.0 — Hermes skill package

Multi-model AI jury system (BSL 1.1).
9 models deliberate. You hold the gavel.

Includes:
- CLI + core modules (license shim, Hermes output)
- 3 Swift desktop bridges (Gemini, Qwen, Doubao)
- JSON Schema contracts (task status, claim ledger, Hermes output)
- System prompt templates
- Docker + docker-compose
- GitHub Actions CI/CD (Docker publish)
- Product landing page with SVG courtroom diagram
- Full documentation (Architecture, Comparison, Human-Centric design)
- BSL 1.1 license → MIT after 4 years"

echo ""
echo "✅ Committed $(git rev-parse --short HEAD)"
echo ""

# ── Push ──
echo "⬆️  Pushing to GitHub..."
git remote add origin "$REMOTE_URL" 2>/dev/null || git remote set-url origin "$REMOTE_URL"
git push -u origin main --force

echo ""
echo "================================="
echo "✅ Published!"
echo "🌐 https://github.com/reguorier/${REPO_NAME}"
echo ""
echo "📋 Next steps:"
echo "   1. Visit the repo and check README renders correctly"
echo "   2. Go to Settings → Pages → Source: GitHub Actions (auto-deploys landing page)"
echo "   3. Share: https://github.com/reguorier/${REPO_NAME}"
echo "================================="
