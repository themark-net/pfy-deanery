#!/bin/bash
# One sandboxed fixture install and one sandboxed fixture run on a main SHA.
#
# Usage: eval/integrate/sandlock/run-on-main.sh RECEIPT.json
#
# Exit 1 when HEAD is not an ancestor of origin/main. Exit 2 on bad usage.
# The receipt is written only after both commands exit 0.
# Cache: PFY_SANDLOCK_CACHE, else ~/.cache/pfy/tools/integrate-sandlock/lane.
# SANDLOCK_BIN, when set, is the passthrough binary wrap.py calls.
# When it is unset and the cache unpack binary is executable, wrap.py calls
# confine.py and SANDLOCK_REAL points at that unpack binary.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "$1" ]; then
  echo "usage: eval/integrate/sandlock/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

receipt=$1
root=$(git rev-parse --show-toplevel)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
  echo "origin/main is missing" >&2
  exit 1
fi
head=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$head" origin/main; then
  echo "HEAD is not an ancestor of origin/main" >&2
  exit 1
fi

wrap=$root/scripts/integrations/sandlock/wrap.py
confine=$root/scripts/integrations/sandlock/confine.py
hello=$root/eval/integrate/sandlock/fixtures/hello.sh
if [ ! -f "$wrap" ] || [ ! -f "$hello" ]; then
  echo "sandlock wiring is missing" >&2
  exit 1
fi

base=${PFY_SANDLOCK_CACHE:-${HOME}/.cache/pfy/tools/integrate-sandlock/lane}
stage=$base/stage
wrap_cache=$base/wrap
mkdir -p "$stage" "$wrap_cache"

if [ -z "${SANDLOCK_BIN:-}" ]; then
  real=${SANDLOCK_REAL:-${HOME}/.cache/pfy/tools/sandlock/unpack/sandlock}
  if [ -x "$real" ] && [ -f "$confine" ]; then
    export SANDLOCK_REAL=$real
    export SANDLOCK_BIN=$confine
  fi
fi

export PFY_SANDLOCK=all
export SANDLOCK_STAGE=$stage

cp_bin=$(command -v cp)
sh_bin=$(command -v sh)
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
install_err=$(mktemp)
run_err=$(mktemp)
trap 'rm -f "$install_err" "$run_err"' EXIT

set +e
python3 "$wrap" --cache "$wrap_cache" --action install -- "$cp_bin" "$hello" "$stage/hello.sh" 2>"$install_err"
install_rc=$?
python3 "$wrap" --cache "$wrap_cache" --action run -- "$sh_bin" "$stage/hello.sh" "$stage/out.txt" 2>"$run_err"
run_rc=$?
set -e

cat "$install_err" >&2 || true
cat "$run_err" >&2 || true

if [ "$install_rc" -ne 0 ]; then
  exit "$install_rc"
fi
if [ "$run_rc" -ne 0 ]; then
  exit "$run_rc"
fi
if [ "$(cat "$stage/out.txt")" != "ok" ]; then
  echo "fixture tool did not write ok" >&2
  exit 1
fi

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
version=sandlock-bin
if [ -n "${SANDLOCK_REAL:-}" ] && [ -x "${SANDLOCK_REAL}" ]; then
  version=$("$SANDLOCK_REAL" --version 2>/dev/null | head -n 1 | tr -d '\r' || true)
fi
if [ -z "$version" ]; then
  version=sandlock-bin
fi

did="Sandboxed one local fixture install and one fixture tool run. Both commands exited 0."
blob=$(cat "$install_err" "$run_err" || true)
case "$blob" in
  *'sandlock: unsandboxed'*)
    did="Fixture install or run fell back unsandboxed after sandlock did not start the command. Both commands exited 0."
    ;;
esac

export RECEIPT_PATH=$receipt
export RECEIPT_SHA=$head
export RECEIPT_RUN_ID="sandlock-${head:0:12}-${started}"
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$version
export RECEIPT_DID=$did
mkdir -p "$(dirname "$receipt")"
python3 - <<'PY'
import json
import os
from pathlib import Path

doc = {
    "slug": "sandlock",
    "run_kind": "pipeline",
    "main_sha": os.environ["RECEIPT_SHA"],
    "run_id": os.environ["RECEIPT_RUN_ID"],
    "started": os.environ["RECEIPT_STARTED"],
    "finished": os.environ["RECEIPT_FINISHED"],
    "outcome": "ok",
    "tool_version": os.environ["RECEIPT_VERSION"],
    "did": os.environ["RECEIPT_DID"],
    "log_path": "ops:eval/integrate/sandlock/notes.md",
}
Path(os.environ["RECEIPT_PATH"]).write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
PY
