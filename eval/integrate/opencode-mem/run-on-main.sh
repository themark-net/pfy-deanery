#!/bin/bash
# Run the existing offline opencode-mem probe against a temp store.
# Write the receipt only when HEAD is an ancestor of origin/main and the probe exits 0.
# Missing package, probe error, or a timeout writes no receipt.
#
# Extra lock: flock $HOME/DEVELOP/pfy-mentat/tmp/integrate2/push.lock
# The main push is a fast-forward under that flock. This script does not push.
# That push flock is distinct from scripts/model_lock.sh. model_lock.sh wraps
# only the probe, because the embedder is a local ONNX model. Do not pull a model.
#
# The temp HOME is the probe lock. Do not install into ~/.config/opencode
# or any real harness home.
#
# The lane marker is $OCM_LANE_MARKER, or
# $HOME/DEVELOP/pfy-mentat/tmp/integrate2/opencode-mem.dispatched.
# A second start exits 2 and writes no receipt. The driver writes "pid <lane-pid>"
# and still holds that file when it runs this script, so a marker whose pid is an
# ancestor of this process is the admitted lane and the probe continues.
# This script does not create or remove the marker.
#
# run_kind is pipeline. Write nothing unless HEAD is an ancestor of origin/main.
#
# Usage: eval/integrate/opencode-mem/run-on-main.sh RECEIPT.json

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/opencode-mem/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

receipt=$1
case "$receipt" in
  /*) ;;
  *) receipt=$PWD/$receipt ;;
esac

marker=${OCM_LANE_MARKER:-$HOME/DEVELOP/pfy-mentat/tmp/integrate2/opencode-mem.dispatched}

marker_pid_is_ancestor() {
  local file=$1
  local target cur guard ppid
  target=$(sed -n 's/^pid \([0-9][0-9]*\)[[:space:]]*$/\1/p' "$file" 2>/dev/null | head -n 1 || true)
  if [ -z "$target" ]; then
    return 1
  fi
  cur=$$
  guard=0
  while (( cur > 1 && guard < 40 )); do
    if [ "$cur" = "$target" ]; then
      return 0
    fi
    if [ ! -r "/proc/$cur/status" ]; then
      return 1
    fi
    ppid=$(awk '/^PPid:/ {print $2}' "/proc/$cur/status" 2>/dev/null || true)
    if [ -z "$ppid" ] || [ "$ppid" = "$cur" ]; then
      return 1
    fi
    cur=$ppid
    guard=$((guard + 1))
  done
  return 1
}

if [ -e "$marker" ]; then
  if ! marker_pid_is_ancestor "$marker"; then
    printf '%s\n' "already dispatched: $marker" >&2
    exit 2
  fi
fi

root=$(git rev-parse --show-toplevel)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
  printf '%s\n' "origin/main is missing" >&2
  exit 1
fi

main_sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$main_sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main" >&2
  exit 1
fi
# grep -q under pipefail can die with SIGPIPE on a match. Do not use it here.
if [[ ! "$main_sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf '%s\n' "main_sha is not 40 hex characters" >&2
  exit 1
fi

probe=$root/eval/evq1107/opencode-mem/probe.py
if [ ! -f "$probe" ]; then
  printf '%s\n' "offline probe missing" >&2
  exit 1
fi
if [ ! -x /usr/bin/node ]; then
  printf '%s\n' "node missing" >&2
  exit 1
fi
if ! command -v rg >/dev/null 2>&1; then
  printf '%s\n' "rg missing" >&2
  exit 1
fi

real_home=$(python3 -c 'import os, pwd; print(pwd.getpwuid(os.getuid()).pw_dir)')
pkg_json=$real_home/.cache/pfy/tools/opencode-mem/prefix/node_modules/opencode-mem/package.json
onnx=$real_home/.cache/pfy/tools/opencode-mem/home/.opencode-mem/data/.cache
if [ ! -f "$pkg_json" ] || [ ! -d "$onnx" ]; then
  printf '%s\n' "opencode-mem package or embedder cache missing" >&2
  exit 1
fi

tool_version=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1], encoding="utf-8")).get("version") or "opencode-mem")' "$pkg_json")
if [ -z "$tool_version" ]; then
  printf '%s\n' "tool version missing" >&2
  exit 1
fi

# Take the model lock on the real cache path before HOME moves.
if [ -z "${PFY_MODEL_LOCK:-}" ]; then
  export PFY_MODEL_LOCK=$real_home/.cache/pfy/locks/local-model.lock
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/opencode-mem-probe.XXXXXX")
home=$work/home
tmp=
cleanup() {
  if [ -n "${work:-}" ]; then
    rm -rf "$work"
  fi
  if [ -n "${tmp:-}" ]; then
    rm -f "$tmp"
  fi
}
trap cleanup EXIT
mkdir -p "$home" "$work/tmp" "$work/store"

# The temp HOME is the lock for this probe.
exec 8<"$home"
if ! flock -n 8; then
  printf '%s\n' "temp HOME lock held" >&2
  exit 2
fi

export HOME=$home
export XDG_CONFIG_HOME=$home/.config
export XDG_CACHE_HOME=$home/.cache
export XDG_DATA_HOME=$home/.local/share
export TMPDIR=$work/tmp

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
timeout 180s "$root/scripts/model_lock.sh" \
  python3 "$probe" \
  --home "$home" \
  --tmp "$work/tmp" \
  --storage "$work/store" \
  --out "$work/results.json" \
  --node /usr/bin/node
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "probe exit $rc" >&2
  exit "$rc"
fi
if [ ! -f "$work/results.json" ]; then
  printf '%s\n' "probe wrote no results" >&2
  exit 1
fi

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_id="opencode-mem-${main_sha:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p -- "$(dirname -- "$receipt")"
tmp=$(mktemp "$(dirname -- "$receipt")/.receipt.XXXXXX")
python3 - "$work/results.json" "$tmp" "$main_sha" "$started" "$finished" "$tool_version" "$run_id" <<'PY'
import json
import sys
from pathlib import Path

results, dest, sha, started, finished, version, run_id = sys.argv[1:]
doc = json.loads(Path(results).read_text(encoding="utf-8"))
hits = doc.get("recall_search_hits")
listed = doc.get("recall_list_hits")
changed = doc.get("real_home_changed")
if doc.get("store_ok") is not True or doc.get("recall_ok") is not True:
    raise SystemExit(1)
if hits != 8 or listed != 8:
    raise SystemExit(1)
if not isinstance(changed, list) or changed:
    raise SystemExit(1)
did = "Ran the offline probe in a temp HOME and searched %s of 8 stored salts." % hits
out = {
    "slug": "opencode-mem",
    "run_kind": "pipeline",
    "main_sha": sha,
    "run_id": run_id,
    "started": started,
    "finished": finished,
    "outcome": "ok",
    "tool_version": version,
    "did": did,
}
Path(dest).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
PY
mv "$tmp" "$receipt"
tmp=
printf '%s\n' "$receipt"
