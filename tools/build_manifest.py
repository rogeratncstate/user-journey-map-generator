#!/usr/bin/env python3
"""
build_manifest.py
Scans ./data/* directories for .json persona files and writes ./data/manifest.json.

Folder structure:
data/
  Course_Folder_A/
    user_one.json
    user_two.json
  Course_Folder_B/
    ...
Outputs manifest.json like:
{
  "courses": [
    {"name": "Course Folder A", "folder": "Course_Folder_A", "files": ["user_one.json", "user_two.json"]},
    ...
  ]
}
"""
import json, os, sys, re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
MANIFEST = DATA / 'manifest.json'

def title_from_folder(folder_name: str) -> str:
    # "Introduction_to_Data_Science" -> "Introduction To Data Science"
    name = folder_name.replace('_', ' ')
    return re.sub(r'\w\S*', lambda m: m.group(0)[0].upper() + m.group(0)[1:], name)

def main():
    if not DATA.exists():
        print(f"[WARN] data directory not found at {DATA}", file=sys.stderr)
        sys.exit(1)

    courses = []
    for entry in sorted(DATA.iterdir()):
        if not entry.is_dir():
            continue
        files = [f.name for f in sorted(entry.glob('*.json')) if f.name != 'manifest.json']
        if not files:
            continue
        courses.append({
            "name": title_from_folder(entry.name),
            "folder": entry.name,
            "files": files
        })

    manifest = {"courses": courses}
    MANIFEST.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(f"[OK] Wrote manifest with {len(courses)} course(s) -> {MANIFEST}")

if __name__ == "__main__":
    main()