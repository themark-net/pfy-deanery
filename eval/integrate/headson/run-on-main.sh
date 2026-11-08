#!/bin/bash
# Preview one json fixture with the pinned headson binary.
# Write the receipt only when HEAD is an ancestor of origin/main and the preview exits 0.
# Missing binary, bad output, or timeout: exit nonzero and write no receipt.
#
# The driver flock on /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/push.lock
# serializes the fast-forward. This script does not take that lock and does not create the lane marker.
#
# The lane marker is $HSON_LANE_MARKER, or
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/headson.dispatched.
# A second start exits 2 and writes no receipt. The driver writes "pid <lane-pid>"
# and still holds that file when it runs this script, so a marker whose pid is an
# ancestor of this process is the admitted lane and the preview continues.
#
# Usage: eval/integrate/headson/run-on-main.sh RECEIPT.json

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/headson/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

receipt=$1
if [ "${receipt#/}" = "$receipt" ]; then
  receipt="$PWD/$receipt"
fi

marker=${HSON_LANE_MARKER:-/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/headson.dispatched}

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

if [ -f "$marker" ]; then
  if ! marker_pid_is_ancestor "$marker"; then
    printf '%s\n' "headson already dispatched" >&2
    exit 2
  fi
fi

root=$(git rev-parse --show-toplevel)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null; then
  printf '%s\n' "origin/main is not available" >&2
  exit 1
fi

main_sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$main_sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main" >&2
  exit 1
fi
if ! [[ "$main_sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf '%s\n' "main_sha is not 40 hex characters" >&2
  exit 1
fi

fixture="$root/eval/integrate/headson/fixture.json"
byte_cap=1024
if [ ! -f "$fixture" ]; then
  printf '%s\n' "fixture missing" >&2
  exit 1
fi

if [ -n "${HSON_BIN:-}" ]; then
  bin=$HSON_BIN
else
  bin="${HOME}/.cache/pfy/tools/headson/bin/hson"
fi
if [ ! -x "$bin" ]; then
  printf '%s\n' "pinned headson binary missing" >&2
  exit 1
fi

expected_sha=1a5920a7088db2f2eaf3e53c588fb5133b020a4b9aa417631977e16ead136422
actual_sha=$(sha256sum "$bin" | awk '{print $1}')
if [ "$actual_sha" != "$expected_sha" ]; then
  printf '%s\n' "pinned headson binary mismatch" >&2
  exit 1
fi

tool_version=$(timeout 30 "$bin" --version 2>/dev/null | head -n 1 | tr -d '\r' || true)
if [ -z "$tool_version" ]; then
  printf '%s\n' "pinned headson version missing" >&2
  exit 1
fi

preview=$(mktemp)
trap 'rm -f "$preview"' EXIT

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
timeout 30 "$bin" -c "$byte_cap" -i json -f json -t strict --no-color "$fixture" >"$preview"
code=$?
set -e
if [ "$code" -ne 0 ]; then
  exit "$code"
fi

python3 - "$preview" "$byte_cap" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
cap = int(sys.argv[2])
raw = path.read_bytes()
if not raw.strip():
    raise SystemExit(1)
body = raw[:-1] if raw.endswith(b"\n") else raw
if len(body) > cap:
    raise SystemExit(1)
try:
    json.loads(body.decode("utf-8"))
except (UnicodeDecodeError, json.JSONDecodeError):
    raise SystemExit(1)
PY

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
did="Previewed one fixture with -c and -t strict."
mkdir -p "$(dirname "$receipt")"
python3 - "$receipt" "$main_sha" "$preview" "$started" "$finished" "$tool_version" "$did" <<'PY'
import json
import os
import sys
import tempfile

receipt, main_sha, log_path, started, finished, tool_version, did = sys.argv[1:]
doc = {
    "slug": "headson",
    "run_kind": "pipeline",
    "main_sha": main_sha,
    "log_path": log_path,
    "started": started,
    "finished": finished,
    "outcome": "pass",
    "tool_version": tool_version,
    "did": did,
}
parent = os.path.dirname(receipt) or "."
fd, tmp_name = tempfile.mkstemp(prefix=".receipt.", dir=parent)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(doc, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_name, receipt)
except Exception:
    try:
        os.unlink(tmp_name)
    except OSError:
        pass
    raise
PY

trap - EXIT
printf '%s\n' "$receipt"
