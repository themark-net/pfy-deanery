#!/bin/bash
# Code-graph fixture smoke. HEAD must be an ancestor of origin/main.
# The receipt is written only after that check and the fixture smoke exit 0.
#
# A second start that finds
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/codebase-memory-mcp.dispatched
# exits 2 and writes no receipt, unless that marker's pid is an ancestor of
# this process. The driver writes "pid <lane-pid>" and still holds the marker
# when it runs the one-argument receipt call, so that admitted lane continues.
# This script does not create or remove the marker.
#
# The main push is one flock fast-forward on
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/push.lock.
# This script does not take that lock. The smoke lock is the fixture
# directory only (flock). No model call.
#
# Usage: eval/integrate/codebase-memory-mcp/run-on-main.sh RECEIPT_PATH
# Driver, after this commit is on origin/main:
#   bash eval/integrate/codebase-memory-mcp/run-on-main.sh eval/integrate/codebase-memory-mcp/receipt.json
# A timeout is not a pass. Missing binary, non-ancestor HEAD, or a nonzero
# smoke exits nonzero and does not create the receipt.

set -euo pipefail

MARKER=${PFY_CBM_LANE_MARKER:-/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/codebase-memory-mcp.dispatched}

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/codebase-memory-mcp/run-on-main.sh RECEIPT_PATH" >&2
  exit 2
fi

marker_pid_is_ancestor() {
  local file=$1
  local target cur guard ppid
  # Unreadable or pid-less marker is not an admitted lane.
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

fixture=$root/examples/codebase-memory-mcp/fixture
if [ ! -d "$fixture" ]; then
  printf '%s\n' "fixture missing: $fixture" >&2
  exit 1
fi

if [ -n "${PFY_CODEBASE_MEMORY+x}" ]; then
  bin=$PFY_CODEBASE_MEMORY
else
  bin=
  if command -v codebase-memory-mcp >/dev/null 2>&1; then
    bin=$(command -v codebase-memory-mcp)
  elif [ -x "${HOME}/.local/bin/codebase-memory-mcp" ]; then
    bin=${HOME}/.local/bin/codebase-memory-mcp
  else
    bin=${PFY_TOOL_CACHE:-${HOME}/.cache/pfy}/bin/codebase-memory-mcp
  fi
fi
if [ -z "$bin" ] || [ ! -x "$bin" ]; then
  printf '%s\n' "codebase-memory-mcp binary missing" >&2
  exit 1
fi

# One smoke at a time. The fixture directory is the lock.
exec 7<"$fixture"
if ! flock -n 7; then
  printf '%s\n' "fixture directory lock held" >&2
  exit 2
fi

cache=$(mktemp -d "${TMPDIR:-/tmp}/cbm-integrate.XXXXXX")
mkdir -p "$cache/db"
receipt_tmp=
cleanup() {
  if [ -n "${cache:-}" ]; then
    rm -rf "$cache"
  fi
  if [ -n "${receipt_tmp:-}" ]; then
    rm -f "$receipt_tmp"
  fi
}
trap cleanup EXIT

export CBM_CACHE_DIR=$cache/db
export CBM_MEM_BUDGET_MB=${CBM_MEM_BUDGET_MB:-8192}
export CBM_WORKERS=${CBM_WORKERS:-2}
export CBM_LOG_LEVEL=${CBM_LOG_LEVEL:-error}
project=pfy-mentat-cm-smoke

set +e
version=$(timeout 30 "$bin" --version 2>/dev/null)
vrc=$?
set -e
if [ "$vrc" -ne 0 ]; then
  if [ "$vrc" -eq 124 ]; then
    printf '%s\n' "version timeout" >&2
  fi
  exit "$vrc"
fi
version=${version%%$'\n'*}
version=${version//$'\r'/}
if [ -z "$version" ]; then
  version=codebase-memory-mcp
fi

cli_out=
run_cli() {
  local rc
  set +e
  cli_out=$(timeout 120 "$bin" "$@" 2>&1)
  rc=$?
  set -e
  printf '%s\n' "$cli_out" >&2
  if [ "$rc" -eq 124 ]; then
    printf '%s\n' "smoke timeout" >&2
    exit 124
  fi
  if [ "$rc" -ne 0 ]; then
    exit "$rc"
  fi
}

out_has() {
  grep -q "$1" <<<"$cli_out"
}

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_cli cli index_repository --repo-path "$fixture" --name "$project" --mode fast
if ! out_has '"status":"indexed"' && ! grep -qi 'indexed' <<<"$cli_out"; then
  printf '%s\n' "index did not report indexed" >&2
  exit 1
fi
run_cli cli list_projects
if ! out_has "$project"; then
  printf '%s\n' "project $project not listed" >&2
  exit 1
fi
run_cli cli search_code --pattern greet --project "$project" --limit 5
if ! grep -Eiq 'greet|app\.py' <<<"$cli_out"; then
  printf '%s\n' "search_code did not hit the fixture" >&2
  exit 1
fi
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Write receipt.json only after the smoke exits 0.
dest_dir=$(dirname -- "$receipt")
mkdir -p "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_TMP=$receipt_tmp
export RECEIPT_SHA=$sha
export RECEIPT_RUN_ID="codebase-memory-mcp-${sha:0:12}-${started}"
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$version
export RECEIPT_DID="Indexed examples/codebase-memory-mcp/fixture as ${project} and search_code found greet. Smoke exited 0."
python3 - <<'PY'
import json
import os
from pathlib import Path

doc = {
    "slug": "codebase-memory-mcp",
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
