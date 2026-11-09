#!/bin/bash
# One advisory scan of the in-repo fixture, then a pipeline receipt.
#
# Usage: eval/integrate/bumblebee/run-on-main.sh RECEIPT.json
#
# The lane marker is $BUMBLEBEE_LANE_MARKER, or
# tmp/integrate2/bumblebee.dispatched in the main checkout (the git common dir's parent).
# First admission creates that marker and continues. A second start exits 2
# and writes no receipt.
#
# The driver creates the marker before Build and still holds it when it runs
# this script for the receipt. Exiting 2 whenever the file exists would park
# that receipt. A marker whose pid is an ancestor of this process is that
# admitted lane, so the scan continues. Any other existing marker is a second
# start. A missing marker is created only after HEAD is an ancestor of
# origin/main, so a refused run does not claim the lane.
#
# bumblebee-main-ff.lock is the flock for the main fast-forward only.
# It is not a global CI lock and it is not scripts/model_lock.sh.
#
# The scan reads tmp/bumblebee-fixture only. It calls scripts/pfy_mcp_scan.py.
# Missing binary, scan error, or timeout: exit nonzero and write no receipt.
# A timeout is not a pass. The scanner's own --out file is a temp file, not
# this receipt. Version text is read with a scratch HOME. When this script is
# not run, today's scan behavior stays.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/bumblebee/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi
receipt=$1
if [ "${receipt#/}" = "$receipt" ]; then
  receipt="$PWD/$receipt"
fi

marker=${BUMBLEBEE_LANE_MARKER:-}
if [ -z "$marker" ]; then
  common=$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
  if [ -z "$common" ]; then
    printf '%s\n' "no git checkout for the lane marker" >&2
    exit 2
  fi
  marker="${common%/.git}/tmp/integrate2/bumblebee.dispatched"
fi
if [ "${marker#/}" = "$marker" ]; then
  marker="$PWD/$marker"
fi

marker_pid_is_ancestor() {
  local file=$1
  local target cur guard ppid
  target=$(sed -n 's/^pid \([0-9][0-9]*\)[[:space:]]*$/\1/p' "$file" | head -n 1)
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
    ppid=$(awk '/^PPid:/ {print $2}' "/proc/$cur/status")
    if [ -z "$ppid" ] || [ "$ppid" = "$cur" ]; then
      return 1
    fi
    cur=$ppid
    guard=$((guard + 1))
  done
  return 1
}

if [ -f "$marker" ] && ! marker_pid_is_ancestor "$marker"; then
  printf '%s\n' "already dispatched" >&2
  exit 2
fi

root=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
  printf '%s\n' "origin/main is not available" >&2
  exit 1
fi
head=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$head" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main" >&2
  exit 1
fi
if ! printf '%s\n' "$head" | grep -E -q '^[0-9a-f]{40}$'; then
  printf '%s\n' "main_sha is not 40 hex characters" >&2
  exit 1
fi

if [ ! -f "$marker" ]; then
  mkdir -p "$(dirname -- "$marker")"
  if ! (set -o noclobber; printf 'pid %s\n' "$$" > "$marker") 2>/dev/null; then
    printf '%s\n' "already dispatched" >&2
    exit 2
  fi
fi

fix=$root/tmp/bumblebee-fixture
rm -rf "$fix"
mkdir -p "$fix/.cursor" "$fix/clean-app"
cat > "$fix/.cursor/mcp.json" <<'EOF'
{
  "mcpServers": {
    "local-notes": {
      "command": "node",
      "args": ["./server.js"]
    }
  }
}
EOF
cat > "$fix/clean-app/package-lock.json" <<'EOF'
{
  "name": "clean-app",
  "version": "1.0.0",
  "lockfileVersion": 2,
  "requires": true,
  "packages": {
    "": {
      "name": "clean-app",
      "version": "1.0.0"
    },
    "node_modules/left-pad": {
      "version": "1.3.0"
    }
  },
  "dependencies": {
    "left-pad": {
      "version": "1.3.0"
    }
  }
}
EOF

scan_out=$(mktemp)
receipt_tmp=
cleanup() {
  rm -f "$scan_out"
  if [ -n "${receipt_tmp:-}" ]; then
    rm -f "$receipt_tmp"
  fi
}
trap cleanup EXIT

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
timeout --foreground 150 python3 "$root/scripts/pfy_mcp_scan.py" \
  --root "$fix" \
  --out "$scan_out"
rc=$?
set -e
if [ "$rc" -eq 124 ]; then
  printf '%s\n' "scan timeout" >&2
  exit 124
fi
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "scan failed rc=$rc" >&2
  exit "$rc"
fi
if [ ! -s "$scan_out" ]; then
  printf '%s\n' "scan wrote no result" >&2
  exit 1
fi

verdict=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("verdict",""))' "$scan_out")
if [ "$verdict" != "CLEAN" ]; then
  printf '%s\n' "scan verdict ${verdict:-empty}" >&2
  exit 1
fi

bin=$(python3 - <<'PY'
import importlib.util

spec = importlib.util.spec_from_file_location("pfy_mcp_scan", "scripts/pfy_mcp_scan.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
found = mod.find_binary()
print("" if found is None else str(found))
PY
)
version=bumblebee
if [ -n "$bin" ] && [ -x "$bin" ]; then
  vhome=$(mktemp -d)
  version=$(
    timeout --foreground 5 env -i PATH="/usr/bin:/bin" HOME="$vhome" \
      "$bin" version 2>/dev/null | head -n 1 | tr -d '\r' || true
  )
  rm -rf "$vhome"
fi
if [ -z "$version" ] || [ "${#version}" -gt 80 ] || printf '%s' "$version" | grep -q '[/~]'; then
  version=bumblebee
fi

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
did="Scanned tmp/bumblebee-fixture with scripts/pfy_mcp_scan.py. Verdict CLEAN. Findings 0."
run_id="bumblebee-${head:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"

dest_dir=$(dirname -- "$receipt")
mkdir -p "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_SHA=$head
export RECEIPT_RUN_ID=$run_id
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$version
export RECEIPT_DID=$did
python3 - "$receipt_tmp" <<'PY'
import json
import os
import sys

doc = {
    "slug": "bumblebee",
    "run_kind": "pipeline",
    "main_sha": os.environ["RECEIPT_SHA"],
    "run_id": os.environ["RECEIPT_RUN_ID"],
    "started": os.environ["RECEIPT_STARTED"],
    "finished": os.environ["RECEIPT_FINISHED"],
    "outcome": "ok",
    "tool_version": os.environ["RECEIPT_VERSION"],
    "did": os.environ["RECEIPT_DID"],
}
with open(sys.argv[1], "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
PY
mv "$receipt_tmp" "$receipt"
receipt_tmp=
trap - EXIT
rm -f "$scan_out"
printf '%s\n' "$receipt"
