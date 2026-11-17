/** Samaratan Director's Desk — accessible, zero-dependency studio controller. */
const $ = (id) => document.getElementById(id);
const ROUTES = new Set(['create', 'productions', 'workflow', 'system']);
const PRESETS = Object.freeze({
  noir: 'A rain-soaked detective thriller in a forgotten coastal city. A detective returns to a closed murder case, finds a witness whose story keeps changing, and chooses between following the clues or protecting a suspect. Cinematic nighttime streets, tense conversations, and meaningful branching consequences.',
  scifi: 'A grounded science-fiction mystery aboard a research vessel orbiting a silent planet. A lone astronaut discovers a transmission in their own voice from a future that has not happened. The player explores the ship, questions the crew, and makes a choice that changes the final scene.',
  horror: 'A psychological thriller inside a remote mountain hotel after the final guest has vanished. An exhausted night manager finds recordings of tomorrow, encounters someone who looks exactly like them, and must choose whether to follow the evidence or confront their own memories.'
});
const PAGE_NAMES = {create:"DIRECTOR'S DESK",productions:'PRODUCTIONS',workflow:'WORKFLOW',system:'SYSTEM STATUS'};
const state = {caps:null,jobs:[],polling:false,currentJob:null,selectedJob:null,toastTimer:null,focusReturn:null};
const els = {form:$('create-form'),prompt:$('prompt'),provider:$('provider'),export:$('export'),submit:$('submit'),overlay:$('production-overlay')};
const API = {
  async json(path, options = {}) {
    const response = await fetch(path, {...options, headers:{...(options.body?{'Content-Type':'application/json'}:{}),...(options.headers||{})}});
    let data;
    try { data = await response.json(); } catch { throw new Error('The local service returned an unreadable response.'); }
    if (!response.ok) {
      const detail = data?.detail;
      throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status}).`);
    }
    return data;
  },
  capabilities:()=>API.json('/api/capabilities'),
  recent:()=>API.json('/api/jobs'),
  getJob:(id)=>API.json(`/api/jobs/${encodeURIComponent(id)}`),
  plan:(id)=>API.json(`/api/jobs/${encodeURIComponent(id)}/plan`),
  create:(value)=>API.json('/api/jobs',{method:'POST',body:JSON.stringify(value)})
};
function el(tag, className = '', content = '') {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (content !== undefined && content !== null) node.textContent = String(content);
  return node;
}
function formatDate(value) {
  const date = new Date(value);
  if (!Number.isFinite(date.getTime())) return 'Unknown date';
  return new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',year:'numeric'}).format(date);
}
function notify(message) {
  const toast = $('toast');
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(state.toastTimer);
  state.toastTimer = setTimeout(()=>{toast.hidden = true},4700);
}
function routeTo(name) {
  if (!ROUTES.has(name)) name='create';
  for (const node of document.querySelectorAll('.view')) node.classList.toggle('is-active',node.id === `view-${name}`);
  for (const node of document.querySelectorAll('[data-route]')) {
    const active = node.dataset.route === name;
    node.classList.toggle('is-active',active);
    if (active && node.classList.contains('nav-item')) node.setAttribute('aria-current','page');
    else node.removeAttribute('aria-current');
  }
  $('breadcrumb-page').textContent = PAGE_NAMES[name];
  document.title = 'Samaratan — ' + ({create:"Director’s Desk",productions:'Productions',workflow:'Workflow',system:'System Status'}[name]);
  if (name === 'productions') refreshJobs();
  if (name === 'system') refreshCapabilities();
  window.scrollTo({top:0,behavior:window.matchMedia('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'});
}
function currentRoute(){return window.location.hash.replace(/^#\/?/,'').split('/')[0]||'create'}
function updateCount(){$('char-count').textContent = `${els.prompt.value.length.toLocaleString()} / 6000`}
function displayProviderHint(){
  const copy={demo:'Free demo uses a sample story. No model calls or credits.',codex:'Uses your locally authenticated Codex CLI. Normal account limits apply.',claude:'Uses your locally authenticated Claude Code CLI. Normal account limits apply.'};
  $('provider-note').textContent = copy[els.provider.value] || copy.demo;
}
async function refreshCapabilities(){
  const label = $('connection-label');
  try{
    const caps = await API.capabilities();
    state.caps=caps;
    label.textContent='Local service online';
    $('rail-status-dot').classList.remove('offline');
    $('server-state').querySelector('.connection-dot')?.classList.remove('offline');
    for(const option of els.provider.options){
      option.disabled = !caps.providers?.[option.value];
      const base = {demo:'Demo director · Free',codex:'Codex · Your subscription',claude:'Claude Code · Your subscription'}[option.value];
      option.textContent = base + (option.disabled?' · CLI not found':'');
    }
    if(els.provider.selectedOptions[0]?.disabled) els.provider.value='demo';
    const canExport = !!caps.engines?.godot4?.windows_export;
    els.export.disabled=!canExport;
    if(!canExport) els.export.checked=false;
    $('export-note').textContent=canExport?'Godot CLI detected. Windows templates still required.':'Not available: Godot CLI is not installed on this build machine.';
    displayProviderHint();
    renderSystem(caps);
  }catch(error){
    state.caps=null;
    label.textContent='Service unavailable';
    $('rail-status-dot').classList.add('offline');
    $('server-state').querySelector('.connection-dot')?.classList.add('offline');
    renderSystem(null);
  }
}
function renderSystem(caps){
  const container=$('system-cards');
  container.replaceChildren();
  const records=[
    {name:'LOCAL SERVICE',value:caps?'Online':'Unavailable',ready:!!caps,description:'The local server orchestrating story plans, source output, and production jobs.'},
    {name:'DIRECTOR · DEMO',value:'Deterministic',ready:!!caps?.providers?.demo,description:'Free offline production fixture. It does not invoke a language model.'},
    {name:'DIRECTOR · CODEX',value:caps?.providers?.codex?'Ready':'Not detected',ready:!!caps?.providers?.codex,description:'Connects to your existing Codex CLI installation and signed-in account.'},
    {name:'DIRECTOR · CLAUDE',value:caps?.providers?.claude?'Ready':'Not detected',ready:!!caps?.providers?.claude,description:'Connects to your existing Claude Code CLI installation and signed-in account.'},
    {name:'GAME ENGINE',value:'Godot 4',ready:!!caps?.engines?.godot4?.source_generation,description:'Generates engine project sources. AAA cinematic rendering is not yet implemented.'},
    {name:'WINDOWS BUILD',value:caps?.engines?.godot4?.windows_export?'CLI detected':'Build worker needed',ready:!!caps?.engines?.godot4?.windows_export,description:'Native .exe packaging requires Godot and matching export templates.'}
  ];
  for(const item of records){
    const card=el('article','system-card');
    card.append(el('span','',item.name),el('div','system-symbol',item.ready?'✳':'◇'),el('h2','',item.value),el('p','',item.description),el('span',`system-pill${item.ready?'':' offline'}`,item.ready?'AVAILABLE':'NOT READY'));
    container.append(card);
  }
}
async function refreshJobs(){
  const list=$('jobs-list');
  try{
    const response=await API.recent();
    state.jobs=response.jobs||[];
    list.replaceChildren();
    if(!state.jobs.length){
      const empty=el('div','empty-state');
      empty.append(el('span','empty-symbol','◇'),el('strong','','No productions yet'),el('p','','Your first project will appear here after you begin production.'));
      const go=el('button','quiet-button','Create a production ↗');go.type='button';go.addEventListener('click',()=>{location.hash='#create'});empty.append(go);list.append(empty);return;
    }
    state.jobs.forEach((job,i)=>{
      const row=el('button','job-row');row.type='button';row.setAttribute('aria-label',`Inspect production ${job.title||job.prompt_preview||'Untitled'}, status ${job.status}`);
      const detail=el('span','job-detail');detail.append(el('span','job-title',job.title||job.prompt_preview||'Untitled production'),el('span','job-meta',`${job.provider==='demo'?'Demo director':job.provider+' director'} · ${job.id.slice(0,8)}`));
      const status=el('span',`job-status ${job.status}`,job.status);
      row.append(el('span','job-no',String(state.jobs.length-i).padStart(2,'0')),detail,el('span','job-date',formatDate(job.created_at)),status,el('span','job-arrow','↗'));
      row.addEventListener('click',()=>inspectJob(job.id));list.append(row);
    });
  }catch(error){list.replaceChildren(el('p','inspector-error',`Unable to load productions: ${error.message}`));}
}
function artifact(label,url){const a=el('a','artifact-link',label+' ↗');a.href=url;a.setAttribute('download','');return a}
async function inspectJob(id){
  const wrapper=$('job-inspector');wrapper.hidden=false;wrapper.scrollIntoView({behavior:'smooth',block:'nearest'});
  $('inspector-title').textContent='Opening production…';
  $('inspector-body').replaceChildren();
  try{
    const job=await API.getJob(id);state.selectedJob=id;
    $('inspector-title').textContent=job.title||'Untitled production';
    const body=$('inspector-body');
    body.append(el('p','inspector-summary',`Status: ${job.status.toUpperCase()}  ·  Director: ${job.provider}  ·  Created ${formatDate(job.created_at)}`));
    if(job.error)body.append(el('p','inspector-error',job.error));
    const actions=el('div','inspector-actions');
    if(job.source_zip)actions.append(artifact('Download engine source',`/api/jobs/${encodeURIComponent(id)}/source`));
    if(job.windows_exe)actions.append(artifact('Download Windows .exe',`/api/jobs/${encodeURIComponent(id)}/windows`));
    if(actions.childNodes.length)body.append(actions);
    if(job.status!=='succeeded'){body.append(el('p','inspector-summary',job.status==='failed'?'This run did not produce final deliverables. Revisit your brief and try again.':'The production is still running. Refresh the archive to see the finished work.'));return;}
    const plan=await API.plan(id);
    body.append(el('div','kicker','STORY ARCHITECTURE'),el('p','inspector-summary',`${plan.genre} · ${plan.setting} · ${plan.characters.length} characters · ${plan.scenes.length} scenes`));
    const grid=el('div','scene-grid');
    plan.scenes.forEach((scene,i)=>{
      const card=el('article','scene-card');
      card.append(el('small','',`SCENE ${String(i+1).padStart(2,'0')} ${scene.id===plan.start_scene?'· OPENING':''}`),el('h3','',scene.title),el('p','',scene.narration),el('div','branches',scene.choices.length?`${scene.choices.length} branching choice${scene.choices.length>1?'s':''}: ${scene.choices.map(c=>c.label).join(' / ')}`:'End of this narrative branch'));
      grid.append(card);
    });body.append(grid);
  }catch(error){$('inspector-body').replaceChildren(el('p','inspector-error',`Unable to inspect story: ${error.message}`));}
}
function setOverlay(active){
  if(active){state.focusReturn=document.activeElement;els.overlay.hidden=false;$('app').inert=true;document.body.style.overflow='hidden';$('overlay-dismiss').focus();}
  else{els.overlay.hidden=true;$('app').inert=false;document.body.style.overflow='';if(state.focusReturn instanceof HTMLElement)state.focusReturn.focus();}
}
function progress(status,text){
  $('overlay-description').textContent=text;
  const statuses=['queued','running','succeeded'];const index=statuses.indexOf(status);
  document.querySelectorAll('.progress-row').forEach((row,i)=>{
    const done=status==='succeeded'?true:status==='failed'?i<2:i<index;
    row.classList.toggle('done',done);
    row.classList.toggle('active',status!=='failed' && status!=='succeeded' && i===index);
    const icon=row.querySelector('i');icon.textContent=done?'✓':status!=='failed'&&i===index?'◌':'—';
  });
}
function overlaySuccess(job){
  document.querySelector('.overlay-heading .kicker').textContent='PRODUCTION COMPLETE';
  $('overlay-heading').closest('.overlay-card').querySelector('h2').textContent='A story takes shape.';
  $('overlay-description').textContent=`${job.title||'Your story'} is ready. Download the actual engine project, or inspect its scene architecture.`;
  progress('succeeded',$('overlay-description').textContent);
  const actions=$('overlay-actions');actions.replaceChildren();
  if(job.source_zip)actions.append(artifact('Download source ZIP',`/api/jobs/${encodeURIComponent(job.id)}/source`));
  if(job.windows_exe)actions.append(artifact('Download .exe',`/api/jobs/${encodeURIComponent(job.id)}/windows`));
  const inspect=el('button','quiet-button','Inspect story ↗');inspect.type='button';inspect.addEventListener('click',async()=>{setOverlay(false);location.hash='#productions';await refreshJobs();await inspectJob(job.id)});actions.append(inspect);
}
function overlayFailure(message){
  document.querySelector('.overlay-heading .kicker').textContent='PRODUCTION INTERRUPTED';
  $('overlay-heading').closest('.overlay-card').querySelector('h2').textContent='Not this time.';
  $('overlay-error').hidden=false;
  $('overlay-error').textContent=message;
  $('overlay-description').textContent='The local build could not complete. No downloadable .exe has been created.';
  progress('failed',$('overlay-description').textContent);
}
async function startProduction(event){
  event.preventDefault();
  if(state.polling)return;
  const prompt=els.prompt.value.trim();
  if(prompt.length<8){notify('Your brief needs at least 8 characters.');els.prompt.focus();return;}
  state.polling=true;els.submit.disabled=true;$('submit-label').textContent='In production…';
  document.querySelector('.overlay-heading .kicker').textContent='PRODUCTION IN PROGRESS';
  $('overlay-heading').closest('.overlay-card').querySelector('h2').replaceChildren(el('span','','Giving your idea '),el('i','','form.'));
  $('overlay-error').hidden=true;
  $('overlay-actions').replaceChildren();
  const view=el('button','quiet-button','Continue in background ↗');view.type='button';view.addEventListener('click',()=>{setOverlay(false);location.hash='#productions'});$('overlay-actions').append(view);
  progress('queued','Preparing a local production job…');setOverlay(true);
  try{
    const created=await API.create({prompt,provider:els.provider.value,export_windows:els.export.checked});
    state.currentJob=created.id;
    progress('running','Building the story contract and generating engine source files.');
    let completed=false;
    for(let i=0;i<300;i++){
      const job=await API.getJob(created.id);
      if(job.status==='succeeded') {completed=true;overlaySuccess(job);notify(`${job.title||'Production'} is ready.`);break;}
      if(job.status==='failed') {completed=true;overlayFailure(job.error||'The build failed.');break;}
      progress(job.status,'Your director is developing the game plan and preparing the engine project.');
      await new Promise(resolve=>setTimeout(resolve,1000));
    }
    if(!completed) overlayFailure('This job exceeded the browser tracking window. Check the Productions archive for its later status.');
    if(currentRoute()==='productions')await refreshJobs();
  }catch(error){overlayFailure(error.message||'The local service could not start a production.');}
  finally{state.polling=false;els.submit.disabled=false;$('submit-label').textContent='Begin production';}
}
function init(){
  els.prompt.addEventListener('input',updateCount);updateCount();
  els.provider.addEventListener('change',displayProviderHint);
  $('presets').addEventListener('click',event=>{
    const button=event.target.closest('[data-preset]');if(!button)return;
    const preset=PRESETS[button.dataset.preset];if(!preset)return;
    els.prompt.value=preset;updateCount();els.prompt.focus();notify('Story spark added. Make it yours.');
  });
  els.form.addEventListener('submit',startProduction);
  window.addEventListener('hashchange',()=>routeTo(currentRoute()));routeTo(currentRoute());
  for(const btn of document.querySelectorAll('[data-go]'))btn.addEventListener('click',()=>{location.hash='#'+btn.dataset.go});
  $('shortcut-button').addEventListener('click',()=>{location.hash='#create';els.prompt.focus()});
  document.addEventListener('keydown',event=>{
    if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();location.hash='#create';els.prompt.focus()}
    if(event.key==='Escape'&&!els.overlay.hidden)setOverlay(false);
  });
  $('overlay-dismiss').addEventListener('click',()=>setOverlay(false));
  $('overlay-view-archive').addEventListener('click',()=>{setOverlay(false);location.hash='#productions'});
  $('close-inspector').addEventListener('click',()=>{$('job-inspector').hidden=true;state.selectedJob=null});
  $('refresh-jobs').addEventListener('click',refreshJobs);
  $('refresh-system').addEventListener('click',refreshCapabilities);
  if (!/Mac|iPhone|iPad/.test(navigator.platform || '')) $('shortcut-button').querySelector('kbd').textContent='Ctrl K';
  displayProviderHint();refreshCapabilities();
}
init();
