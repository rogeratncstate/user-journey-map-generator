import { promises as fs } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOT = resolve(new URL('.', import.meta.url).pathname, '..', '..');
const DATA_DIR = join(ROOT, 'data');
const MANIFEST = join(DATA_DIR, 'manifest.json');

function titleFromFolder(name){
  return name.replace(/_/g,' ').replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1));
}

async function main(){
  await fs.mkdir(DATA_DIR, { recursive: true });
  let entries = [];
  try { entries = await fs.readdir(DATA_DIR, { withFileTypes: true }); } catch {}
  const courses = [];
  for(const d of entries){
    if(!d.isDirectory()) continue;
    const folder = d.name;
    let files = [];
    try {
      files = (await fs.readdir(join(DATA_DIR, folder))).filter(f=>f.endsWith('.json') && f!=='manifest.json').sort();
    } catch {}
    if(!files.length) continue;
    courses.push({ name: titleFromFolder(folder), folder, files });
  }
  const manifest = { courses };
  await fs.writeFile(MANIFEST, JSON.stringify(manifest, null, 2));
  console.log(`[OK] Wrote manifest with ${courses.length} course(s) -> ${MANIFEST}`);
}

main().catch(e=>{ console.error(e); process.exit(1); });
