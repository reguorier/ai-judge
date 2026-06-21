#!/bin/bash
# Build Demo Replay Pack
# public-demo-readiness-v1.0.0
#
# Packages all demo replay directories into a distributable archive.

set -euo pipefail

BASE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PRODUCT_DIR="/Users/audimacmini/Library/Application Support/AI Judge/runtime/product"
DEMO_DIR="$PRODUCT_DIR/demo"
REPLAY_DIR="$DEMO_DIR/replay"
OUTPUT_DIR="${1:-$BASE_DIR/output}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
ARCHIVE_NAME="demo_replay_pack_${TIMESTAMP}.tar.gz"

echo "=== AI Judge Demo Replay Pack Builder ==="
echo ""

# Check manifest exists
MANIFEST="$DEMO_DIR/demo_replay_manifest.json"
if [ ! -f "$MANIFEST" ]; then
    echo "ERROR: demo_replay_manifest.json not found at $MANIFEST"
    exit 1
fi

# Validate manifest
echo "[1/4] Validating manifest..."
python3 -c "
import json, os
with open('$MANIFEST') as f:
    m = json.load(f)
replays = m.get('replays', [])
print(f'  Found {len(replays)} replays')
for r in replays:
    rdir = os.path.join('$DEMO_DIR', r['path'])
    for fname in r.get('files', []):
        fpath = os.path.join(rdir, fname)
        assert os.path.isfile(fpath), f'Missing: {fpath}'
    print(f'  [OK] {r[\"id\"]} — {len(r[\"files\"])} files')
print('Manifest validation passed')
"

# Create output directory
mkdir -p "$OUTPUT_DIR"

# Copy replay files to staging
echo "[2/4] Staging replay files..."
STAGING="$OUTPUT_DIR/demo_replay_staging"
rm -rf "$STAGING"
mkdir -p "$STAGING"

# Copy manifest
cp "$MANIFEST" "$STAGING/demo_replay_manifest.json"

# Copy each replay directory
python3 -c "
import json, shutil, os
with open('$MANIFEST') as f:
    m = json.load(f)
for r in m['replays']:
    src = os.path.join('$DEMO_DIR', r['path'])
    dst = os.path.join('$STAGING', r['path'])
    shutil.copytree(src, dst)
    print(f'  Copied {r[\"id\"]}')
"

# Copy disclaimer and privacy notice
cp "$DEMO_DIR/demo_disclaimer.md" "$STAGING/" 2>/dev/null || true
cp "$DEMO_DIR/demo_privacy_notice.md" "$STAGING/" 2>/dev/null || true

# Create archive
echo "[3/4] Creating archive..."
cd "$OUTPUT_DIR"
tar -czf "$ARCHIVE_NAME" -C "$OUTPUT_DIR" demo_replay_staging

ARCHIVE_SIZE=$(ls -lh "$ARCHIVE_NAME" | awk '{print $5}')
echo "  Archive created: $ARCHIVE_NAME ($ARCHIVE_SIZE)"

# Cleanup staging
rm -rf "$STAGING"

# Verify archive
echo "[4/4] Verifying archive..."
VERIFY_DIR="$OUTPUT_DIR/demo_replay_verify"
rm -rf "$VERIFY_DIR"
mkdir -p "$VERIFY_DIR"
tar -xzf "$ARCHIVE_NAME" -C "$VERIFY_DIR"

python3 -c "
import json, os
with open(os.path.join('$VERIFY_DIR', 'demo_replay_staging', 'demo_replay_manifest.json')) as f:
    m = json.load(f)
for r in m['replays']:
    rdir = os.path.join('$VERIFY_DIR', 'demo_replay_staging', r['path'])
    for fname in r.get('files', []):
        fpath = os.path.join(rdir, fname)
        assert os.path.isfile(fpath), f'Missing in archive: {fpath}'
    print(f'  [OK] {r[\"id\"]} verified in archive')
print('Archive verification passed')
"

rm -rf "$VERIFY_DIR"

echo ""
echo "=== Build Complete ==="
echo "Archive: $OUTPUT_DIR/$ARCHIVE_NAME"
echo "DEMO_REPLAY_PACK_BUILD_PASS"