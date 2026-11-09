#!/bin/bash
# Read one status from a server the operator already started.
# Usage: eval/integrate/strata/run-on-main.sh RECEIPT.json
#
# PFY_STRATA_BASE if set, otherwise http://127.0.0.1:18158.
# The request is GET /v1/status on a loopback host only. It does not start
# the server and it does not fetch model files.
# scripts/model_lock.sh wraps a generate call. This receipt uses status only.
# A timeout is not a pass. Missing listener, error, or timeout writes no receipt.
#
# Lane marker: $HOME/DEVELOP/pfy-mentat/tmp/integrate2/strata.dispatched
# An existing marker is a second start and exits 2, unless its pid line is an
# ancestor of this process (the admitted lane). This script does not create
# or remove the marker.
#
# The main push is a fast-forward under one flock:
# $HOME/DEVELOP/pfy-mentat/tmp/integrate2/push.lock
# This script does not take that flock. No third global lock.
#
# Writes receipt.json only when HEAD is an ancestor of origin/main
# (git merge-base --is-ancestor). run_kind is pipeline.

set -euo pipefail

MARKER=${PFY_STRATA_LANE_MARKER:-$HOME/DEVELOP/pfy-mentat/tmp/integrate2/strata.dispatched}

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/strata/run-on-main.sh RECEIPT.json" >&2
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

if [ -e "$MARKER" ]; then
  if ! marker_pid_is_ancestor "$MARKER"; then
    printf '%s\n' "already dispatched: $MARKER" >&2
    exit 2
  fi
fi

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../../.." && pwd)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null 2>&1; then
  printf '%s\n' "origin/main is missing; no receipt" >&2
  exit 1
fi
sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main; no receipt" >&2
  exit 1
fi
if ! printf '%s\n' "$sha" | grep -E -q '^[0-9a-f]{40}$'; then
  printf '%s\n' "main_sha is not 40 hex characters" >&2
  exit 1
fi

base=${PFY_STRATA_BASE:-http://127.0.0.1:18158}
base=${base%/}
case $base in
  *[@[:space:]]*)
    printf '%s\n' "status request failed; no receipt" >&2
    exit 1
    ;;
esac
case $base in
  */v1) status_url=$base/status ;;
  *) status_url=$base/v1/status ;;
esac

secs=${PFY_STRATA_TIMEOUT:-5}
case $secs in
  [1-9]|[12][0-9]|30) ;;
  *) secs=5 ;;
esac

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
probe=$(
  PFY_STRATA_STATUS_URL=$status_url \
  PFY_STRATA_TIMEOUT=$secs \
    timeout "$((secs + 1))s" python3 - <<'PY'
import json
import os
import socket
import sys
import urllib.parse
import urllib.request

url = os.environ.get("PFY_STRATA_STATUS_URL", "")
parsed = urllib.parse.urlparse(url)
host = (parsed.hostname or "").lower().rstrip(".")
if (
    parsed.scheme not in ("http", "https")
    or parsed.username
    or parsed.password
    or host not in ("127.0.0.1", "localhost", "::1")
):
    sys.exit(1)
key = os.environ.get("PFY_STRATA_API_KEY") or os.environ.get("STRATA_API_KEY") or ""
try:
    sock_timeout = float(os.environ.get("PFY_STRATA_TIMEOUT", "5"))
except ValueError:
    sock_timeout = 5.0
if sock_timeout < 1:
    sock_timeout = 5.0

req = urllib.request.Request(url, method="GET")
if key:
    req.add_header("Authorization", "Bearer " + key)

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None

opener = urllib.request.build_opener(NoRedirect)

def give_up(exc):
    reason = getattr(exc, "reason", None)
    timed = isinstance(exc, (TimeoutError, socket.timeout)) or isinstance(
        reason, (TimeoutError, socket.timeout)
    )
    if not timed and "timed out" in str(reason or "").lower():
        timed = True
    sys.exit(124 if timed else 1)

try:
    with opener.open(req, timeout=sock_timeout) as resp:
        code = getattr(resp, "status", None) or resp.getcode()
        raw = resp.read(65536)
except Exception as exc:
    give_up(exc)
if code != 200:
    sys.exit(1)
try:
    data = json.loads(raw.decode("utf-8"))
except (UnicodeError, json.JSONDecodeError):
    sys.exit(1)
if not isinstance(data, dict) or data.get("service") != "strata":
    sys.exit(1)
engine = data.get("engine")
if isinstance(engine, str) and engine.strip():
    engine = " ".join(engine.split())
else:
    engine = "strata"
if len(engine) > 80 or (key and len(key) >= 8 and key in engine):
    engine = "strata"
loaded = data.get("loaded")
if loaded is True:
    flag = "true"
elif loaded is False:
    flag = "false"
else:
    flag = "absent"
sys.stdout.write(engine + "\n" + flag + "\n")
PY
)
rc=$?
set -e
if [ "$rc" -eq 124 ]; then
  printf '%s\n' "timeout is not a pass; no receipt" >&2
  exit 124
fi
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "status request failed; no receipt" >&2
  exit 1
fi

tool_version=$(printf '%s\n' "$probe" | sed -n '1p')
loaded_flag=$(printf '%s\n' "$probe" | sed -n '2p')
case $loaded_flag in
  true|false|absent) ;;
  *)
    printf '%s\n' "status request failed; no receipt" >&2
    exit 1
    ;;
esac
if [ -z "$tool_version" ]; then
  printf '%s\n' "status request failed; no receipt" >&2
  exit 1
fi
secret=${PFY_STRATA_API_KEY:-${STRATA_API_KEY:-}}
if [ -n "$secret" ] && [ "${#secret}" -ge 8 ]; then
  case $probe in
    *"$secret"*)
      printf '%s\n' "status request failed; no receipt" >&2
      exit 1
      ;;
  esac
fi
unset secret

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_id="strata-${sha:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"
did="Read GET /v1/status from the server the operator already started. service=strata loaded=${loaded_flag}. Did not start the server."

dest_dir=$(dirname -- "$receipt")
mkdir -p -- "$dest_dir"
tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
cleanup() {
  if [ -n "${tmp:-}" ]; then
    rm -f -- "$tmp"
  fi
}
trap cleanup EXIT
RECEIPT_TMP=$tmp \
RECEIPT_SHA=$sha \
RECEIPT_RUN_ID=$run_id \
RECEIPT_STARTED=$started \
RECEIPT_FINISHED=$finished \
RECEIPT_VERSION=$tool_version \
RECEIPT_DID=$did \
python3 - <<'PY'
import json
import os
from pathlib import Path

doc = {
    "slug": "strata",
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
mv -f -- "$tmp" "$receipt"
tmp=
trap - EXIT
printf '%s\n' "$receipt"
