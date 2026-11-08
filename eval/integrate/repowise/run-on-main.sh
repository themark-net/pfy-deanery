#!/bin/bash
# Context-packing smoke receipt. Operator path: make smoke-repowise.
# Pip pin and health, zero LLM. No model call.
#
# Usage:
#   bash eval/integrate/repowise/run-on-main.sh eval/integrate/repowise/receipt.json
#
# A second start that finds
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/repowise.dispatched
# exits 2 and writes no receipt, unless that marker's pid is an ancestor of
# this process. The driver writes "pid <lane-pid>" and still holds the marker
# when it runs this one-argument receipt call, so that admitted lane continues.
# This script does not create or remove the marker.
#
# The main push is a fast-forward under one flock. The extra lock is
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/push.lock
# This script does not take that flock and does not add a lock.
# The smoke temp dir is the only in-script lock.
#
# Write receipt.json only when HEAD is an ancestor of origin/main and
# make smoke-repowise exits 0. Any other path exits nonzero and writes nothing.
# A timeout is not a pass. A worktree-only diff is not the receipt.
# Callers that do not run this script keep today's behavior.

set -euo pipefail

MARKER=${PFY_REPOWISE_LANE_MARKER:-/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/repowise.dispatched}

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/repowise/run-on-main.sh eval/integrate/repowise/receipt.json" >&2
  exit 2
fi

receipt=$1
if [ "${receipt#/}" = "$receipt" ]; then
  receipt=$PWD/$receipt
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

root=$(git rev-parse --show-toplevel)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
  printf '%s\n' "origin/main is missing; no receipt" >&2
  exit 1
fi

sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main; no receipt" >&2
  exit 1
fi
if ! printf '%s\n' "$sha" | grep -E -q '^[0-9a-f]{40}$'; then
  printf '%s\n' "main_sha is not 40 hex characters; no receipt" >&2
  exit 1
fi

if ! command -v timeout >/dev/null 2>&1; then
  printf '%s\n' "timeout is missing; no receipt" >&2
  exit 1
fi
if ! command -v make >/dev/null 2>&1; then
  printf '%s\n' "make is missing; no receipt" >&2
  exit 1
fi

# Smoke temp dir is the lock for this run. Do not take the fast-forward flock.
smoke_tmp=$(mktemp -d "${TMPDIR:-/tmp}/repowise-smoke.XXXXXX")
receipt_tmp=
cleanup() {
  if [ -n "${smoke_tmp:-}" ]; then
    rm -rf "$smoke_tmp"
  fi
  if [ -n "${receipt_tmp:-}" ]; then
    rm -f "$receipt_tmp"
  fi
}
trap cleanup EXIT

tool_version=repowise==0.30.0
pins=$root/examples/repowise/pins.env
if [ -f "$pins" ]; then
  pin=$(sed -n 's/^REPOWISE_PIP_SPEC=//p' "$pins" | head -n 1 | tr -d '\r')
  if [ -n "$pin" ]; then
    tool_version=$pin
  fi
fi

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
TMPDIR=$smoke_tmp timeout 600 make smoke-repowise
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  if [ "$rc" -eq 124 ]; then
    printf '%s\n' "smoke-repowise timeout; no receipt" >&2
  else
    printf '%s\n' "smoke-repowise failed: $rc; no receipt" >&2
  fi
  exit "$rc"
fi
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)

dest_dir=$(dirname -- "$receipt")
mkdir -p -- "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
python3 - "$receipt_tmp" "$sha" "$started" "$finished" "$tool_version" <<'PY'
import json
import sys

path, sha, started, finished, version = sys.argv[1:]
doc = {
    "slug": "repowise",
    "run_kind": "pipeline",
    "main_sha": sha,
    "run_id": "repowise-" + sha[:12] + "-" + started.replace(":", "").replace("-", ""),
    "started": started,
    "finished": finished,
    "outcome": "ok",
    "tool_version": version,
    "did": "Ran make smoke-repowise (pip pin and zero-LLM health). The smoke exited 0.",
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
PY
mv -f "$receipt_tmp" "$receipt"
receipt_tmp=
printf '%s\n' "$receipt"
