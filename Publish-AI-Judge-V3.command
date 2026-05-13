#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"

OWNER="reguorider-gif"
REPO="ai-judge"
REPO_FULL="${OWNER}/${REPO}"
REPO_URL="https://github.com/${REPO_FULL}.git"
TAG="v3.1.0"
ARCHIVE="ai-judge-v3.1.0-release.tar.gz"
DESCRIPTION="AI Judge v3.1: local-first AI jury with hard truth mode and cognitive proxy signals."

clear
echo "AI Judge V3.1 Publisher"
echo "Target: https://github.com/${REPO_FULL}"
echo ""
echo "Paste a GitHub token with repo write access."
echo "The token is used for this run only, via temporary askpass/header files."
printf "GitHub token: "
stty -echo
read -r GITHUB_TOKEN
stty echo
echo ""

if [ -z "${GITHUB_TOKEN}" ]; then
  echo "No token provided. Aborting."
  exit 1
fi

ASKPASS="$(mktemp /tmp/ai-judge-askpass.XXXXXX)"
HEADER_FILE="$(mktemp /tmp/ai-judge-github-header.XXXXXX)"

cleanup() {
  rm -f "$ASKPASS" "$HEADER_FILE"
  unset GITHUB_TOKEN
}
trap cleanup EXIT

cat > "$ASKPASS" <<'EOF'
#!/bin/sh
case "$1" in
  *Username*) echo "x-access-token" ;;
  *Password*) printf "%s" "$GITHUB_TOKEN" ;;
  *) echo "" ;;
esac
EOF
chmod 700 "$ASKPASS"

{
  printf "Authorization: Bearer %s\n" "$GITHUB_TOKEN"
  printf "Accept: application/vnd.github+json\n"
  printf "X-GitHub-Api-Version: 2022-11-28\n"
} > "$HEADER_FILE"
chmod 600 "$HEADER_FILE"

export GIT_ASKPASS="$ASKPASS"
export GIT_TERMINAL_PROMPT=0
export GITHUB_TOKEN

echo ""
echo "Checking GitHub repository..."
if ! curl -fsS -H @"$HEADER_FILE" "https://api.github.com/repos/${REPO_FULL}" >/dev/null; then
  echo "Repository not found. Creating public repo ${REPO_FULL}..."
  python3 - <<'PY' > /tmp/ai-judge-create-repo.json
import json
print(json.dumps({
    "name": "ai-judge",
    "description": "AI Judge v3.1: local-first AI jury with hard truth mode and cognitive proxy signals.",
    "private": False,
    "auto_init": False,
    "has_issues": True,
    "has_projects": False,
    "has_wiki": False,
}))
PY
  curl -fsS -X POST -H @"$HEADER_FILE" \
    --data @/tmp/ai-judge-create-repo.json \
    "https://api.github.com/user/repos" >/dev/null
  rm -f /tmp/ai-judge-create-repo.json
fi

if [ ! -d .git ]; then
  git init
  git branch -M main
fi

git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

echo ""
echo "Staging public release files..."
git add -- \
  .github \
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

git commit -m "Publish AI Judge v3.1.0" 2>/dev/null || echo "No new commit needed."

if git rev-parse "$TAG" >/dev/null 2>&1; then
  git tag -f "$TAG"
else
  git tag -a "$TAG" -m "AI Judge v3.1.0"
fi

echo ""
echo "Building ${ARCHIVE}..."
git archive --format=tar.gz --prefix="ai-judge-v3.1.0/" -o "$ARCHIVE" HEAD

echo ""
echo "Pushing main and ${TAG}..."
git -c credential.helper= push origin main
git -c credential.helper= push origin "$TAG" --force

echo ""
echo "Creating GitHub Release..."
RELEASE_JSON="$(mktemp /tmp/ai-judge-release.XXXXXX.json)"
python3 - <<'PY' > "$RELEASE_JSON"
import json
body = """AI Judge v3.1.0 release.

Highlights:
- v3.1 hard truth mode
- 4 cognitive proxy signals
- dual scores: smart_sounding vs judgment_quality
- visual GitHub README
- local-first CLI, Docker, and Codex skill package

See RELEASE_V3.md for full notes.
"""
print(json.dumps({
    "tag_name": "v3.1.0",
    "name": "AI Judge v3.1.0",
    "body": body,
    "draft": False,
    "prerelease": False,
}))
PY

if ! curl -fsS -X POST -H @"$HEADER_FILE" --data @"$RELEASE_JSON" \
  "https://api.github.com/repos/${REPO_FULL}/releases" >/tmp/ai-judge-release-response.json; then
  echo "Release may already exist. Reusing existing release."
  curl -fsS -H @"$HEADER_FILE" \
    "https://api.github.com/repos/${REPO_FULL}/releases/tags/${TAG}" >/tmp/ai-judge-release-response.json
fi
rm -f "$RELEASE_JSON"

UPLOAD_URL="$(python3 - <<'PY'
import json
with open("/tmp/ai-judge-release-response.json", "r", encoding="utf-8") as f:
    data = json.load(f)
print(data["upload_url"].split("{", 1)[0])
PY
)"
rm -f /tmp/ai-judge-release-response.json

echo "Uploading ${ARCHIVE}..."
curl -fsS -X POST \
  -H @"$HEADER_FILE" \
  -H "Content-Type: application/gzip" \
  --data-binary @"$ARCHIVE" \
  "${UPLOAD_URL}?name=${ARCHIVE}" >/dev/null || echo "Asset upload skipped; it may already exist."

echo ""
echo "Done: https://github.com/${REPO_FULL}"
echo "Release: https://github.com/${REPO_FULL}/releases/tag/${TAG}"
