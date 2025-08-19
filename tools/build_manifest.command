#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR%/tools}"
cd "$PROJECT_ROOT" || exit 1
if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "python3 not found. Please install Python 3." with icon caution buttons {"OK"}'
  exit 1
fi
python3 tools/build_manifest.py
