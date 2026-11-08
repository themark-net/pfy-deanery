#!/bin/bash
# One atg-compile receipt on a commit that is already on origin/main.
#
# Usage: eval/integrate/atomic-task-graph-atg/run-on-main.sh RECEIPT.json
#
# Lane marker: /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/atomic-task-graph-atg.dispatched
# A second start exits 2 when ATG_LANE_MARKER names that file and it exists.
# This script does not create or write the owner-checkout marker.
# The main fast-forward lands under one flock in the driver.
# Extra lock: a receipt-path flock on "<receipt>.lock" so two checkouts
# do not share a receipt write. scripts/model_lock.sh is only the model lock.
#
# Prefer the wired offline check in tests/test_atg_compile_bench.py.
# Call the model only when that check is unavailable and the model is
# already loaded. The model command is examples/atg-compile/bench.py
# under scripts/model_lock.sh. A caller-supplied shell command is not
# accepted. No download. No ollama pull. A timeout is not a pass.
# Missing checkout, missing model, error, or timeout: exit nonzero and
# write no receipt.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/atomic-task-graph-atg/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

receipt=$1
# Resolve before cd. A relative path is the caller's path, not the repo root.
case "$receipt" in
  /*) ;;
  *) receipt=$PWD/$receipt ;;
esac

# Injected lane marker. Absent means this receipt run is the lane already
# in progress, not a second start. Do not create the owner path.
if [ -n "${ATG_LANE_MARKER:-}" ] && [ -e "$ATG_LANE_MARKER" ]; then
  printf '%s\n' "lane marker present" >&2
  exit 2
fi

if [ "${ATG_FORCE_NOT_ANCESTOR:-}" = "1" ]; then
  printf '%s\n' "HEAD is not an ancestor of origin/main" >&2
  exit 1
fi

root=$(git rev-parse --show-toplevel)
cd "$root"

if [ "${ATG_SKIP_MAIN_ANCESTOR:-}" != "1" ]; then
  if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
    printf '%s\n' "origin/main is not available" >&2
    exit 1
  fi
  head=$(git rev-parse HEAD)
  if ! git merge-base --is-ancestor "$head" origin/main; then
    printf '%s\n' "HEAD is not an ancestor of origin/main" >&2
    exit 1
  fi
else
  head=$(git rev-parse HEAD)
fi

if ! printf '%s\n' "$head" | grep -E -q '^[0-9a-fA-F]{40}$'; then
  printf '%s\n' "HEAD is not 40 hex chars" >&2
  exit 1
fi

tool_version=543e778ed24fbf3fc903eb961feb627039019832
mode=model
offline_cmd=()
did=""

if [ -n "${ATG_OFFLINE_CHECK+x}" ]; then
  if [ -n "$ATG_OFFLINE_CHECK" ]; then
    if [ ! -x "$ATG_OFFLINE_CHECK" ]; then
      printf '%s\n' "offline check is not executable" >&2
      exit 1
    fi
    mode=offline
    offline_cmd=("$ATG_OFFLINE_CHECK")
    did="Ran the wired offline atg-compile check. No model call."
  fi
else
  wired=$root/tests/test_atg_compile_bench.py
  if [ -f "$wired" ]; then
    mode=offline
    offline_cmd=(
      python3 -m unittest
      tests.test_atg_compile_bench.AtgCompileBenchTests.test_case_set_has_ten_distinct_tasks
      tests.test_atg_compile_bench.AtgCompileBenchTests.test_unset_atg_repo_exits_2_with_next_step
      tests.test_atg_compile_bench.AtgCompileBenchTests.test_no_default_tmp_worktree_literal_in_tests_data_or_bench
    )
    did="Ran the wired offline atg-compile check in tests/test_atg_compile_bench.py. No model call."
  fi
fi

model_name=${ATG_MODEL:-qwen3.6:35b}
base_url=${ATG_BASE_URL:-http://127.0.0.1:11434}
base_url=${base_url%/}
model_cmd=()
bench_out=

if [ "$mode" = "model" ]; then
  loaded=0
  if [ "${ATG_MODEL_LOADED:-}" = "1" ]; then
    loaded=1
  elif [ "${ATG_MODEL_LOADED:-}" = "0" ]; then
    loaded=0
  elif [ "$base_url" = "http://127.0.0.1:11434" ] \
    && command -v ollama >/dev/null 2>&1 \
    && command -v ss >/dev/null 2>&1; then
    # Query only when the port is already listening. A connect can
    # socket-activate the daemon. Do not pull, run, stop, or restart.
    if ss -ltnH 'sport = :11434' 2>/dev/null | grep -q .; then
      if timeout 5s ollama ps 2>/dev/null | grep -F -- "$model_name" >/dev/null; then
        loaded=1
      fi
    fi
  fi
  if [ "$loaded" != "1" ]; then
    printf '%s\n' "model is not loaded" >&2
    exit 1
  fi
  if [ -z "${ATG_REPO:-}" ] || [ ! -d "$ATG_REPO" ]; then
    printf '%s\n' "ATG checkout is missing" >&2
    exit 1
  fi
  did="Ran one atg-compile case against the already-loaded model under scripts/model_lock.sh. No download and no ollama pull."
fi

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
mkdir -p -- "$(dirname -- "$receipt")"
lock="${receipt}.lock"
exec 9>"$lock"
if ! flock -n 9; then
  printf '%s\n' "receipt-path flock is held" >&2
  exit 2
fi

tmp=
cleanup() {
  if [ -n "${tmp:-}" ]; then
    rm -f "$tmp"
  fi
  if [ -n "${lock:-}" ]; then
    rm -f "$lock"
  fi
  if [ -n "${bench_out:-}" ]; then
    rm -f "$bench_out"
  fi
}
trap cleanup EXIT

if [ "$mode" = "model" ]; then
  bench_out=$(mktemp)
  model_cmd=(
    python3 "$root/examples/atg-compile/bench.py"
    --limit 1
    --case-timeout 60
    --health-timeout 2
    --receipt "$bench_out"
    --atg-repo "$ATG_REPO"
    --model "$model_name"
    --base-url "$base_url"
  )
fi

set +e
if [ "$mode" = "offline" ]; then
  timeout 60s "${offline_cmd[@]}"
  rc=$?
else
  timeout 180s "$root/scripts/model_lock.sh" "${model_cmd[@]}"
  rc=$?
fi
set -e

if [ "$rc" -ne 0 ]; then
  printf '%s\n' "check failed: $rc" >&2
  exit "$rc"
fi

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_id="atg-${head:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"
tmp=$(mktemp "$(dirname -- "$receipt")/.receipt.XXXXXX")
RECEIPT_DID=$did \
RECEIPT_SHA=$head \
RECEIPT_STARTED=$started \
RECEIPT_FINISHED=$finished \
RECEIPT_RUN_ID=$run_id \
RECEIPT_VERSION=$tool_version \
python3 - "$tmp" <<'PY'
import json
import os
import sys

path = sys.argv[1]
doc = {
    "slug": "atomic-task-graph-atg",
    "run_kind": "pipeline",
    "main_sha": os.environ["RECEIPT_SHA"],
    "run_id": os.environ["RECEIPT_RUN_ID"],
    "started": os.environ["RECEIPT_STARTED"],
    "finished": os.environ["RECEIPT_FINISHED"],
    "outcome": "ok",
    "tool_version": os.environ["RECEIPT_VERSION"],
    "did": os.environ["RECEIPT_DID"],
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
PY
mv "$tmp" "$receipt"
tmp=
printf '%s\n' "$receipt"
