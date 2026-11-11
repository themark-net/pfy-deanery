#!/usr/bin/env python3
"""Agent Autoloop trial driver. Runs inside sandlock (see run_trial.sh).

Env: STAGE (writable trial dir), SRC (autoloop checkout at the card pin),
NODE (node 24 binary), LANE_BIN (dir with stub_lane.py and local_lane.py),
PORT (hub port). HOME and AGENT_AUTOLOOP_HOME point inside STAGE.

Steps (each writes a record into $STAGE/results.json):
 1 init with a command agent, rewrite rules.json (stub + local agents,
   group "lanes" parallel 4, worker capacity 4), check
 2 up; emit 6 stub lanes + 1 local-model lane + 1 park lane
 3 wait: the park lane opens a decision card, the rest finish; measure max
   concurrent lanes from conc.log
 4 answer the card (option 1 "approve"); the park lane resumes and finishes
 5 crash: emit park-crash, wait for its card, SIGKILL the hub, start it
   again, check the card survived, answer it, check the lane finishes
 6 runs --json and why --json for the record
"""
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

STAGE = Path(os.environ["STAGE"])
SRC = Path(os.environ["SRC"])
NODE = os.environ["NODE"]
LANE_BIN = Path(os.environ["LANE_BIN"])
PORT = int(os.environ["PORT"])
PHASE = os.environ.get("PHASE", "all")
AL_HOME = STAGE / "al"
LANES = STAGE / "lanes"
HOME = STAGE / "home"
for d in (AL_HOME.parent, LANES, HOME):
    d.mkdir(parents=True, exist_ok=True)
ENV = {
    "HOME": str(HOME),
    "AGENT_AUTOLOOP_HOME": str(AL_HOME),
    "PATH": "%s:/usr/bin:/bin" % Path(NODE).parent,
    "LANG": "C.UTF-8",
    "NO_COLOR": "1",
    "TMPDIR": str(STAGE / "tmp"),
    "STUB_SLEEP": "3",
    "OLLAMA_SOCK": str(STAGE / "ollama.sock"),
}
(STAGE / "tmp").mkdir(exist_ok=True)
RESULTS = {"steps": []}
T0 = time.time()


def rec(step, **kw):
    kw["step"] = step
    kw["t"] = round(time.time() - T0, 2)
    RESULTS["steps"].append(kw)
    (STAGE / "results.json").write_text(json.dumps(RESULTS, indent=1, ensure_ascii=False))
    print(json.dumps(kw, ensure_ascii=False)[:600], flush=True)


def al(*args, check=False, timeout=60):
    cmd = [NODE, "--disable-warning=ExperimentalWarning", str(SRC / "bin" / "agent-autoloop.ts"), *args]
    p = subprocess.run(cmd, env=ENV, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode != 0:
        rec("error", cmd=list(args), rc=p.returncode, out=(p.stdout + p.stderr)[-800:])
        raise SystemExit(1)
    return p


def state():
    p = al("status", "--json")
    try:
        return json.loads(p.stdout)
    except ValueError:
        return {"_raw": (p.stdout + p.stderr)[-500:]}


def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)


def open_cards(st):
    return [c for c in (st.get("cards") or []) if isinstance(c, dict) and c.get("state") == "open"]


def rss_kb(pid):
    try:
        for line in Path("/proc/%d/status" % pid).read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1])
    except OSError:
        return None
    return None


