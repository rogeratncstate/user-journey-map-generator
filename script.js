
function showBanner(msg){
  let bar = document.getElementById('errorBar');
  if(!bar){
    bar = document.createElement('div');
    bar.id = 'errorBar';
    bar.style.cssText = 'margin:8px 0 0 0;padding:10px 12px;border-radius:10px;border:1px solid #fecaca;background:#fff1f2;color:#7f1d1d;font:14px/1.4 system-ui;';
    const app = document.getElementById('app');
    app.parentNode.insertBefore(bar, app);
  }
  bar.textContent = msg;
}

// Avatar helpers
function setAvatarSrc(urls){
  const img = document.getElementById('avatarImg');
  if(!img) return;
  if(!urls || urls.length === 0){
    img.style.display = 'none';
    img.removeAttribute('src');
    return;
  }
  let i = 0;
  img.onerror = function(){
    i += 1;
    if(i < urls.length){
      img.src = urls[i];
    }else{
      img.style.display = 'none';
    }
  };
  img.onload = function(){ img.style.display = 'block'; };
  img.src = urls[0];
}
function applyAvatarForPersona(data, personaUrl){
  if (data && data.image){
    setAvatarSrc([data.image]);
    return;
  }
  try{
    const fname = (personaUrl || '').split('/').pop() || '';
    const base = fname.replace(/\.json$/i,'');
    const tryUrls = [
      `images/${base}.jpg`,
      `images/${base}.png`,
      `images/${base}.jpeg`
    ];
    setAvatarSrc(tryUrls);
  }catch{
    setAvatarSrc([]);
  }
}

// Manifest loader (GitHub-first)
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
          .sort((a,b)=> a.name.localeCompare(b.name));
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
    console.warn('Local manifest missing; using embedded sample', e);
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

function setOptions(sel, items, placeholder){
  sel.innerHTML = '';
  const ph = document.createElement('option');
  ph.value = ''; ph.textContent = placeholder; ph.disabled = true; ph.selected = true;
  sel.appendChild(ph);
  items.forEach(({value,label})=>{
    const opt = document.createElement('option');
    opt.value = value; opt.textContent = label;
    sel.appendChild(opt);
  });
}
function displayNameFromFilename(fname){
  const name = fname.replace(/\.json$/i,'').replace(/_/g,' ');
  return name.replace(/\w\S*/g, w => w.charAt(0).toUpperCase() + w.slice(1));
}

async function init(){
  const manifest = await loadManifest();
  const courseSel = document.getElementById('courseSelect');
  const personaSel = document.getElementById('personaSelect');
  const personaName = document.getElementById('personaName');

  // Populate courses
  const courseItems = (manifest.courses||[]).map(c=>({value:c.folder, label:c.name}));
  setOptions(courseSel, courseItems, '-- Select Course --');
  setOptions(personaSel, [], '-- Select User --');
  personaSel.disabled = true;
  personaName.textContent = '—';

  // Handle course selection
  courseSel.onchange = async ()=>{
    const folder = courseSel.value;
    const course = (manifest.courses||[]).find(c=>c.folder===folder);
    const files = (course && course.files) ? course.files : [];
    const fromGithub = manifest.source === 'github';
    const personas = files.map(f => {
      const fname = typeof f === 'string' ? f : f.name;
      const value = (fromGithub && typeof f === 'object' && f.url) ? f.url : `data/${folder}/${fname}`;
      return { value, label: displayNameFromFilename(fname) };
    });
    setOptions(personaSel, personas, '-- Select User --');
    personaSel.disabled = personas.length === 0;
    personaName.textContent = '—';
    clearGrid();
    setAvatarSrc([]); // clear avatar on course change
  };

  // Handle persona selection
  personaSel.onchange = async ()=>{
    if(!personaSel.value) return;
    try{
      const resp = await fetch(personaSel.value, { cache: 'no-store' });
      if(!resp.ok){ showBanner('Failed to fetch persona: ' + resp.status + ' ' + resp.statusText + '\n' + personaSel.value); return; }
      const data = await resp.json();
      applyAvatarForPersona(data, personaSel.value);
      personaName.textContent = displayNameFromFilename(personaSel.value.split('/').pop());
      render(data);
    }catch(e){
      showBanner('Persona fetch error: ' + (e && e.message ? e.message : e) + '\n' + personaSel.value);
      console.error('Persona fetch error', e);
    }
  };

  document.getElementById('printBtn').addEventListener('click', ()=> window.print());
}

