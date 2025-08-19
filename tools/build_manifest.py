#!/usr/bin/env python3
import json, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data'
MANIFEST = DATA / 'manifest.json'

def title_from_folder(name):
    name = name.replace('_',' ')
    return re.sub(r'\w\S*', lambda m: m.group(0)[0].upper()+m.group(0)[1:], name)

def main():
    DATA.mkdir(parents=True, exist_ok=True)
    courses = []
    for entry in sorted(DATA.iterdir()):
        if not entry.is_dir():
            continue
        files = [f.name for f in sorted(entry.glob('*.json')) if f.name != 'manifest.json']
        if not files: 
            continue
        courses.append({"name": title_from_folder(entry.name), "folder": entry.name, "files": files})
    MANIFEST.write_text(json.dumps({"courses": courses}, indent=2), encoding='utf-8')
    print(f"[OK] Wrote manifest with {len(courses)} course(s) -> {MANIFEST}")

if __name__ == '__main__':
    main()
