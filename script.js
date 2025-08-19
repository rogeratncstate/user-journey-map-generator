let manifest = null;

async function loadJSON(path){ const res = await fetch(path); return res.json(); }
async function loadManifest(){ const res = await fetch('data/manifest.json'); return res.json(); }

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
  return name.replace(/\w\S*/g, (w)=> w.charAt(0).toUpperCase() + w.slice(1));
}

async function init(){
  manifest = await loadManifest();
  const courseSel = document.getElementById('courseSelect');
  const personaSel = document.getElementById('personaSelect');
  const personaName = document.getElementById('personaName');

  // Populate course dropdown with placeholder
  const courseItems = manifest.courses.map(c=>({value:c.folder, label:c.name}));
  setOptions(courseSel, courseItems, '-- Select Course --');
  personaSel.disabled = true;
  setOptions(personaSel, [], '-- Select User --');
  personaName.textContent = '—';

  courseSel.onchange = async ()=>{
    const folder = courseSel.value;
    const course = manifest.courses.find(c=>c.folder===folder);
    const files = (course && course.files) ? course.files : [];
    const personas = files.map(f=>({ value:`data/${folder}/${f}`, label: displayNameFromFilename(f) }));
    setOptions(personaSel, personas, '-- Select User --');
    personaSel.disabled = personas.length === 0;
    personaName.textContent = '—';
    // clear content until persona chosen
    clearGrid();
  };

  personaSel.onchange = async ()=>{
    if(!personaSel.value) return;
    const data = await loadJSON(personaSel.value);
    personaName.textContent = displayNameFromFilename(personaSel.value.split('/').pop());
    render(data);
  };
}

function clearGrid(){
  document.getElementById('scenarioContent').textContent = '';
  const expList = document.getElementById('expectationsList'); expList.innerHTML='';
  document.querySelectorAll('.cell').forEach(c=>{
    if(!c.classList.contains('feelings-merged')) c.innerHTML='';
  });
  drawFeelings([5,5,5,5], ['', '', '', '']); // neutral baseline
}

// ---- Rendering ----
function render(data){
  document.getElementById('scenarioContent').textContent = data.scenario || '';
  const expList = document.getElementById('expectationsList');
  expList.innerHTML='';
  (data.expectations || []).forEach(s=>{
    const li=document.createElement('li'); li.textContent=s; expList.appendChild(li);
  });

  const rows=['actions','pains','opportunities'];
  document.querySelectorAll('.cell').forEach(c=>{
    if(!c.classList.contains('feelings-merged')) c.innerHTML='';
  });
  (data.phases || []).forEach((p,idx)=>{
    rows.forEach(row=>{
      const cell=document.querySelector(`.cell[data-phase="${idx}"][data-row="${row}"]`);
      if(!cell) return;
      const list=p[row]||[];
      if(Array.isArray(list)&&list.length){
        const ul=document.createElement('ul'); ul.className='bullets';
        list.forEach(t=>{ const li=document.createElement('li'); li.textContent=t; ul.appendChild(li); });
        cell.appendChild(ul);
      }else{ cell.textContent='—'; }
    });
  });

  const scores=(data.phases||[]).map(p=>{
    const s=Number(p?.feelings?.score ?? 5);
    return Number.isFinite(s)? Math.min(10,Math.max(1,s)):5;
  }).slice(0,4);
  const quotes=(data.phases||[]).map(p=>p?.feelings?.quote || '').slice(0,4);
  drawFeelings(scores, quotes);
}

// smoothing
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
  const qlayer=document.getElementById('quotesLayer');
  const cols = qlayer.querySelectorAll('.qcol');

  const W=1000, H=220, PADX=40, PADY=20;
  const usableW = W - PADX*2;
  const usableH = H - PADY*2;

  // guides
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

  // markers
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

document.getElementById('printBtn').addEventListener('click', ()=> window.print());

// init();  // moved to DOMContentLoaded in v11

// v11 helpers: show error banner
function showError(msg){
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

document.addEventListener('DOMContentLoaded', async ()=>{
  try{
    if(location.protocol === 'file:'){
      showError('To enable the course dropdown, please serve this folder over HTTP (e.g., run “python3 -m http.server” in the project root) so the browser can fetch data/manifest.json.');
    }
    await init();
  }catch(e){
    console.error('Init failed:', e);
    showError('Could not load courses. Make sure data/manifest.json exists and you are serving the folder over HTTP.');
  }
});
