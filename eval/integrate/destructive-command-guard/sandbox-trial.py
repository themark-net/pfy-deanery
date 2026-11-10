#!/usr/bin/env python3
"""Sandlock trial body for dcg: classify the evq1107 cases through guard.sh.

Usage (run by scripts/integrations/sandlock/trial.py inside sandlock):
  sandbox-trial.py RESULTS.json GUARD.sh DCG_BIN STAGE_DIR
Writes STAGE_DIR/scan.json with verdict CLEAN only when every destructive
case is denied (exit 126), every ordinary case is allowed (exit 0), and no
case used the guard's built-in fallback list. Commands are classified, never run.
"""
import json
import os
import shlex
import subprocess
import sys

results, guard, binary, stage = sys.argv[1:5]
cases = [c for c in json.load(open(results, encoding="utf-8"))["cases"] if c["group"] in ("destructive", "ordinary")]
env = {"PATH": "/usr/bin:/bin", "LANG": "C", "PFY_DCG_BIN": binary,
       "PFY_DCG_CACHE_HOME": os.path.join(stage, "home"), "HOME": os.path.join(stage, "home")}
os.makedirs(env["HOME"], exist_ok=True)
findings = []
counts = {"destructive": [0, 0], "ordinary": [0, 0]}
for case in cases:
    proc = subprocess.run(["bash", guard, *shlex.split(case["command"])], env=env, capture_output=True, text=True, timeout=30)
    want = 126 if case["expect"] == "deny" else 0
    counts[case["group"]][1] += 1
    if proc.returncode == want and "dcg-fallback" not in proc.stderr:
        counts[case["group"]][0] += 1
    else:
        findings.append({"id": case["id"], "exit": proc.returncode, "fallback": "dcg-fallback" in proc.stderr,
                         "stderr": proc.stderr.strip().splitlines()[:1]})
doc = {"verdict": "CLEAN" if not findings else "FINDINGS", "findings": findings,
       "destructive_deny": "%d/%d" % tuple(counts["destructive"]), "ordinary_allow": "%d/%d" % tuple(counts["ordinary"])}
with open(os.path.join(stage, "scan.json"), "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
print(json.dumps(doc))
raise SystemExit(0 if not findings else 1)
