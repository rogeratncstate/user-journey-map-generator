// script.js (patched loadManifest and persona loading parts)

async function loadManifest(){
  const cfg = window.RUNTIME_MANIFEST_SOURCE;
  if (cfg && cfg.type === 'github') {
    try {
      const ts = Date.now();
      const base = `https://api.github.com/repos/${cfg.owner}/${cfg.repo}/contents/${cfg.basePath}?ref=${cfg.branch}&_=${ts}`;
      const headers = { 'Accept': 'application/vnd.github+json' };
      const dirsRes = await fetch(base, { headers, cache: 'no-store' });
      if (!dirsRes.ok) throw new Error('GitHub API ' + dirsRes.status);
      const dirs = await dirsRes.json();
      const toTitle = s => s.replace(/_/g, ' ').replace(/\w\S*/g, w => w[0].toUpperCase() + w.slice(1));
      const courses = [];
      for (const entry of dirs) {
        if (entry.type !== 'dir') continue;
        const folder = entry.name;
        const filesURL = `https://api.github.com/repos/${cfg.owner}/${cfg.repo}/contents/${cfg.basePath}/${folder}?ref=${cfg.branch}&_=${Date.now()}`;
        const filesRes = await fetch(filesURL, { headers, cache: 'no-store' });
        if (!filesRes.ok) continue;
        const files = await filesRes.json();
        const jsons = files
          .filter(f => f.type === 'file' && f.name.toLowerCase().endsWith('.json') && f.name !== 'manifest.json')
          .map(f => ({ name: f.name, url: f.download_url }))
          .sort((a,b) => a.name.localeCompare(b.name));
        if (jsons.length) courses.push({ name: toTitle(folder), folder, files: jsons });
      }
      if (courses.length) return { source: 'github', courses };
    } catch (e) {
      console.warn('GitHub manifest fetch failed; using local fallback', e);
    }
  }
  try {
    const res = await fetch('data/manifest.json', { cache: 'no-store' });
    if (res.ok) {
      const m = await res.json();
      return { source: 'local', ...m };
    }
  } catch(e) {
    console.warn('Local manifest missing', e);
  }
  return {
    source: 'embedded',
    courses: [{
      name: 'Introduction To Data Science',
      folder: 'Introduction_to_Data_Science',
      files: ['evolving_evan.json','determined_diana.json','career_changer_carlos.json']
    }]
  };
}

// When populating personas, use .url if available
function populatePersonas(course, manifest){
  const personaSel = document.getElementById('personaSelect');
  if(!course){ personaSel.innerHTML=''; personaSel.disabled=true; return; }
  const fromGithub = manifest.source === 'github';
  const options = course.files.map(f => {
    const fname = typeof f === 'string' ? f : f.name;
    const value = (fromGithub && typeof f === 'object' && f.url) ? f.url : `data/${course.folder}/${fname}`;
    return { value, label: displayNameFromFilename(fname) };
  });
  setOptions(personaSel, options, '-- Select User --');
  personaSel.disabled = false;
}

// Example handler for personaSelect change
document.getElementById('personaSelect').addEventListener('change', async (e)=>{
  const url = e.target.value;
  if(!url) return;
  try {
    const resp = await fetch(url, { cache: 'no-store' });
    if(!resp.ok) { alert('Fetch error: '+resp.status); return; }
    const data = await resp.json();
    document.getElementById('personaName').textContent = displayNameFromFilename(url.split('/').pop());
    render(data);
  } catch(err) {
    alert('Persona fetch error: '+err);
  }
});
