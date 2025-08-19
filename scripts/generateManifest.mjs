import { promises as fs } from 'node:fs';
import { join, resolve } from 'node:path';

const ROOT = resolve(new URL('.', import.meta.url).pathname, '..', '..');
const DATA_DIR = join(ROOT, 'data');
const MANIFEST = join(DATA_DIR, 'manifest.json');

function titleFromFolder(name){
  return name.replace(/_/g,' ').replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1));
}

async function main(){
  const entries = await fs.readdir(DATA_DIR, { withFileTypes: true }).catch(()=>[]);
  const courses = [];
  for (const dirent of entries){
    if(!dirent.isDirectory()) continue;
    const folder = dirent.name;
    const files = (await fs.readdir(join(DATA_DIR, folder))).filter(f => f.endsWith('.json') && f !== 'manifest.json').sort();
    if(!files.length) continue;
    courses.push({ name: titleFromFolder(folder), folder, files });
  }
  const manifest = { courses };
  await fs.writeFile(MANIFEST, JSON.stringify(manifest, null, 2));
  console.log(`[OK] Wrote manifest with ${courses.length} course(s) -> ${MANIFEST}`);
}

main().catch(err => { console.error(err); process.exit(1); });