
async function runStage(){
  const btn=document.getElementById('btnstage');
  btn.disabled=true;
  paintStage('running env-stage…','');
  document.getElementById('meta').textContent='refreshing…';
  try{
    const j=await postStage();
    if(j && j.ok){
      const c=j.copy||'PASS env-stage';
      paintStage(c, c.indexOf('SKIP')===0?'muted':(c.indexOf('PASS')===0?'ok':''));
    }else{
      paintStage('FAIL '+(j && (j.copy||j.error)||'env-stage'),'fail');
    }
    await tick();
    const ts=(lastSnap&&lastSnap.ts)?lastSnap.ts:'';
    if(ts) document.getElementById('meta').textContent=[lastSnap.host,lastSnap.profile,ts].filter(Boolean).join(' · ');
  }catch(e){
    paintStage('FAIL env-stage','fail');
    document.getElementById('fail').textContent='FAIL  env-stage';
  }finally{
    btn.disabled=false;
  }
}

function paintCatalog(text, kind){
  const el=document.getElementById('catmsg');
  if(!el) return;
  el.textContent=text;
  el.className='attach-result'+(kind?(' '+kind):'');
}
async function postCatalogAsk(name){
  try{
    if(isTauri()){
      try{
        const v=await window.__TAURI__.core.invoke('catalog_ask',{name});
        return typeof v==='string'?JSON.parse(v):v;
      }catch(e){
        return {ok:false,error:String(e),copy:'FAIL ask',live:'FAIL'};
      }
    }
    if(noLiveApi()) return {ok:false,error:'FAIL',copy:'FAIL ask',live:'FAIL',next_step:'Attach grok | opencode | hermes | codex | claude'};
    const r=await fetch(apiRoot()+'/catalog/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name||''})});
    try{return await r.json();}catch(e){return {ok:false,error:String(e),copy:'FAIL ask',live:'FAIL'};}
  }catch(e){
    return {ok:false,error:String(e),copy:'FAIL ask',live:'FAIL'};
  }
}
async function postCatalogQueue(name){
  try{
    if(isTauri()){
      try{
        const v=await window.__TAURI__.core.invoke('catalog_queue',{name});
        return typeof v==='string'?JSON.parse(v):v;
      }catch(e){
        return {ok:false,error:String(e),copy:'FAIL queue',live:'FAIL'};
      }
    }
    if(noLiveApi()) return {ok:false,error:'FAIL',copy:'FAIL queue',live:'FAIL',next_step:'gh issue create --repo themark-net/pfy-deanery'};
    const r=await fetch(apiRoot()+'/catalog/queue',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name:name||''})});
    try{return await r.json();}catch(e){return {ok:false,error:String(e),copy:'FAIL queue',live:'FAIL'};}
  }catch(e){
    return {ok:false,error:String(e),copy:'FAIL queue',live:'FAIL'};
  }
}
async function runCatalogAsk(){
  const name=((document.getElementById('catname')||{}).value||'').trim();
  paintCatalog('asking…','');
  try{
    const j=await postCatalogAsk(name);
    if(j && j.ok){
      if(lastSnap){
        lastSnap.catalog_prompt=j.prompt||lastSnap.catalog_prompt||'';
        if(j.queue) lastSnap.catalog_queue=j.queue;
      }
      paintCatalog(j.copy||'PASS ask','ok');
    }else{
      const nxt=(j && j.next_step)||'Attach grok | opencode | hermes | codex | claude';
      let msg=(j && (j.copy||j.error))||'ask';
      if(String(msg).indexOf(nxt)<0) msg=msg+' · next: '+nxt;
      const skip=String((j&&j.live)||msg).indexOf('SKIP')>=0;
      paintCatalog(skip?msg:(String(msg).indexOf('FAIL')===0?msg:('FAIL '+msg)), skip?'muted':'fail');
    }
    await tick();
  }catch(e){
    paintCatalog('FAIL ask','fail');
  }
}
async function runCatalogQueue(){
  const name=((document.getElementById('catname')||{}).value||'').trim();
  paintCatalog('queueing…','');
  try{
    const j=await postCatalogQueue(name);
    if(j && j.ok){
      if(lastSnap && j.queue) lastSnap.catalog_queue=j.queue;
      paintCatalog(j.copy||'PASS queue','ok');
    }else{
      const nxt=(j && j.next_step)||'gh issue create --repo themark-net/pfy-deanery';
      let msg=(j && (j.copy||j.error))||'queue';
      if(String(msg).indexOf(nxt)<0) msg=msg+' · next: '+nxt;
      const skip=String((j&&j.live)||msg).indexOf('SKIP')>=0;
      paintCatalog(skip?msg:(String(msg).indexOf('FAIL')===0?msg:('FAIL '+msg)), skip?'muted':'fail');
    }
    await tick();
  }catch(e){
    paintCatalog('FAIL queue','fail');
  }
}
async function copyCatalogPrompt(){
  const prompt=(lastSnap&&lastSnap.catalog_prompt)||'';
  if(!prompt){
    paintCatalog('FAIL no prompt — Ask TUI implement first','fail');
    return;
  }
  const ok=await copyText(prompt);
  paintCatalog(ok?'PASS copied':'FAIL clipboard — select the prompt', ok?'ok':'fail');
}
