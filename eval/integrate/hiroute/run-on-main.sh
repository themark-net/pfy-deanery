#!/bin/bash
# Offline dry classification for the HiRoute difficulty router.
# no-listen: do not bind a port. Do not use port 11434. Do not start a daemon.
# A missing binary, a required socket, a listen, or a timeout writes no receipt.
# This script does not create the dispatched marker and does not push.
# modular-ci: no .github/workflows job, no ci/ job, no model_lock.sh
# extra lock: flock eval/integrate/hiroute/hiroute-ff.lock
# The main push is a fast-forward under that flock. A second start exits 2.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/hiroute/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

dest=$1
marker=/home/mark/DEVELOP/pfy-mentat/tmp/integrate2/hiroute.dispatched
if [ -e "$marker" ]; then
  printf '%s\n' "already dispatched: $marker" >&2
  exit 2
fi

if [ -n "${HIROUTE_BIN+x}" ]; then
  bin=$HIROUTE_BIN
else
  bin=${HOME:-/nonexistent}/.cache/pfy/tools/hiroute/home/.local/bin/hiroute
fi
if [ ! -x "$bin" ]; then
  printf '%s\n' "hiroute binary missing" >&2
  exit 1
fi

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH= cd -- "$here/../../.." && pwd)
cd "$root"

if ! git rev-parse --verify --quiet 'origin/main^{commit}' >/dev/null 2>&1; then
  printf '%s\n' "origin/main is missing" >&2
  exit 1
fi
sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main" >&2
  exit 1
fi
case $sha in
  [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
  *)
    printf '%s\n' "HEAD is not 40 hex chars" >&2
    exit 1
    ;;
esac

probe=$(mktemp -d)
trap 'rm -rf "$probe"' EXIT
mkdir -p "$probe/home" "$probe/run" "$probe/state" "$probe/config" "$probe/cache" "$probe/tmp"
set +e
timeout 5 env -i \
  PATH="/usr/bin:/bin" \
  HOME="$probe/home" \
  XDG_RUNTIME_DIR="$probe/run" \
  XDG_STATE_HOME="$probe/state" \
  XDG_CONFIG_HOME="$probe/config" \
  XDG_CACHE_HOME="$probe/cache" \
  TMPDIR="$probe/tmp" \
  "$bin" schema show --command-id routing.preview --output json >"$probe/schema.json" 2>"$probe/schema.err"
code=$?
set -e
if [ "$code" -ne 0 ]; then
  printf '%s\n' "offline contract check failed ($code); no receipt" >&2
  exit 1
fi

python3 - "$probe/schema.json" <<'PY'
import json
import sys

doc = json.load(open(sys.argv[1], encoding="utf-8"))
data = doc.get("data") or {}
network = str(data.get("network") or "")
model = str(data.get("model_call") or "")
effect = str(data.get("effect") or "")
# no-listen. Port 11434 is Ollama and is not a classification path.
if network not in {"none", "no-listen", "offline"} or model not in {"never", "none"} or effect not in {"none", ""}:
    sys.stderr.write("socket or listen required (network=%s); no receipt\n" % network)
    raise SystemExit(1)
PY

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
timeout 5 env -i \
  PATH="/usr/bin:/bin" \
  HOME="$probe/home" \
  XDG_RUNTIME_DIR="$probe/run" \
  XDG_STATE_HOME="$probe/state" \
  XDG_CONFIG_HOME="$probe/config" \
  XDG_CACHE_HOME="$probe/cache" \
  TMPDIR="$probe/tmp" \
  "$bin" routing preview --non-interactive --request-stdin --output json \
  >"$probe/preview.json" 2>"$probe/preview.err" <<'EOF'
{"change":{"schema":"hiroute.publication-checkpoint-change/v1"}}
EOF
preview_code=$?
set -e
if [ "$preview_code" -ne 0 ]; then
  printf '%s\n' "offline preview failed ($preview_code); no receipt" >&2
  exit 1
fi
python3 - "$probe/preview.json" <<'PY'
import json
import sys

doc = json.load(open(sys.argv[1], encoding="utf-8"))
if doc.get("status") != "succeeded":
    sys.stderr.write("preview status is not succeeded; no receipt\n")
    raise SystemExit(1)
PY
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)

resolved=$(readlink -f "$bin" 2>/dev/null || printf '%s' "$bin")
tool_version=$(printf '%s\n' "$resolved" | sed -n 's|.*/\([0-9][0-9.]*\)/hiroute$|\1|p')
if [ -z "$tool_version" ]; then
  tool_version=hiroute
fi

lock=$root/eval/integrate/hiroute/hiroute-ff.lock
exec 9>>"$lock"
if ! flock -n 9; then
  printf '%s\n' "hiroute-ff.lock is busy" >&2
  exit 1
fi

run_id="hiroute-${sha:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"
did="Offline dry classification via routing preview. No listen. Port 11434 was not used."
dest_dir=$(CDPATH= cd -- "$(dirname -- "$dest")" && pwd)
tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
python3 - "$tmp" "$sha" "$started" "$finished" "$tool_version" "$did" "$run_id" <<'PY'
import json
import sys

path, sha, started, finished, version, did, run_id = sys.argv[1:]
doc = {
    "slug": "hiroute",
    "run_kind": "pipeline",
    "main_sha": sha,
    "run_id": run_id,
    "started": started,
    "finished": finished,
    "outcome": "ok",
    "tool_version": version,
    "did": did,
}
with open(path, "w", encoding="utf-8") as handle:
    json.dump(doc, handle, indent=2)
    handle.write("\n")
PY
mv "$tmp" "$dest"
printf '%s\n' "$dest"