def start_hub(tag):
    log = open(STAGE / ("up-%s.log" % tag), "w")
    proc = subprocess.Popen([NODE, "--disable-warning=ExperimentalWarning", str(SRC / "bin" / "agent-autoloop.ts"), "up"],
                            env=ENV, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(100):
        try:
            socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close()
            return proc
        except OSError:
            time.sleep(0.2)
    rec("error", what="hub did not listen", tag=tag)
    raise SystemExit(1)


def lane_state(slug):
    f = LANES / "lanes" / slug / "state.json"
    return json.loads(f.read_text()) if f.is_file() else None


def wait_for(pred, timeout, every=1.0):
    end = time.time() + timeout
    while time.time() < end:
        v = pred()
        if v:
            return v
        time.sleep(every)
    return None


def max_concurrency():
    events = []
    f = LANES / "conc.log"
    if not f.is_file():
        return 0
    for line in f.read_text().splitlines():
        kind, slug, run, ts = line.split()
        events.append((float(ts), 1 if kind == "start" else -1))
    cur = best = 0
    for _, d in sorted(events, key=lambda e: (e[0], e[1])):
        cur += d
        best = max(best, cur)
    return best


# 0 sandbox probes: the real home and the outside network must be out of reach
real_home = os.environ.get("REAL_HOME", "")
probe = {}
if real_home:
    try:
        os.listdir(real_home)
        probe["real_home_list"] = "ALLOWED"
    except OSError as exc:
        probe["real_home_list"] = "denied errno %d" % exc.errno
try:
    socket.create_connection(("1.1.1.1", 443), timeout=3).close()
    probe["outbound_tcp"] = "ALLOWED"
except OSError as exc:
    probe["outbound_tcp"] = "denied errno %s" % exc.errno
try:
    socket.create_connection(("127.0.0.1", 11434), timeout=2).close()
    probe["host_ollama_tcp"] = "ALLOWED"
except OSError as exc:
    probe["host_ollama_tcp"] = "denied errno %s" % exc.errno
rec("sandbox-probe", **probe)

# 1 init
p = al("init", "--command", "python3 %s {prompt}" % (LANE_BIN / "stub_lane.py"), "--no-service", "--port", str(PORT), check=True)
rec("init", rc=p.returncode)
cfg_file = AL_HOME / "config.json"
cfg = json.loads(cfg_file.read_text())
worker = cfg["worker"]["name"]
cfg["worker"]["capacity"] = 4
cfg.pop("channels", None)  # no desktop notifications in the trial
cfg_file.write_text(json.dumps(cfg, indent=2))
rules = json.loads((AL_HOME / "rules.json").read_text())
rules["channels"] = {}
rules["agents"] = {
    "stub": {"name": "stub lane", "worker": worker, "use": "command",
             "command": ["python3", str(LANE_BIN / "stub_lane.py"), "{prompt}"], "timeout": 5},
    "local": {"name": "local model lane", "worker": worker, "use": "command",
              "command": ["python3", str(LANE_BIN / "local_lane.py"), "{prompt}"], "timeout": 5},
}
rules["rules"] = [
    {"name": "stub-lanes", "when": {"source": "local", "types": ["lane.stub"]}, "to": "stub",
     "cwd": str(LANES), "prompt": "Run the catalog lane named in the event subject.", "group": "lanes", "parallel": 4},
    {"name": "local-lanes", "when": {"source": "local", "types": ["lane.local"]}, "to": "local",
     "cwd": str(LANES), "prompt": "Run the catalog lane named in the event subject.", "group": "lanes", "parallel": 4},
]
(AL_HOME / "rules.json").write_text(json.dumps(rules, indent=2, ensure_ascii=False))
p = al("check")
rec("check", rc=p.returncode, out=(p.stdout + p.stderr)[-400:])
if p.returncode != 0:
    raise SystemExit(1)

# 2 up + emit
hub = start_hub("1")
rec("up", pid_started=True)
stubs = ["fake-a", "fake-b", "fake-c", "fake-d", "fake-e", "fake-f"]
for s in stubs:
    p = al("emit", "lane.stub", "--subject", s, "--summary", "stub catalog lane", "--id", "ev-" + s)
    rec("emit", lane=s, rc=p.returncode, out=(p.stdout + p.stderr).strip()[-200:])
p = al("emit", "lane.local", "--subject", "local-h", "--summary", "local model lane", "--id", "ev-local-h")
rec("emit", lane="local-h", rc=p.returncode, out=(p.stdout + p.stderr).strip()[-200:])
p = al("emit", "lane.stub", "--subject", "park-g", "--summary", "lane that hits a hard stop", "--id", "ev-park-g")
rec("emit", lane="park-g", rc=p.returncode, out=(p.stdout + p.stderr).strip()[-200:])

# 3 wait
t_emit = time.time()
done = wait_for(lambda: all((lane_state(s) or {}).get("state") == "done" for s in stubs + ["local-h"]) and
                (lane_state("park-g") or {}).get("state") == "parked", 180)
st = state()
cards = wait_for(lambda: open_cards(state()), 30) or []
(STAGE / "state-after-park.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
rec("wait-park", all_finished=bool(done), wall_s=round(time.time() - t_emit, 1), max_concurrent=max_concurrency(),
    cards=[{k: c.get(k) for k in ("id", "card", "title", "options", "status")} for c in cards],
    local=lane_state("local-h"))
procs = subprocess.run(["ps", "-eo", "pid,args"], capture_output=True, text=True).stdout
rec("idle-while-parked", stub_processes=sum(1 for l in procs.splitlines() if "stub_lane.py" in l and "ps -eo" not in l),
    hub_rss_kb=rss_kb(hub.pid))

# 4 answer
if cards:
    cid = str(cards[0].get("id", cards[0].get("card")))
    p = al("answer", cid, "1")
    rec("answer", card=cid, rc=p.returncode, out=(p.stdout + p.stderr).strip()[-300:])
    resumed = wait_for(lambda: (lane_state("park-g") or {}).get("state") == "done", 60)
    rec("resumed", ok=bool(resumed), lane=lane_state("park-g"))

# 5 crash
p = al("emit", "lane.stub", "--subject", "park-crash", "--summary", "crash test", "--id", "ev-park-crash")
rec("emit", lane="park-crash", rc=p.returncode)
c2 = wait_for(lambda: [c for c in open_cards(state()) if "park-crash" in json.dumps(c)], 60) or []
os.killpg(hub.pid, signal.SIGKILL)
hub.wait()
rec("sigkill-hub", card_before=bool(c2))
time.sleep(1)
hub = start_hub("2")
c3 = wait_for(lambda: [c for c in open_cards(state()) if "park-crash" in json.dumps(c)], 30) or []
rec("restart", card_survived=bool(c3))
if c3:
    cid = str(c3[0].get("id", c3[0].get("card")))
    p = al("answer", cid, "2")
    rec("answer", card=cid, rc=p.returncode, out=(p.stdout + p.stderr).strip()[-300:])
    resumed = wait_for(lambda: (lane_state("park-crash") or {}).get("state") == "done", 60)
    rec("resumed-after-crash", ok=bool(resumed), lane=lane_state("park-crash"))

# 5b crash while a lane is running: the agent is detached and must finish exactly once
p = al("emit", "lane.stub", "--subject", "slow-crash", "--summary", "kill the hub mid-run", "--id", "ev-slow-crash")
started = wait_for(lambda: "start slow-crash" in ((LANES / "conc.log").read_text() if (LANES / "conc.log").is_file() else ""), 30, 0.2)
os.killpg(hub.pid, signal.SIGKILL)
hub.wait()
rec("sigkill-hub-midrun", lane_started=bool(started))
time.sleep(1)
hub = start_hub("3")
fin = wait_for(lambda: (lane_state("slow-crash") or {}).get("state") == "done", 90)
time.sleep(5)
starts = (LANES / "conc.log").read_text().count("start slow-crash")
rec("midrun-recovery", finished=bool(fin), lane_starts=starts)

# 5c same event id twice: one round
before = (LANES / "conc.log").read_text().count("start fake-a")
p = al("emit", "lane.stub", "--subject", "fake-a", "--summary", "duplicate", "--id", "ev-fake-a")
rec("emit-duplicate", rc=p.returncode, out=(p.stdout + p.stderr).strip()[-200:])
time.sleep(6)
rec("duplicate-dedup", fake_a_starts_before=before, after=(LANES / "conc.log").read_text().count("start fake-a"))

# 5d pause a rule: events wait, resume runs them
p = al("pause", "stub-lanes", "--reason", "trial pause")
rec("pause-rule", rc=p.returncode, out=(p.stdout + p.stderr).strip()[-200:])
p = al("emit", "lane.stub", "--subject", "fake-paused", "--summary", "while paused", "--id", "ev-fake-paused")
rec("emit-while-paused", rc=p.returncode, out=(p.stdout + p.stderr).strip()[-200:])
time.sleep(6)
ran_paused = lane_state("fake-paused") is not None
p = al("resume", "stub-lanes")
after = wait_for(lambda: lane_state("fake-paused"), 20)
rec("resume-rule", ran_while_paused=ran_paused, ran_after_resume=bool(after), rc=p.returncode,
    out=(p.stdout + p.stderr).strip()[-200:])

# 6 record
p = al("runs", "--json")
(STAGE / "runs.json").write_text(p.stdout)
try:
    runs = json.loads(p.stdout)
except ValueError:
    runs = None
rec("runs", rc=p.returncode, count=len((runs or {}).get("runs") or []) if isinstance(runs, dict) else None,
    states=sorted({r.get("state") for r in (runs or {}).get("runs", [])}) if isinstance(runs, dict) else None)
st = state()
(STAGE / "state-final.json").write_text(json.dumps(st, indent=1, ensure_ascii=False))
rec("final", open_cards=len(open_cards(st)), max_concurrent=max_concurrency())
os.killpg(hub.pid, signal.SIGTERM)
try:
    hub.wait(timeout=10)
except subprocess.TimeoutExpired:
    os.killpg(hub.pid, signal.SIGKILL)
rec("stopped")
