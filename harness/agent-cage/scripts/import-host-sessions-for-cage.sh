#!/usr/bin/env bash
# Copy host Grok sessions for this catalog repo into the cage session store
# under the cage cwd key (/workspace/pfy-mentat), rewriting summary paths.
#
# Why: Grok keys sessions by absolute cwd. Host uses
#   /home/.../local-llm-dev-tools  →  %2Fhome%2F...
# Cage uses
#   /workspace/pfy-mentat          →  %2Fworkspace%2Fpfy-mentat
# Without this mapping, host "old" sessions never show in the cage.
set -euo pipefail

# HOST_CWD is the host catalog checkout. No private default path.
: "${HOST_CWD:?set HOST_CWD to the host catalog checkout}"

AGENTCAGE_DIR="${AGENTCAGE_DIR:-$HOME/.agentcage}"
CAGE_CWD="${CAGE_CWD:-/workspace/pfy-mentat}"
GROK_HOME_HOST="${GROK_HOME_HOST:-$HOME/.grok}"
STATE_SESSIONS="${AGENTCAGE_DIR}/grok-state/sessions"

python3 - "$HOST_CWD" "$CAGE_CWD" "$GROK_HOME_HOST" "$STATE_SESSIONS" <<'PY'
import json, os, shutil, sys, urllib.parse
from pathlib import Path

host_cwd, cage_cwd, grok_home, state_sessions = sys.argv[1:5]
host_key = urllib.parse.quote(host_cwd, safe="")
cage_key = urllib.parse.quote(cage_cwd, safe="")
src_root = Path(grok_home) / "sessions" / host_key
dst_root = Path(state_sessions) / cage_key
try:
    dst_root.mkdir(parents=True, exist_ok=True)
except PermissionError as e:
    print(
        f"import-host-sessions: cannot mkdir {dst_root}: {e}\n"
        f"  Fix: make -C harness/agent-cage fix-grok-state-perms\n"
        f"  Cause: sessions tree owned by cage agent (uid 1001) after docker chown/cp.",
        file=sys.stderr,
    )
    sys.exit(1)

if not src_root.is_dir():
    print(f"import-host-sessions: no host sessions at {src_root}", file=sys.stderr)
    sys.exit(0)

imported = 0
for child in sorted(src_root.iterdir()):
    if not child.is_dir():
        continue
    # skip locks-only junk
    if not (child / "summary.json").is_file() and not (child / "updates.jsonl").is_file():
        continue
    dest = dst_root / child.name
    if dest.exists():
        # merge: prefer newer updated_at
        try:
            src_sum = json.loads((child / "summary.json").read_text())
            dst_sum = json.loads((dest / "summary.json").read_text()) if (dest / "summary.json").is_file() else {}
            if src_sum.get("updated_at", "") <= dst_sum.get("updated_at", ""):
                print(f"  skip {child.name} (cage copy same/newer)")
                continue
        except Exception:
            pass
        shutil.rmtree(dest)
    shutil.copytree(child, dest)
    # rewrite identity paths so resume treats this as cage cwd
    summary_path = dest / "summary.json"
    if summary_path.is_file():
        try:
            data = json.loads(summary_path.read_text())
            info = data.setdefault("info", {})
            info["id"] = info.get("id") or child.name
            info["cwd"] = cage_cwd
            data["git_root_dir"] = cage_cwd.rstrip("/") + "/"
            data["grok_home"] = "/home/agent/.grok"
            summary_path.write_text(json.dumps(data, indent=2) + "\n")
        except Exception as e:
            print(f"  warn: summary rewrite {child.name}: {e}", file=sys.stderr)
    # drop locks
    for lock in dest.glob("*.lock"):
        lock.unlink(missing_ok=True)
    imported += 1
    print(f"  imported {child.name} → {dest}")

# copy host session_search is not portable; Grok rebuilds index on list
print(f"import-host-sessions: imported {imported} session(s) into {dst_root}")
PY
