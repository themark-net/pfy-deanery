
function show(v){
  view=v;
  document.querySelectorAll('.view').forEach(el=>el.classList.toggle('on', el.id==='view-'+v));
  document.querySelectorAll('.navbtn').forEach(b=>b.classList.toggle('on', b.dataset.go===v));
  paintAttach();
}
document.querySelectorAll('.navbtn').forEach(b=>b.addEventListener('click',()=>show(b.dataset.go)));
function bindAttach(id, hid){
  const el=document.getElementById(id);
  if(el) el.addEventListener('click',()=>attach(hid));
}
bindAttach('btngrok','grok');
bindAttach('btnopen','opencode');
bindAttach('btnhermes','hermes');
bindAttach('btncodex','codex');
bindAttach('btnclaude','claude');
bindAttach('btngab','gab');
bindAttach('att-grok','grok');
bindAttach('att-open','opencode');
bindAttach('att-hermes','hermes');
bindAttach('att-codex','codex');
bindAttach('att-claude','claude');
document.querySelectorAll('[data-mode]').forEach(el=>el.addEventListener('click',()=>selectMode(el.getAttribute('data-mode'))));
document.getElementById('btnrefresh').addEventListener('click',()=>refreshNow());
document.getElementById('btncopy').addEventListener('click',()=>copyStub());
document.getElementById('btnstage').addEventListener('click',()=>runStage());
document.getElementById('btnlaunch').addEventListener('click',()=>runEnv());
document.getElementById('btnlaunchsess')&&document.getElementById('btnlaunchsess').addEventListener('click',()=>runLaunchSession());
document.querySelectorAll('[data-task]').forEach(el=>el.addEventListener('click',()=>runLoopTask(el.getAttribute('data-task'))));
document.querySelectorAll('[data-agent]').forEach(el=>el.addEventListener('click',()=>runLoopAgent(el.getAttribute('data-agent'))));
document.querySelectorAll('[data-lane]').forEach(el=>el.addEventListener('click',()=>runWizard('lane', el.getAttribute('data-lane'))));
document.querySelectorAll('[data-toolset]').forEach(el=>el.addEventListener('click',()=>runWizard('toolsets', el.getAttribute('data-toolset'))));
document.querySelectorAll('[data-harness]').forEach(el=>el.addEventListener('click',()=>runWizard('harness', el.getAttribute('data-harness'))));
document.querySelectorAll('[data-decision]').forEach(el=>el.addEventListener('click',()=>runWizard('decision', el.getAttribute('data-decision'))));
document.getElementById('btncopyendpoint')&&document.getElementById('btncopyendpoint').addEventListener('click',()=>copyLaunchEndpoint());
document.getElementById('btncopyendpoint-eng')&&document.getElementById('btncopyendpoint-eng').addEventListener('click',()=>copyLaunchEndpoint());
document.getElementById('btncopystatus')&&document.getElementById('btncopystatus').addEventListener('click',()=>copyLaunchStatus());
document.getElementById('btnpull').addEventListener('click',()=>runPull());
document.getElementById('btntest').addEventListener('click',()=>runEval());
document.getElementById('btnreco')&&document.getElementById('btnreco').addEventListener('click',()=>runRecommend());
document.getElementById('btntry')&&document.getElementById('btntry').addEventListener('click',()=>runTry());
function paintTools(text, kind){
  const el=document.getElementById('toolsmsg');
  if(!el) return;
  el.textContent=text;
  el.className='attach-result'+(kind?(' '+kind):'');
}
function toolOn(s, id){
  const tools=(s&&s.tools)||{};
  if(id==='mcp') return !!tools.mcp;
  if(id==='write-guard') return !!tools.write_guard;
  if(id==='extra-tools') return (tools.tools_mode||'')==='local_tools';
  return !!((tools.skills||{})[id]);
}
function paintToolRow(s){
  ['one-shot','investigate','agent-loops','hermes-feedback','mcp','write-guard','extra-tools'].forEach(id=>{
    const el=document.getElementById('tool-'+id);
    if(!el) return;
    const on=toolOn(s,id);
    el.textContent=on?'on':'off';
    el.className='live '+(on?'ready':'missing');
  });
}
async function postTool(id, on){
  try{
    if(isTauri()){
      try{
        const v=await window.__TAURI__.core.invoke('set_tool',{id, on});
        return typeof v==='string'?JSON.parse(v):v;
      }catch(e){
        return {ok:false,error:String(e),copy:'FAIL tools',live:'FAIL'};
      }
    }
    if(noLiveApi()) return {ok:false,error:'FAIL',copy:'FAIL tools',live:'FAIL'};
    const r=await fetch(apiRoot()+'/tools',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,on})});
    try{return await r.json();}catch(e){return {ok:false,error:String(e),copy:'FAIL tools',live:'FAIL'};}
  }catch(e){
    return {ok:false,error:String(e),copy:'FAIL tools',live:'FAIL'};
  }
}
async function runTool(id){
  const on=!toolOn(lastSnap,id);
  paintTools('toggling…','');
  try{
    const j=await postTool(id,on);
    if(j && j.ok){
      paintTools(j.copy||('PASS '+id),'ok');
      if(j.tools) lastSnap.tools=j.tools;
      paintToolRow(lastSnap);
    }else{
      paintTools('FAIL '+(j && (j.copy||j.error)||id),'fail');
    }
    await tick();
  }catch(e){
    paintTools('FAIL tools','fail');
  }
}
document.querySelectorAll('[data-tool]').forEach(el=>el.addEventListener('click',()=>runTool(el.getAttribute('data-tool'))));
document.getElementById('btncatask')&&document.getElementById('btncatask').addEventListener('click',()=>runCatalogAsk());
document.getElementById('btncatqueue')&&document.getElementById('btncatqueue').addEventListener('click',()=>runCatalogQueue());
document.getElementById('btncatcopy')&&document.getElementById('btncatcopy').addEventListener('click',()=>copyCatalogPrompt());
function paintCatalogRows(s){
  const list=document.getElementById('cat-list');
  const qel=document.getElementById('cat-queue');
  const att=document.getElementById('cat-attached');
  if(att) att.textContent=s.catalog_attached||s.active||'(none)';
  if(list){
    const rows=s.catalog||[];
    if(!rows.length) list.textContent='(none)';
    else list.innerHTML=rows.slice(0,16).map(r=>'<div class=row><b>'+(r.name||'')+'</b> <span class=muted>'+(r.stage||'-')+'</span> <span class="live '+cls((r.status||'').toLowerCase())+'">'+(r.status||'')+'</span><div class=muted>'+(r.category||'')+' · '+(r.github||'')+'</div><div class=muted>'+(r.notes||'')+'</div></div>').join('')+(rows.length>16?('<div class=muted>… '+(rows.length-16)+' more</div>'):'');
  }
  if(qel){
    const q=s.catalog_queue||[];
    if(!q.length) qel.textContent='(none)';
    else qel.innerHTML=q.map(r=>'<div class=row>'+(r.name||r.id||'')+' · '+(r.kind||'')+' · <span class="live '+cls((r.status||'').toLowerCase())+'">'+(r.status||'')+'</span>'+(r.issue_url?(' <a class=issue href="'+r.issue_url+'">issue</a>'):'')+(r.pr_url?(' <a class=issue href="'+r.pr_url+'">pr</a>'):'')+'</div>').join('');
  }
}
function chipHtml(c){
  const lv=live(c.live);
  return '<div class=chip><b>'+c.id+'</b> <span class="live '+cls(lv)+'">'+lv+'</span><div class=muted>'+c.role+' · '+c.name+'</div></div>';
}
function setLive(id, val){
  const el=document.getElementById(id);
  const lv=live(val);
  el.textContent=lv;
  el.className='live '+cls(lv);
}
async function tick(){
  try{
    const s=await getSnapshot();
    lastSnap=s||{};
    if(s.error && !(s.chips||[]).length){
      document.getElementById('meta').textContent=s.error;
      document.getElementById('fail').textContent='FAIL  '+(s.blocked_copy||GROK_USE);
      attachMsg=attachMsg||('FAIL  '+(s.blocked_copy||GROK_USE));
      attachKind='fail';
      paintAttach();
      return;
    }
    document.getElementById('meta').textContent=[s.host,s.profile,s.ts].filter(Boolean).join(' · ');
    const d=s.detector||{}, r=s.status_runtime||{};
    const engLive=live(s.engine_live||d.status||'missing');
    const g=(s.chips||[]).find(c=>c.id==='grok')||{};
    const stub=!!(s.active_stub || s.active==='continue' || s.active==='agent-cage');
    ['btngrok','btnopen','btnhermes','btncodex','btnclaude','btngab','att-grok','att-open','att-hermes','att-codex','att-claude','att-gab','btnsi'].forEach(id=>{
      const el=document.getElementById(id);
      if(el) el.disabled=stub;
    });
    document.getElementById('fail').textContent=stub?('FAIL  '+(s.blocked_copy||GROK_USE)):(attachKind==='fail'&&attachMsg?attachMsg:'');
    if(stub && attachKind!=='fail'){
      attachMsg='FAIL  '+(s.blocked_copy||GROK_USE);
      attachKind='fail';
    }else if(!attachMsg && stub){
      attachMsg='FAIL  '+(s.blocked_copy||GROK_USE);
      attachKind='fail';
    }
    paintAttach();
    const showOrg=!s.agent_lane_collapsed && (s.org_messages||[]).length;
    document.getElementById('orgnav').style.display=showOrg?'block':'none';
    if(!showOrg && view==='org') show('loop');
    const attached=s.active||'(none)';
    paintUsing(s.using||s.attach_mode||selectedMode||'bare', s.attach_mode_when||'');
    const lev=document.getElementById('loop-evidence');
    if(lev) lev.textContent=s.loop_copy||'(none)';
    const lwhen=document.getElementById('loop-evidence-when');
    if(lwhen) lwhen.textContent=s.loop_when||'';
    const gev=s.graph_copy||'(none)';
    ['loop-graph','att-graph'].forEach(id=>{
      const el=document.getElementById(id);
      if(el) el.textContent=gev;
    });
    const lq=document.getElementById('loop-queue');
    if(lq){
      const qq=s.catalog_queue||[];
      lq.textContent=qq.length?qq.map(r=>((r.name||r.id||'')+' '+(r.status||'')).trim()).join(' · '):'(none)';
    }
    const gwhen=s.graph_when||'';
    ['loop-graph-when','att-graph-when'].forEach(id=>{
      const el=document.getElementById(id);
      if(el) el.textContent=gwhen;
    });
    const verb=lastVerbLabel((s.last_verb&&s.last_verb.verb)||'(none)');
    const when=(s.last_verb&&s.last_verb.when)||'';
    const pid=s.sidecar_pid || '';
    // #171: do not wipe HTML Attach FAIL back to (none) on tick
    if(!(attachKind==='fail' && attachMsg)){
      const attEl=document.getElementById('loop-attached');
      if(attEl) attEl.textContent=attached+(pid?(' pid '+pid):'');
    }
    const reach=(s.session_reach||'').trim()||'(none)';
    if(!(attachKind==='fail' && attachMsg && (!reach || reach==='(none)'))){
      paintSessionReach(reach);
    }
    const lastEl=document.getElementById('loop-last');
    if(lastEl) lastEl.textContent=verb;
    const elv=envLive(s);
    const envEl=document.getElementById('loop-env');
    envEl.textContent=elv;
    envEl.className='live '+cls(elv.toLowerCase());
    const whenEl=document.getElementById('loop-when');
    if(whenEl) whenEl.textContent=when;
    const mon=document.getElementById('loop-monitor');
    if(mon){
      const note=s.monitor_note||'';
      const mpid=s.monitor_pid||'';
      mon.textContent=note||(mpid?('pid '+mpid):'(none)');
    }
    const gpath=s.grok_path||g.live||'missing';
    const gEl=document.getElementById('loop-grok');
    if(gEl) setLive('loop-grok', gpath);
    const u=(s.usage&&typeof s.usage==='object'&&!Array.isArray(s.usage))?s.usage:{};
    const engName=u.engine||d.engine||r.engine||'none';
    document.getElementById('eng-name').textContent=engName;
    const ep=u.endpoint||r.endpoint||r.base_url||d.base_url||'(none)';
    const epEl=document.getElementById('eng-endpoint');
    if(epEl) epEl.textContent=ep||'(none)';
    setLive('eng-live', engLive);
    setLive('eng-grok', g.live);
    const models=(u.models&&u.models.length)?u.models:(s.models||[]);
    document.getElementById('eng-models').textContent=models.length?models.join(' · '):'(none)';
    const tok=u.tok_path||r.tok_path||'SKIP';
    const tokEl=document.getElementById('eng-tok');
    if(tokEl) tokEl.textContent=tok||'SKIP';
    const vram=u.vram||r.vram||'SKIP';
    const vramEl=document.getElementById('eng-vram');
    if(vramEl) vramEl.textContent=vram||'SKIP';
    const reco=(s.recommend&&s.recommend.length)?s.recommend:[];
    const recoEl=document.getElementById('eng-reco');
    if(recoEl) recoEl.textContent=reco.length?reco.slice(0,5).join(' · '):'(none)';
    const pinEl=document.getElementById('eng-pinned');
    if(pinEl) pinEl.textContent=s.pinned_model||'(none)';
    const recoFail=document.getElementById('eng-reco-fail');
    if(recoFail){
      if(s.recommend_ok===false){
        const rc=s.recommend_copy||'FAIL recommend';
        const rn=s.recommend_next||'Launch env or ./pfy up';
        recoFail.style.display='block';
        recoFail.textContent=rc+(rn && String(rc).indexOf(rn)<0?(' · next: '+rn):'');
      }else{
        recoFail.style.display='none';
        recoFail.textContent='';
      }
    }
    const failEl=document.getElementById('eng-usage-fail');
    if(failEl){
      if(u && u.ok===false){
        const fail=u.fail||'FAIL: no local engine up';
        const nxt=u.next_step||'Launch env or ./pfy up';
        failEl.style.display='block';
        failEl.textContent=fail+' · next: '+nxt;
      }else{
        failEl.style.display='none';
        failEl.textContent='';
      }
    }
    paintToolRow(s);
    paintCatalogRows(s);
    paintWizard(s);
    const tape=s.tape||[];
    const stage=tape.find(t=>t.id==='env-stage'||t.label==='env-stage')||{};
    const sl=stage.live||'SKIP';
    const stageEl=document.getElementById('stage-live');
    stageEl.textContent=sl;
    stageEl.className='live '+cls((sl||'').toLowerCase());
    if(!(attachKind==='fail' && attachMsg)){
      document.getElementById('att-now').textContent=attached;
    }
    document.getElementById('att-last').textContent=verb;
    document.getElementById('att-rail').innerHTML=(s.chips||[]).map(chipHtml).join('');
    document.querySelectorAll('[data-start]').forEach(el=>el.addEventListener('click',e=>{e.preventDefault();attach(el.getAttribute('data-start'));}));
    document.querySelectorAll('a.inspect').forEach(el=>el.addEventListener('click',e=>{e.preventDefault(); const t=el.textContent||''; if(t){ copyText(t).then(ok=>paintCopy(ok?'copied':'FAIL clipboard — select the one-liner', ok?'ok':'fail')); } else { paintCopy('FAIL no stub one-liner','fail'); }}));
    if(showOrg){
      const rows=(s.org_messages||[]).map(m=>'<tr><td>'+m.from+' → '+m.to+'</td><td>'+(m.pr||m.issue||'')+'</td><td>'+(m.state||'')+'</td></tr>').join('');
      document.getElementById('org-body').innerHTML='<table>'+rows+'</table>';
    } else {
      document.getElementById('org-body').textContent='no org loop';
    }
  }catch(e){
    document.getElementById('fail').textContent='FAIL  '+GROK_USE;
    attachMsg='FAIL  '+GROK_USE;
    attachKind='fail';
    paintAttach();
  }
}
tick(); setInterval(tick, REFRESH);

document.getElementById('btngabsync')&&document.getElementById('btngabsync').addEventListener('click',async()=>{
  const msg=document.getElementById('recomsg');
  if(msg) msg.textContent='gab sync…';
  try{
    const r=await fetch((window.apiRoot?apiRoot():'')+'/gab/sync',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});
    const j=await r.json();
    const el=document.getElementById('eng-gab-sync');
    const honest=document.getElementById('eng-gab-honest');
    if(el){
      const rows=(j.rows||[]).slice(0,6).map(x=>x.tag+'·'+x.fit+(x.local==='local'?'·local':'')).join(' · ')||'(none)';
      el.textContent=rows;
    }
    if(honest) honest.textContent=(j.honesty||'gab auto ≠ local ranking');
    if(msg) msg.textContent=j.copy||'gab sync';
    if(lastSnap){ lastSnap.gab_sync_rows=j.rows||[]; lastSnap.gab_honesty=j.honesty||''; }
  }catch(e){ if(msg) msg.textContent='FAIL gab sync'; }
});
