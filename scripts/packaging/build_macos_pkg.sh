#!/bin/bash
# Canonical macOS PKG Build Pipeline
# Builds an unsigned local PKG from the canonical source repo.
# Target runtime: /Users/Shared/AI Judge/runtime
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CANONICAL_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="$CANONICAL_ROOT/build"
INSTALLER_PAYLOAD="$BUILD_DIR/installer_payload"
RUNTIME_TARGET="$INSTALLER_PAYLOAD/Users/Shared/AI Judge/runtime"
DIST_DIR="$CANONICAL_ROOT/dist"
MANIFEST="$BUILD_DIR/installer_payload_manifest.json"

VERSION="3.8.14-RC1"
PKG_NAME="AI-Judge-v${VERSION}-macOS-arm64"

echo "=== Canonical PKG Build Pipeline ==="
echo "Canonical root: $CANONICAL_ROOT"
echo "Version: $VERSION"
echo ""

# ── Step 1: Clean staging ──
echo "[1/7] Clean staging directories..."
rm -rf "$INSTALLER_PAYLOAD"
rm -rf "$BUILD_DIR/pkg_extract_verify"
rm -rf "$BUILD_DIR/pkg_extract_runtime"
mkdir -p "$RUNTIME_TARGET"

# ── Step 2: Stage runtime payload from canonical source ──
echo "[2/7] Stage runtime payload..."
cd "$CANONICAL_ROOT"

RUNTIME_DIRS=(
    ".venv"
    "assets"
    "bridges"
    "cli"
    "core"
    "data"
    "product"
    "prompts"
    "schemas"
)

for dir in "${RUNTIME_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "  Copying $dir ..."
        cp -r "$dir" "$RUNTIME_TARGET/"
    else
        echo "  SKIP $dir (not found)"
    fi
done

# copy top-level files needed by runtime
for file in pyproject.toml uv.lock; do
    if [ -f "$file" ]; then
        cp "$file" "$RUNTIME_TARGET/"
        echo "  Copied $file"
    fi
done

# ── Step 3: Exclude caches, runs, logs, secrets ──
echo "[3/7] Strip caches and excluded patterns..."
find "$RUNTIME_TARGET" -type d \( \
    -name "__pycache__" -o \
    -name ".pytest_cache" -o \
    -name ".git" -o \
    -name "node_modules" -o \
    -name "runs" -o \
    -name "dist" -o \
    -name "build" \
\) -prune -exec rm -rf {} + 2>/dev/null || true

find "$RUNTIME_TARGET" -type f \( \
    -name "*.pyc" -o \
    -name "*.pyo" -o \
    -name "*.log" -o \
    -name "*.token" -o \
    -name "*.key" -o \
    -name "*.pem" -o \
    -name ".env" -o \
    -name "*.env" \
\) -delete 2>/dev/null || true

# ── Step 4: Generate manifest ──
echo "[4/7] Generate payload manifest..."
python3 "$SCRIPT_DIR/build_runtime_payload.py" \
    --payload-root "$INSTALLER_PAYLOAD" \
    --canonical-root "$CANONICAL_ROOT" \
    --version "$VERSION" \
    --output "$MANIFEST"

# ── Step 5: Security scan ──
echo "[5/7] Run security scan..."
SECURITY_LOG="$BUILD_DIR/security_scan.log"
{
    echo "=== Security Scan ==="
    echo ""

    echo "--- Local path leaks ---"
    grep -rn "/Users/audimacmini\|/home/\|C:\\\\" "$INSTALLER_PAYLOAD" 2>/dev/null || echo "PASS: No local path leaks"
    echo ""

    echo "--- Secrets/credentials ---"
    grep -rn "OPENAI_API_KEY\|ANTHROPIC_API_KEY\|GEMINI_API_KEY\|sk-[a-zA-Z0-9]\{20,\}" "$INSTALLER_PAYLOAD" --include="*.py" --include="*.json" --include="*.html" --include="*.js" 2>/dev/null || echo "PASS: No secrets found"
    echo ""

    echo "--- Sensitive file types ---"
    find "$INSTALLER_PAYLOAD" -type f \( -name "*.pem" -o -name "*.key" -o -name ".env" -o -name "*.token" \) 2>/dev/null || echo "PASS: No sensitive file types"
    echo ""

    echo "--- Allowed: /Users/Shared/AI Judge/runtime ---"
    grep -rn "/Users/Shared/AI Judge/runtime" "$INSTALLER_PAYLOAD" | head -5 || echo "(expected — hardcoded paths may appear in source referencing target location)"

} > "$SECURITY_LOG" 2>&1
cat "$SECURITY_LOG"

# ── Step 6: Build PKG ──
echo "[6/7] Build unsigned PKG..."
mkdir -p "$DIST_DIR"

pkgbuild \
    --root "$INSTALLER_PAYLOAD" \
    --identifier "local.ai-judge.runtime" \
    --version "$VERSION" \
    --install-location "/" \
    "$DIST_DIR/$PKG_NAME.pkg"

echo "  PKG built: $DIST_DIR/$PKG_NAME.pkg"

# ── Step 7: SHA-256 ──
echo "[7/7] Generate SHA-256..."
shasum -a 256 "$DIST_DIR/$PKG_NAME.pkg" | awk '{print $1}' > "$DIST_DIR/$PKG_NAME.pkg.sha256"
echo "  SHA-256: $(cat "$DIST_DIR/$PKG_NAME.pkg.sha256")"

echo ""
echo "=== Build Complete ==="
echo "PKG: $DIST_DIR/$PKG_NAME.pkg"
echo "SHA: $DIST_DIR/$PKG_NAME.pkg.sha256"
echo "Manifest: $MANIFEST"
echo "Security log: $SECURITY_LOG"

# Also copy security log to output
OUTPUT_DIR="$CANONICAL_ROOT/../output"  # will be overridden in final report
cp "$SECURITY_LOG" "$CANONICAL_ROOT/build/installer_security_scan.log" 2>/dev/null || true
