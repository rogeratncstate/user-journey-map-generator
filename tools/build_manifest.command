#!/bin/bash
# Double-click this file on macOS to regenerate data/manifest.json
# It runs the Python builder located next to this script.

# Resolve folder of this .command, then cd to project root
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR%/tools}"
cd "$PROJECT_ROOT" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display dialog "python3 not found. Please install Xcode Command Line Tools or Python 3." with icon caution buttons {"OK"}'
  exit 1
fi

python3 tools/build_manifest.py
STATUS=$?

if [ $STATUS -eq 0 ]; then
  osascript -e 'display notification "Manifest updated successfully." with title "Journey Map"'
else
  osascript -e 'display dialog "Manifest build failed. See Terminal for details." with icon stop buttons {"OK"}'
fi

exit $STATUS