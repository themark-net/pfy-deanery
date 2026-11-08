#!/bin/bash
# Run the wired dcg gate once from a checkout whose HEAD is an ancestor of origin/main.
# Write the receipt JSON to the path in $1.
# Exit nonzero and write nothing when HEAD is not an ancestor of origin/main.
# The guard classifies argv and does not execute it.

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

dest=$1

set -euo pipefail

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  printf '%s\n' "not a git checkout" >&2
  exit 1
fi
if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
  printf '%s\n' "origin/main is not available" >&2
  exit 1
fi

head=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$head" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main" >&2
  exit 1
fi

HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
ROOT=$(CDPATH= cd -- "$HERE/../../.." && pwd)
GUARD="$ROOT/scripts/integrations/dcg/guard.sh"
if [ ! -f "$GUARD" ]; then
  printf '%s\n' "guard.sh missing: $GUARD" >&2
  exit 1
fi

if [ -n "${PFY_DCG_BIN+x}" ]; then
  bin=$PFY_DCG_BIN
else
  bin="${HOME}/.cache/pfy/tools/destructive-command-guard/unpack/dcg"
fi
if [ -f "$bin" ]; then
  cache_home="${PFY_DCG_CACHE_HOME:-${HOME}/.cache/pfy/tools/destructive-command-guard/home}"
  tool_version=$(
    env -i PATH="/usr/bin:/bin" LANG=C NO_COLOR=1 HOME="$cache_home" \
      "$bin" --version 2>/dev/null || true
  )
  tool_version=${tool_version%%$'\n'*}
  tool_version=${tool_version//$'\r'/}
  if [ -z "$tool_version" ]; then
    tool_version=fallback
  fi
else
  tool_version=fallback
fi

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
bash "$GUARD" rm -rf / >/dev/null
code=$?
set -e
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)

if [ "$code" -eq 126 ]; then
  outcome=ok
else
  outcome="not-denied"
fi
run_id="dcg-${head:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"
did="Classified argv rm -rf / with scripts/integrations/dcg/guard.sh. Exit ${code}. The command was not executed."

dest_dir=$(CDPATH= cd -- "$(dirname -- "$dest")" && pwd)
tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
trap 'rm -f "$tmp"' EXIT
python3 - "$tmp" "$head" "$started" "$finished" "$outcome" "$tool_version" "$did" "$run_id" <<'PY'
import json
import sys

path, sha, started, finished, outcome, version, did, run_id = sys.argv[1:]
doc = {
    "slug": "destructive-command-guard",
    "run_kind": "gate",
    "main_sha": sha,
    "run_id": run_id,
    "started": started,
    "finished": finished,
    "outcome": outcome,
    "tool_version": version,
    "did": did,
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
PY
mv "$tmp" "$dest"
trap - EXIT
printf '%s\n' "$dest"
