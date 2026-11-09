#!/bin/bash
# Local-control receipt for a published HiRoute plan.
# no-listen: this script does not bind a port. Do not use port 11434.
# Do not start Ollama. Do not call a model. routing list is local_control_only
# and its contract says model_call never. A missing binary, a down socket,
# a non-success envelope, or a timeout writes no receipt.
# This is not routing_agreement_of_20. That metric is a model trial.
# This script does not create the dispatched marker and does not push.
# modular-ci: no .github/workflows job, no ci/ job, no model_lock.sh
# extra lock: flock eval/integrate/hiroute/hiroute-ff.lock
# The main push is a fast-forward under that flock. A second start exits 2.
# A marker whose pid is an ancestor of this process is the admitted lane.
# Any other existing marker is a second start.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/hiroute/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

dest=$1
marker=${PFY_HIROUTE_LANE_MARKER:-$HOME/DEVELOP/pfy-mentat/tmp/integrate2/hiroute.dispatched}

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

if [ -e "$marker" ]; then
  if ! marker_pid_is_ancestor "$marker"; then
    printf '%s\n' "already dispatched: $marker" >&2
    exit 2
  fi
fi

if [ -n "${HIROUTE_BIN+x}" ]; then
  bin=$HIROUTE_BIN
else
  bin=${HIROUTE_CACHE:-${HOME:-/nonexistent}/.cache/pfy/tools/hiroute}/home/.local/bin/hiroute
fi
if [ ! -x "$bin" ]; then
  printf '%s\n' "hiroute binary missing; no receipt" >&2
  exit 1
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

cache=${HIROUTE_CACHE:-${HOME:-/nonexistent}/.cache/pfy/tools/hiroute}
trial_home=$cache/home
runtime=$cache/run
tmp_dir=$cache/tmp

out=$(mktemp)
err=$(mktemp)
ver_out=$(mktemp)
cleanup() {
  rm -f "$out" "$err" "$ver_out"
  if [ -n "${receipt_tmp:-}" ]; then
    rm -f "$receipt_tmp"
  fi
}
trap cleanup EXIT

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
timeout 20 env -i \
  HOME="$trial_home" \
  XDG_DATA_HOME="$trial_home/.local/share" \
  XDG_CONFIG_HOME="$trial_home/.config" \
  XDG_CACHE_HOME="$trial_home/.cache" \
  XDG_STATE_HOME="$trial_home/.local/state" \
  XDG_RUNTIME_DIR="$runtime" \
  TMPDIR="$tmp_dir" \
  PATH="/usr/bin:/bin" \
  "$bin" routing list --output json >"$out" 2>"$err"
rc=$?
set -e
if [ "$rc" -eq 124 ]; then
  printf '%s\n' "routing list timeout; no receipt" >&2
  exit 124
fi
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "routing list failed; no receipt" >&2
  exit 1
fi

parsed=$(python3 - "$out" <<'PY'
import json
import re
import sys
from pathlib import Path

raw = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").strip()
if not raw:
    raise SystemExit(1)
try:
    doc = json.loads(raw)
except json.JSONDecodeError:
    raise SystemExit(1)
if not isinstance(doc, dict) or doc.get("status") != "succeeded":
    raise SystemExit(1)
data = doc.get("data")
if not isinstance(data, dict):
    raise SystemExit(1)
plans = data.get("plans")
if not isinstance(plans, list) or not plans:
    raise SystemExit(1)
alias = ""
first = plans[0]
if isinstance(first, dict):
    raw_alias = first.get("model_alias")
    if isinstance(raw_alias, str) and re.fullmatch(r"[A-Za-z0-9._:-]{1,80}", raw_alias):
        alias = raw_alias
print(f"{len(plans)}\t{alias}")
PY
) || {
  printf '%s\n' "routing list envelope rejected; no receipt" >&2
  exit 1
}

plan_count=${parsed%%$'\t'*}
alias=${parsed#*$'\t'}
case "$plan_count" in
  ''|*[!0-9]*) printf '%s\n' "routing list envelope rejected; no receipt" >&2; exit 1 ;;
esac
if [ "$plan_count" -lt 1 ]; then
  printf '%s\n' "routing list envelope rejected; no receipt" >&2
  exit 1
fi

set +e
timeout 5 env -i \
  HOME="$trial_home" \
  XDG_DATA_HOME="$trial_home/.local/share" \
  XDG_CONFIG_HOME="$trial_home/.config" \
  XDG_CACHE_HOME="$trial_home/.cache" \
  XDG_STATE_HOME="$trial_home/.local/state" \
  XDG_RUNTIME_DIR="$runtime" \
  TMPDIR="$tmp_dir" \
  PATH="/usr/bin:/bin" \
  "$bin" version >"$ver_out" 2>/dev/null
set -e
tool_version=$(head -n 1 "$ver_out" 2>/dev/null | tr -d '\r' || true)
if [ -z "$tool_version" ] || [ "${#tool_version}" -gt 80 ] || printf '%s' "$tool_version" | grep -q '[/~]'; then
  tool_version=hiroute
fi

if [ -n "$alias" ]; then
  alias_text="alias ${alias}"
else
  alias_text="alias withheld"
fi
did="routing list on the local-control socket returned ${plan_count} plans. ${alias_text}. model_call never. Did not score routing_agreement_of_20."

finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_id="hiroute-${sha:0:12}-$(date -u +%Y%m%dT%H%M%SZ)"
dest_dir=$(dirname -- "$dest")
mkdir -p "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_SHA=$sha
export RECEIPT_RUN_ID=$run_id
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$tool_version
export RECEIPT_DID=$did
python3 - "$receipt_tmp" <<'PY'
import json
import os
import sys

doc = {
    "slug": "hiroute",
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
mv -f "$receipt_tmp" "$dest"
receipt_tmp=
trap - EXIT
rm -f "$out" "$err" "$ver_out"
printf '%s\n' "$dest"
