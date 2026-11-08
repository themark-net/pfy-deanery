#!/bin/bash
# One read-only GET of the server that is already running.
#
# Usage: eval/integrate/ollama/run-on-main.sh RECEIPT.json
# Driver, after this commit is on origin/main:
#   bash eval/integrate/ollama/run-on-main.sh eval/integrate/ollama/receipt.json
#
# Lane marker (this script does not create, remove, or write it):
#   /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/ollama.dispatched
# A second start exits 2.
# The main push is a fast-forward under one flock on
#   /home/mark/DEVELOP/pfy-mentat/tmp/integrate2/push.lock
# This script does not take that flock. scripts/model_lock.sh wraps only the GET.
#
# HEAD must be an ancestor of origin/main (git merge-base --is-ancestor).
# A worktree-only diff is not a receipt: exit nonzero and write nothing.
# A timeout or any other failed GET exits nonzero and writes no receipt.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/ollama/run-on-main.sh RECEIPT.json" >&2
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

probe=$(mktemp)
receipt_tmp=
cleanup() {
  rm -f "$probe"
  if [ -n "${receipt_tmp}" ]; then
    rm -f "$receipt_tmp"
  fi
}
trap cleanup EXIT

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
"$root/scripts/model_lock.sh" python3 - "$probe" <<'PY'
import json
import sys
import urllib.error
import urllib.request

dest = sys.argv[1]
url = "http://127.0.0.1:11434/api/version"
req = urllib.request.Request(url, method="GET")
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        status = int(resp.getcode())
        raw = resp.read()
except (urllib.error.URLError, TimeoutError, OSError):
    sys.exit(1)
if status != 200:
    sys.exit(1)
version = ""
try:
    parsed = json.loads(raw.decode("utf-8"))
    if isinstance(parsed, dict) and isinstance(parsed.get("version"), str):
        version = parsed["version"].splitlines()[0].strip()[:64]
except (UnicodeError, json.JSONDecodeError):
    version = ""
if not version:
    version = "unknown"
with open(dest, "w", encoding="utf-8") as handle:
    handle.write("%s\n%s\n" % (status, version))
PY
rc=$?
set -e
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "GET /api/version failed" >&2
  exit "$rc"
fi

http_status=$(sed -n '1p' "$probe")
tool_version=$(sed -n '2p' "$probe")
if [ "$http_status" != "200" ] || [ -z "$tool_version" ]; then
  printf '%s\n' "GET /api/version did not return HTTP 200" >&2
  exit 1
fi

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
dest_dir=$(dirname -- "$receipt")
mkdir -p "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_TMP=$receipt_tmp
export RECEIPT_SHA=$sha
export RECEIPT_RUN_ID="ollama-${sha:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$tool_version
export RECEIPT_DID="GET http://127.0.0.1:11434/api/version returned HTTP 200."
python3 - <<'PY'
import json
import os
from pathlib import Path

doc = {
    "slug": "ollama",
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
trap - EXIT
rm -f "$probe"
printf '%s\n' "$receipt"
