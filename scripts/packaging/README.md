# Canonical PKG Build Pipeline

## Overview

Builds an unsigned local macOS `.pkg` installer from the canonical source repo.

## Source

```
/Users/audimacmini/Documents/ai-judge-skill
```

## Target Runtime

```
/Users/Shared/AI Judge/runtime
```

## Files

- `build_macos_pkg.sh` — main build script
- `build_runtime_payload.py` — manifest/hash generator

## Usage

```bash
bash scripts/packaging/build_macos_pkg.sh
```

## What It Does

1. Cleans staging directory `build/installer_payload`
2. Stages runtime files from canonical source only
3. Strips caches, runs, logs, tokens, secrets, `.git`, `node_modules`
4. Generates `build/installer_payload_manifest.json` with SHA-256 hashes
5. Runs security scan for path leaks and secrets
6. Builds unsigned `.pkg` into `dist/`
7. Writes SHA-256 checksum

## Artifacts

- `dist/AI-Judge-v<VERSION>-macOS-arm64.pkg`
- `dist/AI-Judge-v<VERSION>-macOS-arm64.pkg.sha256`
- `build/installer_payload_manifest.json`

## Verification

After build, extract and verify:

```bash
PKG="dist/AI-Judge-<version>-macOS-arm64.pkg"
EXTRACT="build/pkg_extract_verify"
pkgutil --expand-full "$PKG" "$EXTRACT"
find "$EXTRACT" -path "*/product/client_api.py" -print
```

## Not Production

This pipeline produces unsigned, non-notarized local installer artifacts.
Not for public or production distribution.
