#!/bin/bash
# Code-graph fixture smoke on a commit that is already an ancestor of origin/main.
# A second start that finds
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/codebase-memory-mcp.dispatched
# must exit 2 and write no receipt. The lane keeps that marker while it runs
# this script, so a one-argument receipt call is not a second start.
# The main push is one flock fast-forward on
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/push.lock.
# The smoke lock is the fixture directory only. No model call.
# Usage: eval/integrate/codebase-memory-mcp/run-on-main.sh RECEIPT_PATH
# Driver, after this commit is on origin/main:
#   bash eval/integrate/codebase-memory-mcp/run-on-main.sh eval/integrate/codebase-memory-mcp/receipt.json
# A timeout is not a pass. Missing binary, non-ancestor HEAD, or a nonzero
# smoke exits nonzero and does not create that receipt.json.

set -euo pipefail

MARKER=/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/codebase-memory-mcp.dispatched

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  if [ -f "$MARKER" ]; then
    printf '%s\n' "already dispatched: $MARKER" >&2
  fi
  printf '%s\n' "usage: eval/integrate/codebase-memory-mcp/run-on-main.sh RECEIPT_PATH" >&2
  exit 2
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
version=$(timeout 30 "$bin" --version 2>/dev/null | head -n 1 | tr -d '\r')
vrc=$?
set -e
if [ "$vrc" -ne 0 ]; then
  exit "$vrc"
fi
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
  if [ "$rc" -ne 0 ]; then
    exit "$rc"
  fi
}

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_cli cli index_repository --repo-path "$fixture" --name "$project" --mode fast
printf '%s\n' "$cli_out" | grep -q '"status":"indexed"' \
  || printf '%s\n' "$cli_out" | grep -qi 'indexed' \
  || {
    printf '%s\n' "index did not report indexed" >&2
    exit 1
  }
run_cli cli list_projects
printf '%s\n' "$cli_out" | grep -q "$project" || {
  printf '%s\n' "project $project not listed" >&2
  exit 1
}
run_cli cli search_code --pattern greet --project "$project" --limit 5
printf '%s\n' "$cli_out" | grep -Eiq 'greet|app\.py' || {
  printf '%s\n' "search_code did not hit the fixture" >&2
  exit 1
}
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
