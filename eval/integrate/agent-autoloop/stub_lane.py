#!/usr/bin/env python3
"""Stub catalog lane for the Agent Autoloop trial (use: command agent).

Reads the round's context file (AGENT_AUTOLOOP_CONTEXT). The lane slug is the
event subject. Each lane writes only under <cwd>/lanes/<slug>/ (per-lane
state). A "slow-" slug sleeps 12 s (crash test). A slug starting with "park-" asks for a decision on its first round
and finishes on the round that carries the answer. Start and end times go to
<cwd>/conc.log so the trial can measure how many lanes ran at once.
"""
import json
import os
import sys
import time
from pathlib import Path

ctx_path = os.environ.get("AGENT_AUTOLOOP_CONTEXT", "")
ctx = json.loads(Path(ctx_path).read_text()) if ctx_path and Path(ctx_path).is_file() else {}
events = ctx.get("events") or []
slug = str((events[0] if events else {}).get("subject") or "unknown")
answers = ctx.get("answers") or []
run = os.environ.get("AGENT_AUTOLOOP_RUN", "?")
lane = Path.cwd() / "lanes" / slug
lane.mkdir(parents=True, exist_ok=True)
(lane / ("context-run%s.json" % run)).write_text(json.dumps(ctx, indent=1, ensure_ascii=False))
with open(Path.cwd() / "conc.log", "a") as fh:
    fh.write("start %s %s %.3f\n" % (slug, run, time.time()))
time.sleep(12.0 if slug.startswith("slow-") else float(os.environ.get("STUB_SLEEP", "3")))
with open(Path.cwd() / "conc.log", "a") as fh:
    fh.write("end %s %s %.3f\n" % (slug, run, time.time()))

if slug.startswith("park-") and not answers:
    (lane / "state.json").write_text(json.dumps({"slug": slug, "state": "parked", "run": run}))
    print("Lane %s parked on a hard stop." % slug)
    print("```agent-autoloop")
    print(json.dumps({"ask": [{
        "title": "Let lane %s pass a hard stop?" % slug,
        "text": "Stub hard stop: GPU run with no approvals row.",
        "options": ["approve", "park"],
        "recommend": 1,
        "about": "lane %s waits on the GPU approval; approve resumes the run, park keeps it parked" % slug,
        "key": "hs-%s" % slug,
    }]}))
    print("```")
    sys.exit(0)

chosen = [a.get("chosen") for a in answers]
(lane / "state.json").write_text(json.dumps({"slug": slug, "state": "done", "run": run, "answers": chosen}))
print("Lane %s done%s." % (slug, (" after answer %s" % chosen) if chosen else ""))
