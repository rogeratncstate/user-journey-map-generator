
# User Journey Map (v14)

- Emoji Y-axis on feelings graph (🙂 top, 😐 middle, 🙁 bottom)
- Soft print behavior to avoid splitting the feelings row across pages
- Prebuilt `data/manifest.json` for drag-and-deploy
- Optional build tools for regenerating manifest

## Quick start (local)
```bash
python3 -m http.server 5173
# open http://localhost:5173
```

## Vercel (static)
- Framework Preset: **Other**
- Install Command: *(blank or `npm i`)*
- Build Command: *(blank)*
- Output Directory: **`.`**

## Rebuild manifest (optional)
```bash
npm i
npm run build  # Node script
# or macOS
chmod +x tools/build_manifest.command && tools/build_manifest.command
# or POSIX
sh tools/build_manifest.sh
```
