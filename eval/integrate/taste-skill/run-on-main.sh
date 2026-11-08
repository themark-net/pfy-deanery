#!/bin/bash
# Offline taste-skill app-mode lint on one operator page.
# One output file. No browser download. The operator UI build stays as it is
# when this script is not called.
#
# Usage:
#   bash eval/integrate/taste-skill/run-on-main.sh eval/integrate/taste-skill/receipt.json
#
# A busy flock on eval/integrate/taste-skill/.run.lock exits 2 and writes no
# receipt. That check runs before ancestry and before the lint.
# The driver lane marker is left untouched. This script does not create it,
# remove it, or read it.
#
# The main fast-forward is one flock. Extra lock name: taste-skill-ff.
# This script does not take taste-skill-ff and does not push.
#
# Write the receipt only when HEAD is an ancestor of origin/main and the lint
# exits 0 or 1. A missing pinned cache binary, exit 2, and a timeout write
# nothing. A timeout is not a pass.
# A worktree-only diff is not the receipt.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/taste-skill/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

receipt=$1
case "$receipt" in
  /*) ;;
  *) receipt=$PWD/$receipt ;;
esac

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# Second start: flock before ancestry and before the lint.
exec 9>>"$here/.run.lock"
if ! flock -n 9; then
  printf '%s\n' "run lock held" >&2
  exit 2
fi

root=$(git -C "$here" rev-parse --show-toplevel)
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

rel=gui/operator/frontend/index.html
page=$root/$rel
if [ ! -f "$page" ]; then
  printf '%s\n' "fixture missing: $rel" >&2
  exit 1
fi

cache=${TASTE_SKILL_CACHE:-${HOME}/.cache/pfy/tools/taste-skill}
src=$cache/src
lint=$src/skills/taste-skill/scripts/lint.mjs
pin=6010f91a9935f1c167dfc500fb1a475681892e6b
lint_sha=05f2fae2f56fc051b539cdbacb43a6f78fbbfb9644bb74aa11be472ff12dcaf5
if [ -n "${TASTE_SKILL_NODE+x}" ]; then
  node=$TASTE_SKILL_NODE
else
  node=$(command -v node || true)
fi
if [ -z "${node:-}" ] || [ ! -x "$node" ] || [ ! -f "$lint" ]; then
  printf '%s\n' "pinned cache binary missing" >&2
  exit 2
fi
actual_sha=$(sha256sum "$lint" | awk '{print $1}')
if [ "$actual_sha" != "$lint_sha" ]; then
  printf '%s\n' "pinned cache binary mismatch" >&2
  exit 2
fi
got_pin=$(git -C "$src" rev-parse HEAD 2>/dev/null || true)
if [ "$got_pin" != "$pin" ]; then
  printf '%s\n' "pinned cache commit mismatch" >&2
  exit 2
fi
if ! command -v timeout >/dev/null 2>&1; then
  printf '%s\n' "timeout command missing" >&2
  exit 2
fi

tool_version=$(git -C "$src" describe --tags --exact-match HEAD 2>/dev/null || true)
if [ -z "$tool_version" ]; then
  tool_version=$pin
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/taste-skill-integrate.XXXXXX")
receipt_tmp=
cleanup() {
  if [ -n "${receipt_tmp:-}" ]; then
    rm -f "$receipt_tmp"
  fi
  if [ -n "${work:-}" ]; then
    rm -rf "$work"
  fi
}
trap cleanup EXIT
mkdir -p "$work/home" "$work/tmp" "$work/xdg"

started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
timeout 30 env \
  HOME="$work/home" \
  TMPDIR="$work/tmp" \
  XDG_CONFIG_HOME="$work/xdg" \
  XDG_CACHE_HOME="$work/xdg" \
  XDG_DATA_HOME="$work/xdg" \
  TASTE_SKILL_TMP="$work/tmp" \
  TASTE_SKILL_HISTORY="$work/history.json" \
  NO_COLOR=1 \
  "$node" "$lint" "$rel" --app --json >"$work/lint.json" 2>"$work/lint.err"
rc=$?
set -e
if [ "$rc" -eq 124 ]; then
  printf '%s\n' "timeout is not a pass" >&2
  exit 124
fi
if [ "$rc" -ne 0 ] && [ "$rc" -ne 1 ]; then
  printf '%s\n' "lint exit $rc" >&2
  cat "$work/lint.err" >&2 || true
  exit "$rc"
fi
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)

dest_dir=$(dirname -- "$receipt")
mkdir -p -- "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_TMP=$receipt_tmp
export RECEIPT_SHA=$sha
export RECEIPT_RUN_ID="taste-skill-${sha:0:12}-${started}"
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$tool_version
export RECEIPT_RC=$rc
export LINT_JSON=$work/lint.json
python3 - <<'PY'
import json
import os
from pathlib import Path

rc = os.environ["RECEIPT_RC"]
page = "gui/operator/frontend/index.html"
fails = None
warns = None
try:
    data = json.loads(Path(os.environ["LINT_JSON"]).read_text(encoding="utf-8"))
except (OSError, json.JSONDecodeError):
    data = None
if isinstance(data, dict) and isinstance(data.get("findings"), list):
    fails = 0
    warns = 0
    for row in data["findings"]:
        if not isinstance(row, dict):
            continue
        level = row.get("level")
        if level == "FAIL":
            fails += 1
        elif level == "WARN":
            warns += 1
if fails is None:
    did = (
        f"Ran pinned taste-skill lint.mjs --app on {page}. "
        f"Exit {rc}."
    )
else:
    did = (
        f"Ran pinned taste-skill lint.mjs --app on {page}. "
        f"Exit {rc}. FAIL {fails}. WARN {warns}."
    )
outcome = "ok" if rc == "0" else "findings"
doc = {
    "slug": "taste-skill",
    "run_kind": "pipeline",
    "main_sha": os.environ["RECEIPT_SHA"],
    "run_id": os.environ["RECEIPT_RUN_ID"],
    "started": os.environ["RECEIPT_STARTED"],
    "finished": os.environ["RECEIPT_FINISHED"],
    "outcome": outcome,
    "tool_version": os.environ["RECEIPT_VERSION"],
    "did": did,
}
Path(os.environ["RECEIPT_TMP"]).write_text(
    json.dumps(doc, indent=2) + "\n",
    encoding="utf-8",
)
PY
mv -f "$receipt_tmp" "$receipt"
receipt_tmp=
printf '%s\n' "$receipt"
