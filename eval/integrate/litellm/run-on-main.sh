#!/bin/bash
# Read-only probe of an already running OpenAI-compatible proxy.
#
# A completion is the only call wrapped by scripts/model_lock.sh.
# This probe is not a completion, so it does not call that wrapper.
#
# Lane marker: /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/litellm.dispatched
# If that file exists and its recorded pid is not an ancestor of this
# process, exit 2 before any probe or receipt write. The driver writes
# "pid <lane-pid>" and still holds the marker when it runs this script,
# so that admitted lane continues. This script does not create the marker
# and does not remove it.
#
# The main push is a fast-forward under one flock on
# /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/push.lock
# (lane.sh holds that flock around the fast-forward). This script does not
# take that lock and does not push.
#
# A timeout is not a pass. A missing binary, a proxy error, or a timeout
# exits nonzero and does not create or update the receipt.
#
# Usage: eval/integrate/litellm/run-on-main.sh RECEIPT_PATH

set -euo pipefail

MARKER=${PFY_LITELLM_LANE_MARKER:-/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/litellm.dispatched}

marker_pid_is_ancestor() {
  local file=$1
  local target cur guard ppid
  target=$(sed -n 's/^pid \([0-9][0-9]*\)[[:space:]]*$/\1/p' "$file" 2>/dev/null | head -n 1 || true)
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

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/litellm/run-on-main.sh RECEIPT_PATH" >&2
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
if [[ ! "$sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf '%s\n' "main_sha is not 40 hex characters" >&2
  exit 1
fi

# Write receipt.json only after the ancestor check and a successful probe.
for bin in curl timeout python3; do
  if ! command -v "$bin" >/dev/null 2>&1; then
    printf '%s\n' "missing binary: $bin" >&2
    exit 1
  fi
done

body=
tmp=
cleanup() {
  if [ -n "${body:-}" ]; then
    rm -f "$body"
  fi
  if [ -n "${tmp:-}" ]; then
    rm -f "$tmp"
  fi
}
trap cleanup EXIT

saw_timeout=0
probe_models() {
  local base url code rc count
  base=${1%/}
  base=${base%/v1}
  url=$base/v1/models
  body=$(mktemp)
  set +e
  code=$(timeout 10 curl -s --noproxy '*' --max-time 5 -o "$body" -w '%{http_code}' "$url")
  rc=$?
  set -e
  if [ "$rc" -ne 0 ]; then
    rm -f "$body"
    body=
    if [ "$rc" -eq 124 ] || [ "$rc" -eq 28 ]; then
      saw_timeout=1
    fi
    return 1
  fi
  if [ "$code" != "200" ]; then
    rm -f "$body"
    body=
    return 1
  fi
  set +e
  count=$(python3 - "$body" <<'PY'
import json
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
if not raw.strip():
    raise SystemExit(1)
try:
    data = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit(1)
if not isinstance(data, dict):
    raise SystemExit(1)
items = data.get("data")
if items is None:
    items = data.get("models")
if not isinstance(items, list):
    raise SystemExit(1)
print(len(items))
PY
  )
  rc=$?
  set -e
  rm -f "$body"
  body=
  if [ "$rc" -ne 0 ]; then
    return 1
  fi
  PROBE_URL=$url
  PROBE_COUNT=$count
  return 0
}

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
PROBE_URL=
PROBE_COUNT=
if [ -n "${PFY_LITELLM_BASE:-}" ]; then
  if ! probe_models "$PFY_LITELLM_BASE"; then
    if [ "$saw_timeout" -eq 1 ]; then
      printf '%s\n' "proxy timeout" >&2
      exit 124
    fi
    printf '%s\n' "proxy probe failed" >&2
    exit 1
  fi
else
  probed=0
  for base in http://127.0.0.1:4000 http://127.0.0.1:11435 http://127.0.0.1:11434; do
    if probe_models "$base"; then
      probed=1
      break
    fi
  done
  if [ "$probed" -ne 1 ]; then
    if [ "$saw_timeout" -eq 1 ]; then
      printf '%s\n' "proxy timeout" >&2
      exit 124
    fi
    printf '%s\n' "proxy missing" >&2
    exit 1
  fi
fi
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)

tool_version=openai-compat
set +e
imported=$(timeout 10 python3 -c 'import litellm; print(getattr(litellm, "__version__", "") or "")' 2>/dev/null)
vrc=$?
set -e
if [ "$vrc" -eq 124 ]; then
  printf '%s\n' "version timeout" >&2
  exit 124
fi
if [ "$vrc" -eq 0 ]; then
  imported=${imported%%$'\n'*}
  imported=${imported//$'\r'/}
  if [ -n "$imported" ]; then
    tool_version=$imported
  fi
fi

dest_dir=$(dirname -- "$receipt")
mkdir -p "$dest_dir"
tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_TMP=$tmp
export RECEIPT_SHA=$sha
export RECEIPT_RUN_ID="litellm-${sha:0:12}-${started}"
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$tool_version
export RECEIPT_DID="Read-only GET ${PROBE_URL} on the already running OpenAI-compatible proxy returned HTTP 200 and ${PROBE_COUNT} model ids. No completion."
python3 - <<'PY'
import json
import os
from pathlib import Path

doc = {
    "slug": "litellm",
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
mv -f "$tmp" "$receipt"
tmp=
printf '%s\n' "$receipt"