function clearGrid(){
  document.getElementById('scenarioContent').textContent = '';
  const expList = document.getElementById('expectationsList'); expList.innerHTML='';
  document.querySelectorAll('.cell').forEach(c=>{
    if(!c.classList.contains('feelings-merged')) c.innerHTML='';
  });
  drawFeelings([5,5,5,5], ['', '', '', '']); // neutral
}

// ----- Rendering -----
function render(data){
  document.getElementById('scenarioContent').textContent = (typeof data.scenario === 'string') ? data.scenario : (data?.scenario?.description || '');
  const expList = document.getElementById('expectationsList');
  expList.innerHTML='';
  const exps = Array.isArray(data.expectations) ? data.expectations : (data.expectations ? [data.expectations] : []);
  exps.forEach(s=>{ const li=document.createElement('li'); li.textContent=s; expList.appendChild(li); });

  const rows=['actions','pains','opportunities'];
  document.querySelectorAll('.cell').forEach(c=>{
    if(!c.classList.contains('feelings-merged')) c.innerHTML='';
  });

  // Accept both array (preferred) or object phases {awareness,consideration,enrollment,engagement}
  let phases = Array.isArray(data.phases) ? data.phases : null;
  if(!phases && data.phases && typeof data.phases==='object'){
    const order = ['awareness','consideration','enrollment','engagement'];
    phases = order.map(k => data.phases[k]).filter(Boolean);
  }

  // Global continuous numbering for actions
  let actionCounter = 1;

  (phases || []).forEach((p,idx)=>{
    rows.forEach((row)=>{
      const cell=document.querySelector(`.cell[data-phase="${idx}"][data-row="${row}"]`);
      if(!cell) return;
      const list=p[row]||[];
      const items = Array.isArray(list) ? list : (list ? [list] : []);
      if(items.length){
        if(row === 'actions'){
          const ol=document.createElement('ol');
          ol.start = actionCounter;
          items.forEach(t=>{ const li=document.createElement('li'); li.textContent=t; ol.appendChild(li); });
          cell.appendChild(ol);
          actionCounter += items.length;
        } else {
          const ul=document.createElement('ul'); ul.className='bullets';
          items.forEach(t=>{ const li=document.createElement('li'); li.textContent=t; ul.appendChild(li); }); // fixed
          cell.appendChild(ul);
        }
      }else{ cell.textContent='—'; }
    });
  });

  const scores=(phases||[]).map(p=>{
    const raw = (p?.feelings?.score ?? p?.feelings?.feeling_score ?? 5);
    return Math.max(1, Math.min(10, Number(raw)));
  }).slice(0,4);
  const quotes=(phases||[]).map(p=>p?.feelings?.quote || '').slice(0,4);
  drawFeelings(scores, quotes);
}

// Curve smoothing
function catmullRom2bezier(points){
  if(points.length<2) return '';
  const p = points.map(pt=>({x:pt.x, y:pt.y}));
  let d = `M ${p[0].x} ${p[0].y}`;
  for(let i=0;i<p.length-1;i++){
    const p0 = p[i-1] || p[i];
    const p1 = p[i];
    const p2 = p[i+1];
    const p3 = p[i+2] || p[i+1];
    const cp1x = p1.x + (p2.x - p0.x)/6;
    const cp1y = p1.y + (p2.y - p0.y)/6;
    const cp2x = p2.x - (p3.x - p1.x)/6;
    const cp2y = p2.y - (p3.y - p1.y)/6;
    d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }
  return d;
}

