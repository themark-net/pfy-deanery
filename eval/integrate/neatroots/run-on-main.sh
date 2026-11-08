#!/bin/bash
# Offline neatroots check on one saved trace. No network and no shared service.
#
# Usage:
#   bash eval/integrate/neatroots/run-on-main.sh eval/integrate/neatroots/receipt.json
#
# Exit nonzero and write no receipt when HEAD is not an ancestor of origin/main.
# A worktree-only diff is not the receipt.
#
# A second start that finds
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/neatroots.dispatched
# exits 2 and writes no receipt, unless that marker's pid is an ancestor of
# this process. The driver writes "pid <lane-pid>" and still holds the marker
# when it runs this one-argument receipt call, so that admitted lane continues.
# This script does not create or remove the marker.
#
# The main push is one flock fast-forward. The extra lock is
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/neatroots.push.lock.
# This script does not take that lock. The check lock is the fixture file
# only (flock).
#
# Missing binary, exit 2, and a 60 second timeout write no receipt.
# A timeout is not a pass.
# Callers that do not run this script stay as they are.

set -euo pipefail

MARKER=${PFY_NEATROOTS_LANE_MARKER:-/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/neatroots.dispatched}

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/neatroots/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

marker_pid_is_ancestor() {
  local file=$1
  local target cur guard ppid
  target=$(sed -n 's/^pid \([0-9][0-9]*\)[[:space:]]*$/\1/p' "$file" 2>/dev/null || true)
  target=${target%%$'\n'*}
  if [ -z "$target" ]; then
    return 1
  fi
  cur=$$
  guard=0
  while [ "$cur" -gt 1 ] && [ "$guard" -lt 40 ]; do
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

if [ -f "$MARKER" ]; then
  if ! marker_pid_is_ancestor "$MARKER"; then
    printf '%s\n' "already dispatched: $MARKER" >&2
    exit 2
  fi
fi

receipt=$1
root=$(git rev-parse --show-toplevel)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
  printf '%s\n' "origin/main is missing" >&2
  exit 1
fi
sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main" >&2
  exit 1
fi
if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf '%s\n' "main_sha is not 40 hex characters" >&2
  exit 1
fi

rel=eval/integrate/neatroots/fixtures/trace.json
trace=$root/$rel
if [ ! -f "$trace" ]; then
  printf '%s\n' "fixture missing: $rel" >&2
  exit 2
fi

if [ -n "${NEATROOTS_NODE+x}" ]; then
  node=$NEATROOTS_NODE
else
  node=${HOME}/.cache/pfy/tools/neatroots/node/bin/node
  if [ ! -x "$node" ]; then
    node=$(command -v node || true)
  fi
fi
if [ -n "${NEATROOTS_APP+x}" ]; then
  cli=${NEATROOTS_APP}/neatroots/dist/cli.js
else
  cli=${HOME}/.cache/pfy/tools/neatroots/app/neatroots/dist/cli.js
fi
if [ -z "${node:-}" ] || [ ! -x "$node" ] || [ ! -f "$cli" ]; then
  printf '%s\n' "neatroots binary missing" >&2
  exit 2
fi

exec 7<"$trace"
if ! flock -n 7; then
  printf '%s\n' "fixture lock held" >&2
  exit 2
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/neatroots-integrate.XXXXXX")
receipt_tmp=
cleanup() {
  if [ -n "${receipt_tmp:-}" ]; then
    rm -f "$receipt_tmp"
  fi
  if [ -n "${work:-}" ]; then
    rm -rf "$work"
  fi
}
trap cleanup EXIT
mkdir -p "$work/home" "$work/tmp" "$work/xdg/config" "$work/xdg/cache"

run_neatroots() {
  # stdout, stderr, then the command words. timeout 60. 124 is not a pass.
  local out=$1
  local err=$2
  shift 2
  local rc
  set +e
  timeout 60 env -u FORCE_COLOR NO_COLOR=1 \
    HOME="$work/home" \
    TMPDIR="$work/tmp" \
    XDG_CONFIG_HOME="$work/xdg/config" \
    XDG_CACHE_HOME="$work/xdg/cache" \
    "$node" "$cli" "$@" >"$out" 2>"$err"
  rc=$?
  set -e
  if [ "$rc" -eq 124 ]; then
    printf '%s\n' "timeout is not a pass" >&2
    exit 124
  fi
  if [ "$rc" -eq 2 ]; then
    printf '%s\n' "neatroots exit 2" >&2
    exit 2
  fi
  if [ "$rc" -ne 0 ]; then
    printf '%s\n' "neatroots exit $rc" >&2
    exit "$rc"
  fi
}

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_neatroots "$work/version.txt" "$work/version.err" --version
version=$(tail -n 1 "$work/version.txt" | tr -d '\r')
if [ -z "$version" ]; then
  version=neatroots
fi

run_neatroots "$work/check.json" "$work/check.err" check "$trace" --json
python3 - "$work/check.json" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
if not isinstance(data, dict):
    raise SystemExit("check json is not an object")
errors = data.get("errors")
if errors:
    raise SystemExit("check json reported errors")
PY
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)

dest_dir=$(dirname -- "$receipt")
mkdir -p "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_TMP=$receipt_tmp
export RECEIPT_SHA=$sha
export RECEIPT_RUN_ID="neatroots-${sha:0:12}-${started}"
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$version
export RECEIPT_DID="Ran neatroots check on eval/integrate/neatroots/fixtures/trace.json offline. Exit 0."
python3 - <<'PY'
import json
import os
from pathlib import Path

doc = {
    "slug": "neatroots",
    "run_kind": "pipeline",
    "main_sha": os.environ["RECEIPT_SHA"],
    "run_id": os.environ["RECEIPT_RUN_ID"],
    "started": os.environ["RECEIPT_STARTED"],
    "finished": os.environ["RECEIPT_FINISHED"],
    "outcome": "ok",
    "tool_version": os.environ["RECEIPT_VERSION"],
    "did": os.environ["RECEIPT_DID"],
}
Path(os.environ["RECEIPT_TMP"]).write_text(
    json.dumps(doc, indent=2) + "\n",
    encoding="utf-8",
)
PY
mv -f "$receipt_tmp" "$receipt"
receipt_tmp=
printf '%s\n' "$receipt"
