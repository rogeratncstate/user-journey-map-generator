# User Journey Map (v9)

This build adds an **automatic manifest generator** so you don't have to manually edit `data/manifest.json`.

## How it works
The page reads `data/manifest.json` to populate the **Course** dropdown, and each course lists the personas (JSON files) under that course's folder.

## Generate the manifest
1. Put your course folders and persona JSON files here:
   ```
   data/
     Introduction_to_Data_Science/
       evolving_evan.json
       determined_diana.json
       career_changer_carlos.json
     Another_Course_Name/
       your_user_one.json
       your_user_two.json
   ```
2. Run the build script:
   ```bash
   # from the folder containing tools/build_manifest.py
   python3 tools/build_manifest.py
   ```
   You should see:
   ```
   [OK] Wrote manifest with N course(s) -> data/manifest.json
   ```

## Naming conventions
- **Course folder names**: use underscores; UI will show them Title Cased (underscores → spaces).
- **Persona files**: `snake_case.json`. The UI shows **Title Case** without the `.json` extension.

## Use the app
1. Open `index.html` in a browser.
2. Choose a **Course** → choose a **User**.
3. Print via **Print / Save as PDF** when ready.
## macOS: Double‑click to build
Use the included script:

- `tools/build_manifest.command` — double‑clickable.
  - On first run you may need to grant execute permission:
    ```bash
    chmod +x tools/build_manifest.command
    ```
  - If macOS blocks it as downloaded from the internet, run:
    ```bash
    xattr -d com.apple.quarantine tools/build_manifest.command
    ```
- Or run the portable shell script:
  ```bash
  sh tools/build_manifest.sh
  ```

## Local development tip (fixes dropdown issues)
Modern browsers block `fetch()` from local files. Serve the folder over HTTP:

```bash
# from project root
python3 -m http.server 8000
# then open
open http://localhost:8000
```

If you still don’t see courses:
- Run the builder to generate `data/manifest.json`:
  ```bash
  python3 tools/build_manifest.py
  ```
- Check your browser devtools Console/Network for errors.


## Deploy to Vercel (recommended)
This repo is a static site. Vercel can run a small Node build step that generates `data/manifest.json` from your folders, then serve everything statically.

### One‑time setup
1. Push this folder to GitHub (or GitLab/Bitbucket).
2. In Vercel, **New Project** → import your repo.
3. **Framework Preset**: *Other* (static).
4. **Build Command**: `npm run build`
5. **Output Directory**: `.` (project root)
6. **Install Command**: `npm i`

> The build command runs `scripts/generateManifest.mjs` to create `data/manifest.json` from the files under `data/`.

### Local dev
```bash
npm i
npm run dev
# opens a static server on http://localhost:5173 (press Ctrl+C to stop)
```

### Add courses / personas
- Create a folder under `data/` for each course (use underscores in names).
- Drop `.json` persona files into that folder.
- Deploy: Vercel rebuild runs the generator and your dropdowns update automatically.


## Vercel Deployment (clean static setup)

### Recommended: Git-based deploy
1. Push this folder to GitHub/GitLab/Bitbucket.
2. In Vercel → **New Project** → Import your repo.
3. Settings:
   - **Framework Preset**: Other
   - **Install Command**: `npm i`
   - **Build Command**: `npm run vercel-build`
   - **Output Directory**: `.`
4. Deploy. The build step generates `data/manifest.json` from your `data/*/*.json` files.

### Alternative: Drag‑and‑drop deploy
We already included a prebuilt `data/manifest.json`, so you can zip and drag this folder into Vercel **without any build step**.

> If you later add files, regenerate the manifest locally:
> ```bash
> npm i
> npm run build
> ```
> Commit & redeploy, or re-upload the updated folder.

### Common Vercel errors & fixes
- **DEPLOYMENT_NOT_FOUND / 404 NOT_FOUND**  
  Usually a bad route or stale preview link. Re-deploy and open the new URL from the dashboard.
- **BODY_NOT_A_STRING_FROM_FUNCTION / Function 502**  
  Indicates a serverless/edge function run. This project is static — remove any `vercel.json` with function builds. We’ve removed it here.
- **DEPLOYMENT_NOT_READY_REDIRECTING (303)**  
  The preview isn’t built yet. Wait for build to finish, then refresh.
- **ROUTER_CANNOT_MATCH (502)**  
  Accessing a path without a file. Ensure you’re opening `/` (root) and that `index.html` exists at the project root.
- **DNS_* errors**  
  Custom domain misconfig. Use the default `*.vercel.app` link first; add DNS only after deploy works.
- **INFINITE_LOOP_DETECTED (508)**  
  Rare. Check for client-side redirects or meta refresh loops.

If anything still misbehaves, confirm:
- `data/manifest.json` exists at deploy time (open it at `/data/manifest.json`).
- Your course folder and persona JSONs are committed in `data/<Course_Folder>/`.
- Open DevTools → Network tab to ensure `manifest.json` returns 200 OK.