function drawFeelings(scores, quotes){
  const svg=document.getElementById('feelingsSVG');
  const path=document.getElementById('feelingsPath');
  const markers=document.getElementById('markers');
  const guides=document.getElementById('guides');
  const yaxis=document.getElementById('yaxis');
  const qlayer=document.getElementById('quotesLayer');
  const cols = qlayer.querySelectorAll('.qcol');

  const W=1000, H=220, PADX=68, PADY=20;
  const usableW = W - PADX*2;
  const usableH = H - PADY*2;

  yaxis.innerHTML = '';
  const axisX = PADX - 28;
  const axisLine = document.createElementNS('http://www.w3.org/2000/svg','line');
  axisLine.setAttribute('x1', String(axisX));
  axisLine.setAttribute('x2', String(axisX));
  axisLine.setAttribute('y1', String(PADY));
  axisLine.setAttribute('y2', String(H - PADY));
  yaxis.appendChild(axisLine);

  const topY = PADY;
  const midY = PADY + usableH/2;
  const botY = H - PADY;
  [['🙂', topY], ['😐', midY], ['🙁', botY]].forEach(([ch, y])=>{
    const t = document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x', String(axisX - 18));
    t.setAttribute('y', String(y));
    t.textContent = ch;
    yaxis.appendChild(t);
  });

  guides.innerHTML='';
  for(let i=1;i<=10;i++){
    const y = PADY + usableH - ((i-1)/9)*usableH;
    const g = document.createElementNS('http://www.w3.org/2000/svg','line');
    g.setAttribute('x1', String(PADX));
    g.setAttribute('x2', String(W-PADX));
    g.setAttribute('y1', String(y));
    g.setAttribute('y2', String(y));
    g.setAttribute('stroke', '#e5e7eb');
    g.setAttribute('stroke-width', '1');
    guides.appendChild(g);
  }

  const xs=[0,1,2,3].map(i=>PADX + (usableW/3)*i);
  const ys=scores.map(s=> PADY + usableH - ((s-1)/9)*usableH);
  const points = xs.map((x,i)=>({x, y:ys[i]}));
  const d = catmullRom2bezier(points);
  path.setAttribute('d', d);
  path.setAttribute('stroke', getComputedStyle(document.documentElement).getPropertyValue('--path').trim() || '#111827');

  markers.innerHTML='';
  xs.forEach((x,idx)=>{
    const y=ys[idx];
    const g = document.createElementNS('http://www.w3.org/2000/svg','g');
    g.setAttribute('class','marker');
    const c = document.createElementNS('http://www.w3.org/2000/svg','circle');
    c.setAttribute('cx', String(x)); c.setAttribute('cy', String(y)); c.setAttribute('r','12');
    const t = document.createElementNS('http://www.w3.org/2000/svg','text');
    t.setAttribute('x', String(x)); t.setAttribute('y', String(y)); t.textContent=String(idx+1);
    g.appendChild(c); g.appendChild(t);
    markers.appendChild(g);
  });

  // quotes in 4 non-overlapping columns
  cols.forEach(c => c.innerHTML='');
  const layerRect = svg.getBoundingClientRect();
  const toPxY = y => (y / H) * layerRect.height;
  quotes.forEach((quote, idx)=>{
    if(!quote) return;
    const box = document.createElement('div');
    const isAbove = scores[idx] <= 5;
    box.className = 'quote-box ' + (isAbove ? 'above' : 'below');
    box.textContent = quote;
    const col = cols[idx];
    col.appendChild(box);
    requestAnimationFrame(()=>{
      const rect = box.getBoundingClientRect();
      const py = toPxY(ys[idx]);
      const layer = col.getBoundingClientRect();
      const offset = 16;
      const top = isAbove ? (py - rect.height - offset) : (py + offset);
      box.style.left = '0px';
      box.style.top = Math.max(0, Math.min(top - layer.top + qlayer.getBoundingClientRect().top, layer.height - rect.height)) + 'px';
    });
  });
}

document.addEventListener('DOMContentLoaded', ()=>{
  init().catch(e=>{
    console.error('Init error', e);
    showBanner('Could not initialize app. Check console for details.');
  });
});
