
async function loadManifest(){
  const cfg = window.RUNTIME_MANIFEST_SOURCE;
  try{
    const base = `https://api.github.com/repos/${cfg.owner}/${cfg.repo}/contents/${cfg.basePath}?ref=${cfg.branch}`;
    const headers = { 'Accept': 'application/vnd.github+json' };
    const dirs = await fetch(base, { headers, cache: 'no-store' }).then(r=>r.json());
    const toTitle = s => s.replace(/_/g, ' ').replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1));
    const courses = [];
    for(const d of dirs){
      if(d.type!=='dir') continue;
      const files = await fetch(`${base}/${d.name}`, { headers, cache: 'no-store' }).then(r=>r.json());
      const jsons = files.filter(f=>f.type==='file' && f.name.endsWith('.json')).map(f=>f.name).sort();
      if(!jsons.length) continue;
      courses.push({ name: toTitle(d.name), folder: d.name, files: jsons });
    }
    return { courses };
  }catch(e){
    return fetch('data/manifest.json').then(r=>r.json());
  }
}
document.addEventListener('DOMContentLoaded', async ()=>{
  const m = await loadManifest();
  const courseSel = document.getElementById('courseSelect');
  const personaSel = document.getElementById('personaSelect');
  const personaName = document.getElementById('personaName');
  const setOptions = (sel, items, ph) => {
    sel.innerHTML=''; const opt=document.createElement('option'); opt.value=''; opt.textContent=ph; opt.disabled=true; opt.selected=true; sel.appendChild(opt);
    items.forEach(({value,label})=>{ const o=document.createElement('option'); o.value=value; o.textContent=label; sel.appendChild(o); });
  };
  const disp = s => s.replace(/\.json$/,'').replace(/_/g,' ').replace(/\w\S*/g, w=>w[0].toUpperCase()+w.slice(1));
  setOptions(courseSel, m.courses.map(c=>({value:c.folder,label:c.name})), '-- Select Course --');
  setOptions(personaSel, [], '-- Select User --'); personaSel.disabled=true;
  courseSel.onchange = ()=>{
    const c = m.courses.find(x=>x.folder===courseSel.value);
    const items = (c?.files||[]).map(f=>({value:`data/${c.folder}/${f}`,label:disp(f)}));
    setOptions(personaSel, items, '-- Select User --');
    personaSel.disabled = items.length===0; personaName.textContent='—';
  };
  personaSel.onchange = async ()=>{
    if(!personaSel.value) return; personaName.textContent = disp(personaSel.value.split('/').pop());
  };
});
