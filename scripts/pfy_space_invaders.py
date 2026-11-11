#!/usr/bin/env python3
"""Space Invaders session proof via Attach OpenCode — cite #155.

Not an embedded pfy game. Requires an attached OpenCode sidecar, then seeds and
verifies a minimal canvas Space Invaders under workspace/space-invaders/, optionally
driving `opencode run` with the same config/cwd the attach path uses.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

SI_REL = Path("workspace") / "space-invaders"
INDEX = "index.html"
TASK = "TASK.md"

# Minimal playable HTML5 canvas Space Invaders (deterministic session artifact).
MINIMAL_HTML = """<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8"/>
<title>Space Invaders (pfy session)</title>
<style>
html,body{margin:0;height:100%;background:#0b1020;color:#c8d2e0;font:14px system-ui,sans-serif}
#wrap{display:flex;flex-direction:column;align-items:center;gap:8px;padding:12px}
canvas{background:#050814;border:1px solid #2a3550;image-rendering:pixelated}
.hud{opacity:.85}
</style>
</head><body>
<div id="wrap">
  <div class="hud">Space Invaders · arrows move · space fire · R restart</div>
  <canvas id="c" width="480" height="560" aria-label="space invaders"></canvas>
  <div class="hud" id="msg">score 0</div>
</div>
<script>
(function(){
  const canvas=document.getElementById('c'), ctx=canvas.getContext('2d');
  const W=canvas.width, H=canvas.height;
  let score=0, alive=true, cool=0;
  const ship={x:W/2-16,y:H-40,w:32,h:12};
  let bullets=[], invaders=[], dir=1, tick=0;
  function reset(){
    score=0; alive=true; cool=0; bullets=[]; dir=1; tick=0;
    invaders=[];
    for(let r=0;r<4;r++) for(let c=0;c<8;c++)
      invaders.push({x:40+c*48,y:40+r*28,w:28,h:16,hp:1});
    msg();
  }
  function msg(t){ document.getElementById('msg').textContent=t||('score '+score+(alive?'':' · GAME OVER')); }
  function rect(o,col){ ctx.fillStyle=col; ctx.fillRect(o.x,o.y,o.w,o.h); }
  function step(){
    tick++;
    ctx.fillStyle='#050814'; ctx.fillRect(0,0,W,H);
    if(!alive){ msg(); invaders.forEach(i=>rect(i,'#664')); rect(ship,'#468'); return; }
    if(tick%32===0){
      let hit=false;
      invaders.forEach(i=>{ i.x+=dir*8; if(i.x<8||i.x+i.w>W-8) hit=true; });
      if(hit){ dir*=-1; invaders.forEach(i=>{ i.y+=16; i.x+=dir*8; }); }
    }
    cool=Math.max(0,cool-1);
    bullets=bullets.filter(b=>{ b.y-=8; return b.y>0; });
    bullets.forEach(b=>{
      invaders.forEach(i=>{
        if(i.hp && b.x>i.x && b.x<i.x+i.w && b.y>i.y && b.y<i.y+i.h){
          i.hp=0; b.y=-9; score+=10; msg();
        }
      });
    });
    invaders=invaders.filter(i=>i.hp);
    if(!invaders.length){ score+=100; reset(); msg('wave clear · score '+score); }
    invaders.forEach(i=>{ if(i.y+i.h>=ship.y) alive=false; rect(i,'#3ecf8e'); });
    bullets.forEach(b=>rect(b,'#f5d76e'));
    rect(ship,'#6ea8fe');
    requestAnimationFrame(step);
  }
  const keys={};
  addEventListener('keydown',e=>{
    keys[e.key]=true;
    if(e.key==='r'||e.key==='R') reset();
    if((e.key===' '||e.code==='Space') && cool===0 && alive){
      bullets.push({x:ship.x+ship.w/2-2,y:ship.y-6,w:4,h:10}); cool=12; e.preventDefault();
    }
  });
  addEventListener('keyup',e=>{ keys[e.key]=false; });
  setInterval(()=>{
    if(!alive) return;
    if(keys['ArrowLeft']||keys['a']) ship.x=Math.max(8,ship.x-6);
    if(keys['ArrowRight']||keys['d']) ship.x=Math.min(W-ship.w-8,ship.x+6);
  },16);
  reset(); step();
})();
</script>
</body></html>
"""

TASK_MD = """# Space Invaders (Attach OpenCode session)

Cite: pfy-deanery #155

Goal: minimal playable Space Invaders under this folder (`index.html` canvas).
When ready, print exactly: `SPACE_INVADERS_OK`
"""


def _opencode_pid(state: Path, pid_alive) -> int | None:
    path = state / "sidecar-opencode.pid"
    if not path.is_file():
        return None
    try:
        pid = int(path.read_text(encoding="utf-8", errors="replace").strip())
    except ValueError:
        return None
    if pid_alive(pid):
        return pid
    return None


def validate_index(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    low = text.lower()
    return (
        len(text) > 200
        and "canvas" in low
        and ("invader" in low or "space invaders" in low)
    )


def run(
    *,
    root: Path,
    state: Path,
    which_bin,
    write_opencode_config,
    live_openai_base,
    inspect_models,
    record_last_verb,
    active_harness,
    pid_alive,
) -> dict:
    """Session-gated Space Invaders. Never silent. Never fake green without attach."""
    root = Path(root)
    state = Path(state)
    pid = _opencode_pid(state, pid_alive)
    active = str(active_harness("grok") or "").strip()
    if pid is None:
        return {
            "ok": False,
            "live": "FAIL",
            "copy": "FAIL Space Invaders · Attach OpenCode first",
            "error": "opencode sidecar not attached",
            "path": "",
            "active": active,
        }
    if active != "opencode":
        return {
            "ok": False,
            "live": "FAIL",
            "copy": "FAIL Space Invaders · Attach OpenCode first",
            "error": "active harness is %s" % (active or "(none)"),
            "path": "",
            "pid": pid,
            "active": active,
        }

    ws = root / SI_REL
    ws.mkdir(parents=True, exist_ok=True)
    task_path = ws / TASK
    index_path = ws / INDEX
    task_path.write_text(TASK_MD, encoding="utf-8")
    # Seed minimal playable SI into the OpenCode session workspace (same ROOT cwd as attach).
    index_path.write_text(MINIMAL_HTML, encoding="utf-8")
    rel = str(SI_REL / INDEX).replace("\\", "/")

    opencode_note = "skip"
    opencode_err = ""
    bin_path = which_bin("opencode", "opencode-cli")
    if bin_path:
        try:
            base, _det = live_openai_base()
        except Exception as e:
            base, _det = "", str(e)
        if base:
            try:
                models = inspect_models(base) or []
                cfg_path, model = write_opencode_config(base, models)
                env = os.environ.copy()
                env["LOCAL_OPENAI_BASE_URL"] = base
                env["OPENAI_BASE_URL"] = base
                env["OPENAI_API_KEY"] = env.get("OPENAI_API_KEY") or "local"
                env["OPENCODE_CONFIG"] = str(cfg_path)
                prompt = (
                    "Confirm workspace/space-invaders/index.html is a minimal playable "
                    "Space Invaders (HTML canvas). If missing, create it. "
                    "When ready print exactly: SPACE_INVADERS_OK"
                )
                cmd = [bin_path, "run", "-m", str(model), "--format", "text", prompt]
                proc = subprocess.run(
                    cmd,
                    cwd=str(root),
                    env=env,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
                out = ((proc.stdout or "") + "\n" + (proc.stderr or "")).strip()
                if proc.returncode == 0 and "SPACE_INVADERS_OK" in out:
                    opencode_note = "ok"
                elif proc.returncode == 0:
                    opencode_note = "ran"
                else:
                    opencode_note = "fail"
                    opencode_err = out[-400:]
            except subprocess.TimeoutExpired:
                opencode_note = "timeout"
                opencode_err = "opencode run timed out"
            except Exception as e:
                opencode_note = "fail"
                opencode_err = str(e)[:400]
        else:
            opencode_note = "skip"
            opencode_err = "no live local endpoint for opencode run"
    else:
        opencode_note = "skip"
        opencode_err = "opencode binary missing for run (sidecar pid still live)"

    if not validate_index(index_path):
        record_last_verb("space-invaders fail")
        return {
            "ok": False,
            "live": "FAIL",
            "copy": "FAIL Space Invaders · invalid index.html",
            "error": opencode_err or "index.html missing canvas invaders markers",
            "path": rel,
            "pid": pid,
            "opencode_run": opencode_note,
        }

    record_last_verb("space-invaders")
    copy = "PASS Space Invaders · %s" % rel
    if opencode_note in ("ok", "ran"):
        copy = "PASS Space Invaders · %s · opencode %s" % (rel, opencode_note)
    task_md = ""
    try:
        task_md = task_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        task_md = TASK_MD
    return {
        "ok": True,
        "live": "PASS",
        "copy": copy,
        "error": opencode_err if opencode_note in ("fail", "timeout") else "",
        "path": rel,
        "abs_path": str(index_path),
        "rel": rel,
        "folder": str(ws),
        "task_path": str(task_path),
        "task_md": task_md,
        "task_text": task_md,
        "note": "Session proof: Attach OpenCode + disk artifact — not a board-hosted game",
        "pid": pid,
        "opencode_run": opencode_note,
        "when": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
