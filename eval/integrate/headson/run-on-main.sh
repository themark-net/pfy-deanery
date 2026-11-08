#!/bin/bash
# Preview one json fixture with the pinned headson binary.
# Write the receipt only when HEAD is an ancestor of origin/main and the preview exits 0.
# Missing binary, bad output, or timeout: exit nonzero and write no receipt.
#
# The driver flock on /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/push.lock
# serializes the fast-forward. This script does not take that lock and does not create the lane marker.
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

marker=/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/headson.dispatched
if [ -f "$marker" ]; then
  printf '%s\n' "headson already dispatched" >&2
  exit 2
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
fixture_bytes=$(wc -c < "$fixture" | tr -d ' ')
if [ "$fixture_bytes" -le "$byte_cap" ]; then
  :
else
  printf '%s\n' "byte cap is below the fixture" >&2
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

tool_version=$("$bin" --version 2>/dev/null | head -n 1 | tr -d '\r' || true)
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
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
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
json.loads(body.decode("utf-8"))
PY

did="Previewed one fixture with -c and -t strict."
mkdir -p "$(dirname "$receipt")"
python3 - "$receipt" "$main_sha" "$preview" "$started" "$finished" "$tool_version" "$did" <<'PY'
import json
import sys

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
with open(receipt, "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
PY

trap - EXIT
printf '%s\n' "$receipt"
