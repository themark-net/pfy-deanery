#!/bin/bash
# Advisory read-only ci-score of this checkout, then a pipeline receipt.
#
# Pipeline: scripts/integrate_lane.sh calls this after the fast-forward
# onto origin/main. Before it: the land push. After it:
# scripts/catalog_apply_verdict.py. An operator can run the same command
# on a commit that is already on origin/main:
#   bash eval/integrate/starsling-skills/run-on-main.sh \
#     eval/integrate/starsling-skills/receipt.json
#
# This is new wiring. When this script is not selected, workflow files
# and the pipeline exit stay as they are. The lane treats a missing
# script as today's behavior.
#
# Fail safe: a missing pin, a collect error, a worktree change, or a
# timeout (STARSLING_TIMEOUT seconds, default 60) exits nonzero and
# writes no receipt. A timeout is not a pass. An existing receipt file
# is left in place. This script does not edit workflow files and does
# not apply fixes. ci-speedup is not run here; it needs run history and
# stays the earlier measured probe.
#
# Duplicate-run: the driver marker tmp/integrate/starsling-skills.dispatched
# makes a second lane start exit 2. This script does not create that
# marker and does not push. Extra lock: flock -n on
# eval/integrate/starsling-skills/.run.lock (one state file in this
# worktree). A second start in this checkout exits 2 and writes no
# receipt. There is no port; ci-score is offline and scores only this
# checkout. Two other checkouts each take their own lock and each score
# their own tree. If they name the same receipt path, the later full
# rename wins and a reader never sees a partial file.

set -euo pipefail

if [ "$#" -ne 1 ] || [ -z "${1:-}" ]; then
  printf '%s\n' "usage: eval/integrate/starsling-skills/run-on-main.sh RECEIPT.json" >&2
  exit 2
fi

receipt=$1
case "$receipt" in
  /*) ;;
  *) receipt=$PWD/$receipt ;;
esac

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
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
main_sha=$(git rev-parse HEAD)
if ! git merge-base --is-ancestor "$main_sha" origin/main; then
  printf '%s\n' "HEAD is not an ancestor of origin/main; no receipt" >&2
  exit 1
fi
if [[ ! "$main_sha" =~ ^[0-9a-f]{40}$ ]]; then
  printf '%s\n' "main_sha is not 40 hex characters" >&2
  exit 1
fi

pin=${STARSLING_PIN:-14571ad98289d8afd8de1a5b87ddc51909984f30}
if [ -n "${STARSLING_ROOT:-}" ]; then
  skill=$STARSLING_ROOT
else
  skill="${HOME}/.cache/pfy/tools/starsling-skills"
fi
collect=$skill/skills/ci-score/scripts/collect_config.py
if [ ! -f "$collect" ]; then
  printf '%s\n' "pinned ci-score missing" >&2
  exit 1
fi
got_pin=$(git -C "$skill" rev-parse HEAD 2>/dev/null || true)
if [ "$got_pin" != "$pin" ]; then
  printf '%s\n' "pinned ci-score commit mismatch" >&2
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  printf '%s\n' "python3 missing" >&2
  exit 1
fi
if ! command -v timeout >/dev/null 2>&1; then
  printf '%s\n' "timeout command missing" >&2
  exit 1
fi

limit=${STARSLING_TIMEOUT:-60}
case "$limit" in
  ''|*[!0-9]*)
    printf '%s\n' "timeout is not a positive integer" >&2
    exit 1
    ;;
esac
if [ "$limit" -lt 1 ]; then
  printf '%s\n' "timeout is not a positive integer" >&2
  exit 1
fi

work=$(mktemp -d "${TMPDIR:-/tmp}/starsling-score.XXXXXX")
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

before=$(git status --porcelain)
started=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
timeout --kill-after=5 "$limit" python3 "$collect" --repo "$root" --out "$work/findings.json" >"$work/collect.out" 2>"$work/collect.err"
rc=$?
set -e
after=$(git status --porcelain)
if [ "$before" != "$after" ]; then
  printf '%s\n' "ci-score changed the worktree; no receipt" >&2
  exit 1
fi
if [ "$rc" -eq 124 ] || [ "$rc" -eq 137 ]; then
  printf '%s\n' "timeout is not a pass" >&2
  exit "$rc"
fi
if [ "$rc" -ne 0 ]; then
  printf '%s\n' "ci-score exit $rc" >&2
  exit "$rc"
fi
if [ ! -s "$work/findings.json" ]; then
  printf '%s\n' "ci-score wrote no findings" >&2
  exit 1
fi

parsed=$(python3 - "$work/findings.json" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
score = data.get("ci_score") if isinstance(data, dict) else None
if not isinstance(score, dict):
    raise SystemExit(1)
value = score.get("value")
if isinstance(value, bool) or not isinstance(value, (int, float)) or int(value) != value:
    raise SystemExit(1)
spec = score.get("spec_version")
if not isinstance(spec, str):
    spec = ""
scanned = data.get("scanned_workflows")
if isinstance(scanned, bool) or not isinstance(scanned, int) or scanned < 0:
    scanned = -1
sys.stdout.write("%d\n%s\n%d\n" % (int(value), spec, scanned))
PY
) || {
  printf '%s\n' "ci-score findings had no score" >&2
  exit 1
}
score=$(printf '%s\n' "$parsed" | sed -n '1p')
spec=$(printf '%s\n' "$parsed" | sed -n '2p')
scanned=$(printf '%s\n' "$parsed" | sed -n '3p')
if ! printf '%s' "$spec" | grep -E -q '^[A-Za-z0-9._+-]{1,40}$'; then
  spec=$pin
fi
finished=$(date -u +%Y-%m-%dT%H:%M:%SZ)
run_id="starsling-skills-${main_sha:0:12}-${started}"
if [ "$scanned" -ge 0 ]; then
  did="Ran pinned ci-score collect_config.py on ${main_sha}. Score ${score}/100 (${spec}). Scanned ${scanned} workflows. Workflows unchanged. ci-speedup was not run."
else
  did="Ran pinned ci-score collect_config.py on ${main_sha}. Score ${score}/100 (${spec}). Workflows unchanged. ci-speedup was not run."
fi

ops=$root/tmp/ops/eval/integrate/starsling-skills
mkdir -p "$ops"
cp "$work/findings.json" "$ops/ci-score-findings.json"
cp "$work/collect.out" "$ops/ci-score.out"
cp "$work/collect.err" "$ops/ci-score.err"

dest_dir=$(dirname -- "$receipt")
mkdir -p -- "$dest_dir"
receipt_tmp=$(mktemp "$dest_dir/.receipt.XXXXXX")
export RECEIPT_TMP=$receipt_tmp
export RECEIPT_SHA=$main_sha
export RECEIPT_RUN_ID=$run_id
export RECEIPT_STARTED=$started
export RECEIPT_FINISHED=$finished
export RECEIPT_VERSION=$spec
export RECEIPT_DID=$did
python3 - <<'PY'
import json
import os
from pathlib import Path

doc = {
    "slug": "starsling-skills",
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
printf '%s\n' "$receipt"
