#!/bin/sh
# POSIX fallback: run from anywhere, rebuilding data/manifest.json
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR%/tools}"
cd "$PROJECT_ROOT" || exit 1
exec python3 tools/build_manifest.py